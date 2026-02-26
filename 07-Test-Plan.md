# Comprehensive Test Plan

**Project**: GenRecon - Generic Data Reconciliation Platform  
**Version**: 1.0  
**Date**: January 30, 2026  
**Test Framework**: pytest, FastAPI TestClient

---

## 1. Test Strategy Overview

### 1.1 Test Levels

| Level | Coverage | Tools |
|-------|----------|-------|
| **Unit Tests** | Individual functions, classes | pytest, unittest.mock |
| **Integration Tests** | Component interactions | pytest, testcontainers |
| **API Tests** | REST endpoint validation | FastAPI TestClient |
| **End-to-End Tests** | Complete reconciliation flows | pytest, real databases |
| **Performance Tests** | Load, throughput, scalability | locust, pytest-benchmark |

### 1.2 Test Database Setup

```python
# tests/conftest.py

import pytest
from testcontainers.oracle import OracleContainer
from testcontainers.mongodb import MongoDbContainer
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def oracle_container():
    """Oracle database for testing"""
    with OracleContainer("gvenzl/oracle-xe:21-slim") as oracle:
        yield oracle

@pytest.fixture(scope="session")
def mongodb_container():
    """MongoDB for testing"""
    with MongoDbContainer("mongo:7.0") as mongo:
        yield mongo

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL for metadata storage"""
    with PostgresContainer("postgres:15") as postgres:
        yield postgres

@pytest.fixture
def test_data_loader(oracle_container, mongodb_container):
    """Load test data into containers"""
    # Load Oracle test data
    conn = oracle_container.get_connection()
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE CUSTOMERS (
            CUSTOMER_ID NUMBER(10) PRIMARY KEY,
            CUSTOMER_NAME VARCHAR2(100),
            EMAIL VARCHAR2(100),
            ACCOUNT_STATUS VARCHAR2(20),
            BALANCE NUMBER(15,2),
            CREATED_DATE DATE
        )
    """)
    
    # Insert test records
    test_customers = [
        (1001, 'John Doe', 'john@example.com', 'ACTIVE', 5000.00, '2024-01-15'),
        (1002, 'Jane Smith', 'jane@example.com', 'ACTIVE', 15000.50, '2024-02-20'),
        # ... more test data
    ]
    
    cursor.executemany(
        "INSERT INTO CUSTOMERS VALUES (:1, :2, :3, :4, :5, TO_DATE(:6, 'YYYY-MM-DD'))",
        test_customers
    )
    conn.commit()
    
    # Load MongoDB test data
    mongo_client = mongodb_container.get_connection_client()
    db = mongo_client['test_db']
    
    db.customers.insert_many([
        {
            "customerId": 1001,
            "customerName": "John Doe",
            "email": "john@example.com",
            "accountStatus": "ACTIVE",
            "balance": 5000.00,
            "createdDate": "2024-01-15"
        },
        {
            "customerId": 1002,
            "customerName": "Jane Smith",
            "email": "jane@example.com",
            "accountStatus": "ACTIVE",
            "balance": 15000.50,
            "createdDate": "2024-02-20"
        }
        # ... more test data
    ])
    
    yield {
        'oracle': oracle_container,
        'mongodb': mongodb_container
    }
    
    # Cleanup
    cursor.execute("DROP TABLE CUSTOMERS")
    db.customers.drop()
```

---

## 2. Unit Tests

### 2.1 Schema Inference Tests

```python
# tests/unit/test_schema_inference.py

import pytest
from src.schema_inference.oracle_inferrer import OracleSchemaInferrer
from src.schema_inference.mongodb_inferrer import MongoDBSchemaInferrer

class TestOracleSchemaInferrer:
    """Test Oracle schema inference"""
    
    def test_infer_table_schema(self, oracle_container):
        """Test basic table schema inference"""
        inferrer = OracleSchemaInferrer(oracle_container.get_connection())
        
        schema = inferrer.infer_table_schema("CUSTOMERS")
        
        assert schema['table_name'] == "CUSTOMERS"
        assert 'fields' in schema
        assert len(schema['fields']) == 6
        
        # Check specific fields
        customer_id_field = next(f for f in schema['fields'] if f['field_id'] == 'customerId')
        assert customer_id_field['field_name'] == 'CUSTOMER_ID'
        assert customer_id_field['data_type'] == 'NUMBER'
        assert customer_id_field['is_primary_key'] is True
        assert customer_id_field['is_nullable'] is False
    
    def test_infer_foreign_keys(self, oracle_container):
        """Test foreign key detection"""
        inferrer = OracleSchemaInferrer(oracle_container.get_connection())
        
        # Assuming ORDERS table has FK to CUSTOMERS
        schema = inferrer.infer_table_schema("ORDERS")
        
        fk_field = next(f for f in schema['fields'] if f['field_id'] == 'customerId')
        assert fk_field['foreign_key'] is not None
        assert fk_field['foreign_key']['referenced_table'] == 'CUSTOMERS'
        assert fk_field['foreign_key']['referenced_field'] == 'CUSTOMER_ID'
    
    def test_infer_data_type_mapping(self, oracle_container):
        """Test Oracle data type to generic type mapping"""
        inferrer = OracleSchemaInferrer(oracle_container.get_connection())
        
        mappings = [
            ('NUMBER(10)', 'INTEGER'),
            ('NUMBER(15,2)', 'DECIMAL'),
            ('VARCHAR2(100)', 'STRING'),
            ('DATE', 'DATE'),
            ('TIMESTAMP', 'TIMESTAMP'),
            ('CLOB', 'TEXT')
        ]
        
        for oracle_type, expected_generic in mappings:
            generic = inferrer.map_to_generic_type(oracle_type)
            assert generic == expected_generic

class TestMongoDBSchemaInferrer:
    """Test MongoDB schema inference"""
    
    def test_infer_collection_schema(self, mongodb_container):
        """Test collection schema inference from documents"""
        client = mongodb_container.get_connection_client()
        db = client['test_db']
        
        inferrer = MongoDBSchemaInferrer(db)
        schema = inferrer.infer_collection_schema("customers", sample_size=100)
        
        assert schema['collection_name'] == "customers"
        assert 'fields' in schema
        
        # Check inferred fields
        customer_id_field = next(f for f in schema['fields'] if f['field_id'] == 'customerId')
        assert customer_id_field['data_type'] in ['INTEGER', 'NUMBER']
        assert customer_id_field['field_path'] == 'customerId'
    
    def test_handle_nested_documents(self, mongodb_container):
        """Test nested document schema inference"""
        client = mongodb_container.get_connection_client()
        db = client['test_db']
        
        # Insert document with nested structure
        db.customers.insert_one({
            "customerId": 9999,
            "address": {
                "street": "123 Main St",
                "city": "Springfield",
                "zipCode": "12345"
            }
        })
        
        inferrer = MongoDBSchemaInferrer(db)
        schema = inferrer.infer_collection_schema("customers")
        
        # Check nested field paths
        street_field = next(f for f in schema['fields'] if f['field_id'] == 'address.street')
        assert street_field['field_path'] == 'address.street'
        assert street_field['data_type'] == 'STRING'
    
    def test_handle_arrays(self, mongodb_container):
        """Test array field inference"""
        client = mongodb_container.get_connection_client()
        db = client['test_db']
        
        db.customers.insert_one({
            "customerId": 9998,
            "tags": ["premium", "vip", "verified"]
        })
        
        inferrer = MongoDBSchemaInferrer(db)
        schema = inferrer.infer_collection_schema("customers")
        
        tags_field = next(f for f in schema['fields'] if f['field_id'] == 'tags')
        assert tags_field['data_type'] == 'ARRAY'
        assert tags_field['array_item_type'] == 'STRING'
```

### 2.2 Data Extraction Tests

```python
# tests/unit/test_data_extraction.py

import pytest
from src.data_extraction.oracle_extractor import OracleDataExtractor
from src.data_extraction.mongodb_extractor import MongoDBDataExtractor

class TestOracleDataExtractor:
    """Test Oracle data extraction"""
    
    def test_extract_table_data(self, oracle_container, test_data_loader):
        """Test extracting data from Oracle table"""
        extractor = OracleDataExtractor(oracle_container.get_connection())
        
        data = extractor.extract_data(
            table_name="CUSTOMERS",
            batch_size=100
        )
        
        records = list(data)
        assert len(records) > 0
        assert 'customerId' in records[0]
        assert 'customerName' in records[0]
    
    def test_extract_with_filters(self, oracle_container, test_data_loader):
        """Test extraction with WHERE clause"""
        extractor = OracleDataExtractor(oracle_container.get_connection())
        
        data = extractor.extract_data(
            table_name="CUSTOMERS",
            filters={"accountStatus": "ACTIVE"},
            batch_size=50
        )
        
        records = list(data)
        assert all(r['accountStatus'] == 'ACTIVE' for r in records)
    
    def test_extract_with_transformations(self, oracle_container, test_data_loader):
        """Test field transformations during extraction"""
        extractor = OracleDataExtractor(oracle_container.get_connection())
        
        transformations = {
            'createdDate': lambda d: d.strftime('%Y-%m-%d') if d else None
        }
        
        data = extractor.extract_data(
            table_name="CUSTOMERS",
            transformations=transformations,
            batch_size=100
        )
        
        records = list(data)
        assert isinstance(records[0]['createdDate'], str)

class TestMongoDBDataExtractor:
    """Test MongoDB data extraction"""
    
    def test_extract_collection_data(self, mongodb_container, test_data_loader):
        """Test extracting data from MongoDB collection"""
        client = mongodb_container.get_connection_client()
        db = client['test_db']
        
        extractor = MongoDBDataExtractor(db)
        
        data = extractor.extract_data(
            collection_name="customers",
            batch_size=100
        )
        
        records = list(data)
        assert len(records) > 0
        assert 'customerId' in records[0]
    
    def test_flatten_nested_documents(self, mongodb_container):
        """Test nested document flattening"""
        client = mongodb_container.get_connection_client()
        db = client['test_db']
        
        db.customers.insert_one({
            "customerId": 8888,
            "address": {
                "street": "456 Oak St",
                "city": "Boston"
            }
        })
        
        extractor = MongoDBDataExtractor(db)
        data = extractor.extract_data(
            collection_name="customers",
            flatten=True
        )
        
        record = next(r for r in data if r['customerId'] == 8888)
        assert 'address.street' in record
        assert record['address.street'] == "456 Oak St"
```

### 2.3 Field Comparator Tests

```python
# tests/unit/test_comparators.py

import pytest
from src.comparison.comparators import (
    ExactComparator, NumericComparator, DateComparator,
    StringCaseInsensitiveComparator, ReferenceDataComparator
)
from datetime import datetime, date

class TestExactComparator:
    """Test exact value comparison"""
    
    def test_exact_match(self):
        comparator = ExactComparator()
        
        result = comparator.compare("John Doe", "John Doe")
        assert result.is_match is True
        assert result.difference is None
    
    def test_exact_mismatch(self):
        comparator = ExactComparator()
        
        result = comparator.compare("John Doe", "Jane Smith")
        assert result.is_match is False
        assert result.difference == "John Doe != Jane Smith"

class TestNumericComparator:
    """Test numeric comparison with tolerance"""
    
    def test_exact_numeric_match(self):
        comparator = NumericComparator(tolerance=0.0)
        
        result = comparator.compare(100.50, 100.50)
        assert result.is_match is True
    
    def test_within_tolerance(self):
        comparator = NumericComparator(tolerance=0.01)
        
        result = comparator.compare(100.50, 100.51)
        assert result.is_match is True
    
    def test_outside_tolerance(self):
        comparator = NumericComparator(tolerance=0.01)
        
        result = comparator.compare(100.50, 100.60)
        assert result.is_match is False
        assert "diff: 0.10" in result.difference

class TestDateComparator:
    """Test date comparison"""
    
    def test_exact_date_match(self):
        comparator = DateComparator()
        
        d1 = date(2024, 1, 15)
        d2 = date(2024, 1, 15)
        
        result = comparator.compare(d1, d2)
        assert result.is_match is True
    
    def test_date_format_conversion(self):
        comparator = DateComparator(
            source_format="%Y-%m-%d",
            target_format="%d/%m/%Y"
        )
        
        result = comparator.compare("2024-01-15", "15/01/2024")
        assert result.is_match is True

class TestReferenceDataComparator:
    """Test reference data comparison"""
    
    def test_reference_lookup(self):
        reference_data = {
            "ACTIVE": "A",
            "INACTIVE": "I",
            "CLOSED": "C"
        }
        
        comparator = ReferenceDataComparator(reference_map=reference_data)
        
        result = comparator.compare("ACTIVE", "A")
        assert result.is_match is True
    
    def test_reverse_lookup(self):
        reference_data = {
            "ACTIVE": "A",
            "INACTIVE": "I"
        }
        
        comparator = ReferenceDataComparator(
            reference_map=reference_data,
            bidirectional=True
        )
        
        result = comparator.compare("A", "ACTIVE")
        assert result.is_match is True
```

---

## 3. Integration Tests

### 3.1 End-to-End Reconciliation Test

```python
# tests/integration/test_reconciliation_flow.py

import pytest
from src.orchestration.reconciliation_engine import ReconciliationEngine

class TestReconciliationFlow:
    """Test complete reconciliation workflow"""
    
    def test_full_customer_reconciliation(
        self, 
        oracle_container, 
        mongodb_container, 
        postgres_container,
        test_data_loader
    ):
        """Test complete reconciliation from schema inference to results"""
        
        # 1. Setup engine
        engine = ReconciliationEngine(
            metadata_db=postgres_container.get_connection()
        )
        
        # 2. Create systems
        oracle_system = engine.create_system(
            system_id="oracle-test",
            system_type="ORACLE",
            connection_config=oracle_container.get_connection_params()
        )
        
        mongo_system = engine.create_system(
            system_id="mongo-test",
            system_type="MONGODB",
            connection_config=mongodb_container.get_connection_params()
        )
        
        # 3. Infer schemas
        oracle_schema = engine.infer_schema(
            system_id="oracle-test",
            dataset_name="CUSTOMERS"
        )
        
        mongo_schema = engine.infer_schema(
            system_id="mongo-test",
            dataset_name="customers"
        )
        
        # 4. Create datasets
        source_dataset = engine.create_dataset(
            dataset_id="customers_oracle",
            system_id="oracle-test",
            schema_id=oracle_schema['schema_id'],
            physical_name="CUSTOMERS"
        )
        
        target_dataset = engine.create_dataset(
            dataset_id="customers_mongo",
            system_id="mongo-test",
            schema_id=mongo_schema['schema_id'],
            physical_name="customers"
        )
        
        # 5. Create mapping
        mapping = engine.create_mapping(
            mapping_id="customer_mapping",
            source_schema_id=oracle_schema['schema_id'],
            target_schema_id=mongo_schema['schema_id'],
            field_mappings=[
                {
                    "source_field": "customerId",
                    "target_field": "customerId",
                    "comparator_type": "EXACT"
                },
                {
                    "source_field": "customerName",
                    "target_field": "customerName",
                    "comparator_type": "EXACT"
                },
                {
                    "source_field": "balance",
                    "target_field": "balance",
                    "comparator_type": "NUMERIC",
                    "comparator_config": {"tolerance": 0.01}
                }
            ]
        )
        
        # 6. Create rule set
        rule_set = engine.create_rule_set(
            rule_set_id="customer_recon",
            source_dataset_id="customers_oracle",
            target_dataset_id="customers_mongo",
            mapping_id="customer_mapping",
            matching_keys=[
                {"source_field": "customerId", "target_field": "customerId"}
            ]
        )
        
        # 7. Execute reconciliation
        job_id = engine.start_reconciliation(rule_set_id="customer_recon")
        
        # Wait for completion
        engine.wait_for_completion(job_id, timeout=300)
        
        # 8. Verify results
        results = engine.get_results(job_id)
        
        assert results['status'] == 'COMPLETED'
        assert results['total_source_records'] > 0
        assert results['total_target_records'] > 0
        assert results['match_rate_percent'] >= 95.0  # Expect high match rate
        
        # Check specific metrics
        summary = results['summary']
        assert summary['matched_records'] == summary['matched_with_no_discrepancy'] + summary['matched_with_discrepancy']
        
        # Verify discrepancies if any
        if summary['matched_with_discrepancy'] > 0:
            discrepancies = engine.get_discrepancies(job_id, limit=10)
            assert len(discrepancies) > 0
            assert all('field_id' in d for d in discrepancies)
            assert all('difference' in d for d in discrepancies)
```

### 3.2 Multi-Table Reconciliation Test

```python
# tests/integration/test_multi_table_reconciliation.py

class TestMultiTableReconciliation:
    """Test reconciliation across multiple related tables"""
    
    def test_customer_and_orders_reconciliation(
        self,
        oracle_container,
        mongodb_container,
        postgres_container
    ):
        """Test reconciling customers and their orders"""
        
        engine = ReconciliationEngine(
            metadata_db=postgres_container.get_connection()
        )
        
        # Setup for CUSTOMERS table
        customers_rule_set = engine.create_complete_rule_set(
            rule_set_id="customers_recon",
            source_system="oracle-test",
            source_table="CUSTOMERS",
            target_system="mongo-test",
            target_collection="customers",
            matching_keys=["customerId"]
        )
        
        # Setup for ORDERS table
        orders_rule_set = engine.create_complete_rule_set(
            rule_set_id="orders_recon",
            source_system="oracle-test",
            source_table="ORDERS",
            target_system="mongo-test",
            target_collection="orders",
            matching_keys=["orderId"]
        )
        
        # Execute both reconciliations
        customers_job = engine.start_reconciliation("customers_recon")
        orders_job = engine.start_reconciliation("orders_recon")
        
        # Wait for both to complete
        engine.wait_for_completion(customers_job)
        engine.wait_for_completion(orders_job)
        
        # Verify both results
        customers_results = engine.get_results(customers_job)
        orders_results = engine.get_results(orders_job)
        
        assert customers_results['status'] == 'COMPLETED'
        assert orders_results['status'] == 'COMPLETED'
        
        # Cross-check: unmatched orders should not reference unmatched customers
        unmatched_orders = engine.get_unmatched_source(orders_job)
        unmatched_customers = engine.get_unmatched_source(customers_job)
        
        unmatched_customer_ids = {c['customerId'] for c in unmatched_customers}
        
        for order in unmatched_orders:
            # Orders referencing missing customers is expected
            # This validates referential integrity checking
            if order['customerId'] in unmatched_customer_ids:
                print(f"Order {order['orderId']} references unmatched customer {order['customerId']}")
```

---

## 4. API Tests

```python
# tests/api/test_jobs_api.py

from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

class TestJobsAPI:
    """Test Jobs REST API"""
    
    def test_create_job(self):
        """Test creating a reconciliation job via API"""
        response = client.post(
            "/api/v1/jobs",
            json={
                "rule_set_id": "customer_recon"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert 'job_id' in data
        assert data['status'] == 'PENDING'
        assert data['rule_set_id'] == 'customer_recon'
    
    def test_get_job_status(self):
        """Test retrieving job status"""
        # Create job first
        create_response = client.post(
            "/api/v1/jobs",
            json={"rule_set_id": "customer_recon"}
        )
        job_id = create_response.json()['job_id']
        
        # Get status
        response = client.get(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data['job_id'] == job_id
        assert data['status'] in ['PENDING', 'RUNNING', 'COMPLETED']
    
    def test_list_jobs(self):
        """Test listing jobs with filters"""
        response = client.get(
            "/api/v1/jobs",
            params={
                "rule_set_id": "customer_recon",
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(j['rule_set_id'] == 'customer_recon' for j in data)
    
    def test_cancel_job(self):
        """Test cancelling a running job"""
        # Create job
        create_response = client.post(
            "/api/v1/jobs",
            json={"rule_set_id": "customer_recon"}
        )
        job_id = create_response.json()['job_id']
        
        # Cancel it
        response = client.delete(f"/api/v1/jobs/{job_id}")
        
        assert response.status_code == 204

class TestResultsAPI:
    """Test Results REST API"""
    
    def test_get_summary(self, completed_job_id):
        """Test getting result summary"""
        response = client.get(f"/api/v1/results/{completed_job_id}/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert 'total_source_records' in data
        assert 'total_target_records' in data
        assert 'match_rate_percent' in data
        assert 'accuracy_rate_percent' in data
    
    def test_get_discrepancies_paginated(self, completed_job_id):
        """Test getting paginated discrepancies"""
        response = client.get(
            f"/api/v1/results/{completed_job_id}/discrepancies",
            params={"limit": 50, "offset": 0}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 50
        
        if len(data) > 0:
            assert 'field_id' in data[0]
            assert 'difference' in data[0]
    
    def test_export_results_csv(self, completed_job_id):
        """Test exporting results to CSV"""
        response = client.get(
            f"/api/v1/results/{completed_job_id}/export",
            params={"format": "csv"}
        )
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/csv'
        assert 'Content-Disposition' in response.headers
```

---

## 5. Performance Tests

```python
# tests/performance/test_load.py

import pytest
from locust import HttpUser, task, between

class ReconciliationUser(HttpUser):
    """Locust user for load testing"""
    wait_time = between(1, 3)
    
    @task(3)
    def get_job_status(self):
        """Simulate checking job status"""
        self.client.get("/api/v1/jobs/JOB_TEST_123")
    
    @task(1)
    def create_job(self):
        """Simulate creating a job"""
        self.client.post(
            "/api/v1/jobs",
            json={"rule_set_id": "customer_recon"}
        )
    
    @task(2)
    def get_results(self):
        """Simulate fetching results"""
        self.client.get("/api/v1/results/JOB_TEST_123/summary")

# Run with: locust -f tests/performance/test_load.py --host=http://localhost:8000

class TestReconciliationPerformance:
    """Test reconciliation performance with large datasets"""
    
    @pytest.mark.benchmark
    def test_100k_records_reconciliation(self, benchmark):
        """Benchmark reconciliation of 100K records"""
        
        def run_reconciliation():
            engine = ReconciliationEngine()
            job_id = engine.start_reconciliation("large_customer_recon")
            engine.wait_for_completion(job_id)
            return engine.get_results(job_id)
        
        result = benchmark(run_reconciliation)
        
        # Assert performance requirements
        assert result['total_source_records'] == 100000
        assert benchmark.stats['mean'] < 60.0  # Should complete in under 60 seconds
    
    @pytest.mark.benchmark
    def test_field_comparison_performance(self, benchmark):
        """Benchmark field comparison throughput"""
        
        comparator = NumericComparator(tolerance=0.01)
        
        def compare_fields():
            for i in range(10000):
                comparator.compare(100.50 + (i * 0.001), 100.50)
        
        benchmark(compare_fields)
        
        # Should be able to compare 10K fields very quickly
        assert benchmark.stats['mean'] < 0.1  # Less than 100ms
```

---

## 6. Test Data Scenarios

### 6.1 Test Data Sets

```python
# tests/data/test_scenarios.py

TEST_SCENARIOS = {
    "perfect_match": {
        "description": "All records match perfectly",
        "oracle_records": 1000,
        "mongo_records": 1000,
        "expected_match_rate": 100.0,
        "expected_accuracy_rate": 100.0
    },
    
    "missing_target_records": {
        "description": "Some records missing in target",
        "oracle_records": 1000,
        "mongo_records": 950,
        "expected_match_rate": 95.0,
        "expected_unmatched_source": 50
    },
    
    "field_discrepancies": {
        "description": "Records match but fields have differences",
        "oracle_records": 1000,
        "mongo_records": 1000,
        "discrepancy_rate": 0.10,  # 10% of matched records have discrepancies
        "expected_match_rate": 100.0,
        "expected_accuracy_rate": 90.0
    },
    
    "mixed_scenario": {
        "description": "Combination of missing records and discrepancies",
        "oracle_records": 1000,
        "mongo_records": 980,
        "discrepancy_rate": 0.05,
        "expected_match_rate": 98.0,
        "expected_accuracy_rate": 93.1  # 98% match * 95% accuracy
    }
}
```

---

## 7. Test Execution & CI/CD

### 7.1 pytest Configuration

```ini
# pytest.ini

[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    performance: Performance tests
    slow: Slow running tests

addopts =
    -v
    --strict-markers
    --cov=src
    --cov-report=html
    --cov-report=term-missing
    --maxfail=5
```

### 7.2 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml

name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run unit tests
        run: pytest tests/unit -m unit
      
      - name: Run integration tests
        run: pytest tests/integration -m integration
      
      - name: Run API tests
        run: pytest tests/api -m api
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 8. Test Coverage Requirements

| Component | Minimum Coverage |
|-----------|------------------|
| Schema Inference | 90% |
| Data Extraction | 85% |
| Field Comparators | 95% |
| Matching Engine | 90% |
| Reconciliation Engine | 85% |
| API Layer | 80% |
| **Overall** | **85%** |

---

## 9. Test Checklist

### Before Release

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] All API tests passing
- [ ] Performance benchmarks met
- [ ] Test coverage above 85%
- [ ] No critical bugs in backlog
- [ ] Load testing completed (10K concurrent users)
- [ ] Oracle → MongoDB reconciliation validated
- [ ] Multi-table reconciliation validated
- [ ] Reference data comparison validated
- [ ] Export functionality tested (CSV, Excel)
- [ ] API documentation generated and verified
- [ ] Security testing completed
- [ ] Docker containers tested
- [ ] Database migrations tested

---

**Document End**

This comprehensive test plan ensures the GenRecon platform is thoroughly validated across all layers and components before deployment.
