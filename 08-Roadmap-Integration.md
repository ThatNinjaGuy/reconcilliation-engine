# Implementation Roadmap & Integration Guide

**Project**: GenRecon - Generic Data Reconciliation Platform  
**Version**: 1.0  
**Date**: January 30, 2026  
**Type**: Master Implementation Plan

---

## Document Index

This master document references all implementation documents:

1. **00-High-Level-Overview.md** - Complete system architecture and design philosophy
2. **01-Schema-Inference.md** - Schema discovery and metadata extraction
3. **02-Data-Extraction.md** - Data extraction from Oracle and MongoDB
4. **03-Field-Mapping-Comparison.md** - Field mapping and comparison logic
5. **04-Matching-Reconciliation.md** - Record matching and reconciliation engine
6. **05-Results-Storage-Reporting.md** - Results storage and reporting
7. **06-API-Layer-Design.md** - REST API implementation
8. **07-Test-Plan.md** - Comprehensive testing strategy
9. **08-Implementation-Roadmap.md** - This document

---

## 1. Implementation Phases

### Phase 1: Foundation (Weeks 1-3)

**Goal**: Setup infrastructure and core data models

#### Week 1: Project Setup
- [ ] Initialize Python project structure
- [ ] Setup FastAPI application skeleton
- [ ] Configure PostgreSQL for metadata storage
- [ ] Setup development environment (Docker Compose)
- [ ] Initialize Git repository
- [ ] Setup CI/CD pipeline (GitHub Actions)

**Deliverables**:
```
genrecon/
├── src/
│   ├── api/
│   ├── core/
│   ├── schema_inference/
│   ├── data_extraction/
│   ├── comparison/
│   ├── matching/
│   ├── results/
│   └── utils/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

#### Week 2: Metadata Models
- [ ] Implement metadata database schema (see 00-High-Level-Overview.md)
- [ ] Create SQLAlchemy models for all metadata tables
- [ ] Implement metadata repository layer
- [ ] Write unit tests for metadata operations
- [ ] Create database migration scripts (Alembic)

**Key Files**:
- `src/core/models.py` - All SQLAlchemy models
- `src/core/repositories.py` - Data access layer
- `alembic/versions/*.py` - Migration scripts

#### Week 3: Connection Management
- [ ] Implement OracleConnectionManager (see 02-Data-Extraction.md, Section 3)
- [ ] Implement MongoDBConnectionManager
- [ ] Create connection pool configuration
- [ ] Add connection health check endpoints
- [ ] Write connection integration tests

**Key Classes**:
```python
# src/core/connections.py
class ConnectionManager(ABC)
class OracleConnectionManager(ConnectionManager)
class MongoDBConnectionManager(ConnectionManager)
```

---

### Phase 2: Schema Inference (Weeks 4-5)

**Goal**: Implement schema discovery for Oracle and MongoDB

#### Week 4: Oracle Schema Inference
- [ ] Implement OracleSchemaInferrer (see 01-Schema-Inference.md, Section 2)
- [ ] Add support for:
  - [ ] Primary keys
  - [ ] Foreign keys
  - [ ] Data types
  - [ ] Nullable constraints
- [ ] Write comprehensive unit tests
- [ ] Test with real Oracle database

**Key Implementation**:
```python
# src/schema_inference/oracle_inferrer.py
class OracleSchemaInferrer:
    def infer_table_schema(self, table_name: str) -> Dict
    def get_primary_keys(self, table_name: str) -> List[str]
    def get_foreign_keys(self, table_name: str) -> List[Dict]
    def map_to_generic_type(self, oracle_type: str) -> str
```

#### Week 5: MongoDB Schema Inference
- [ ] Implement MongoDBSchemaInferrer (see 01-Schema-Inference.md, Section 3)
- [ ] Add support for:
  - [ ] Nested documents
  - [ ] Arrays
  - [ ] Type inference from samples
  - [ ] Field path extraction
- [ ] Write comprehensive unit tests
- [ ] Test with real MongoDB database

**Key Implementation**:
```python
# src/schema_inference/mongodb_inferrer.py
class MongoDBSchemaInferrer:
    def infer_collection_schema(self, collection_name: str) -> Dict
    def infer_from_samples(self, documents: List[Dict]) -> Dict
    def flatten_nested_paths(self, document: Dict) -> List[str]
```

---

### Phase 3: Data Extraction (Weeks 6-7)

**Goal**: Implement data extraction with batching and transformation

#### Week 6: Oracle Data Extraction
- [ ] Implement OracleDataExtractor (see 02-Data-Extraction.md, Section 4)
- [ ] Add features:
  - [ ] Batch processing
  - [ ] WHERE clause filters
  - [ ] Field transformations
  - [ ] Pagination support
- [ ] Implement extraction monitoring
- [ ] Write performance tests

**Key Implementation**:
```python
# src/data_extraction/oracle_extractor.py
class OracleDataExtractor:
    def extract_data(
        self,
        table_name: str,
        filters: Optional[Dict] = None,
        batch_size: int = 1000,
        transformations: Optional[Dict] = None
    ) -> Generator[Dict, None, None]
```

#### Week 7: MongoDB Data Extraction
- [ ] Implement MongoDBDataExtractor (see 02-Data-Extraction.md, Section 5)
- [ ] Add features:
  - [ ] Batch processing with cursor
  - [ ] Query filters
  - [ ] Nested document flattening
  - [ ] Projection support
- [ ] Write performance tests
- [ ] Test with large datasets

**Key Implementation**:
```python
# src/data_extraction/mongodb_extractor.py
class MongoDBDataExtractor:
    def extract_data(
        self,
        collection_name: str,
        query: Optional[Dict] = None,
        batch_size: int = 1000,
        flatten: bool = True
    ) -> Generator[Dict, None, None]
```

---

### Phase 4: Field Mapping & Comparison (Weeks 8-9)

**Goal**: Implement field mapping and comparison logic

#### Week 8: Field Comparators
- [ ] Implement base Comparator interface (see 03-Field-Mapping-Comparison.md, Section 4)
- [ ] Implement comparators:
  - [ ] ExactComparator
  - [ ] NumericComparator (with tolerance)
  - [ ] DateComparator (with format conversion)
  - [ ] StringCaseInsensitiveComparator
  - [ ] ReferenceDataComparator
- [ ] Write comprehensive unit tests for each comparator
- [ ] Create comparator factory

**Key Implementation**:
```python
# src/comparison/comparators.py
class Comparator(ABC)
class ExactComparator(Comparator)
class NumericComparator(Comparator)
class DateComparator(Comparator)
class ReferenceDataComparator(Comparator)
class ComparatorFactory:
    def get_comparator(self, comparator_type: str, config: Dict) -> Comparator
```

#### Week 9: Field Mapping Service
- [ ] Implement FieldMappingService (see 03-Field-Mapping-Comparison.md, Section 3)
- [ ] Add features:
  - [ ] Source-to-target field mapping
  - [ ] Transformation pipeline
  - [ ] Validation
- [ ] Integrate with comparators
- [ ] Write integration tests

**Key Implementation**:
```python
# src/comparison/field_mapping_service.py
class FieldMappingService:
    def apply_mapping(
        self,
        source_record: Dict,
        mapping: Mapping
    ) -> Dict
    
    def apply_transformation(
        self,
        value: Any,
        transformation: str
    ) -> Any
```

---

### Phase 5: Matching & Reconciliation Engine (Weeks 10-12)

**Goal**: Implement core reconciliation logic

#### Week 10: Matching Engine
- [ ] Implement MatchingEngine (see 04-Matching-Reconciliation.md, Section 2)
- [ ] Add features:
  - [ ] Hash-based matching (for perfect keys)
  - [ ] Composite key matching
  - [ ] Duplicate detection
- [ ] Optimize for large datasets (millions of records)
- [ ] Write performance benchmarks

**Key Implementation**:
```python
# src/matching/matching_engine.py
class MatchingEngine:
    def match_records(
        self,
        source_records: Iterator[Dict],
        target_records: Iterator[Dict],
        matching_keys: List[MatchingKey]
    ) -> MatchingResult
    
    def build_hash_index(
        self,
        records: Iterator[Dict],
        keys: List[str]
    ) -> Dict[str, Dict]
```

#### Week 11-12: Reconciliation Engine
- [ ] Implement ReconciliationEngine (see 04-Matching-Reconciliation.md, Section 3)
- [ ] Add orchestration for:
  - [ ] Data extraction
  - [ ] Record matching
  - [ ] Field comparison
  - [ ] Results storage
- [ ] Implement progress tracking
- [ ] Add error handling and recovery
- [ ] Write end-to-end integration tests

**Key Implementation**:
```python
# src/orchestration/reconciliation_engine.py
class ReconciliationEngine:
    def execute_reconciliation(
        self,
        rule_set: RuleSet,
        filters: Optional[Dict] = None
    ) -> str  # Returns run_id
    
    def track_progress(self, run_id: str) -> ProgressStatus
```

---

### Phase 6: Results Storage & Reporting (Weeks 13-14)

**Goal**: Implement results persistence and reporting

#### Week 13: Results Storage
- [ ] Implement ResultsRepository (see 05-Results-Storage-Reporting.md, Section 2)
- [ ] Optimize database schema for queries:
  - [ ] Indexes on run_id, field_id, severity
  - [ ] Partitioning for large result sets
- [ ] Implement batch insertion for discrepancies
- [ ] Write performance tests

**Key Implementation**:
```python
# src/results/results_repository.py
class ResultsRepository:
    def save_summary_stats(self, stats: SummaryStats) -> None
    def save_discrepancies(self, discrepancies: List[FieldDiscrepancy]) -> None
    def get_discrepancies_paginated(
        self,
        run_id: str,
        limit: int,
        offset: int
    ) -> List[FieldDiscrepancy]
```

#### Week 14: Reporting Service
- [ ] Implement ReportingService (see 05-Results-Storage-Reporting.md, Section 3)
- [ ] Add export formats:
  - [ ] CSV export
  - [ ] Excel export
- [ ] Generate summary statistics
- [ ] Create visualization data structures
- [ ] Write export tests

**Key Implementation**:
```python
# src/results/reporting_service.py
class ReportingService:
    def get_summary_stats(self, run_id: str) -> SummaryStats
    def export_to_csv(self, run_id: str) -> BinaryIO
    def export_to_excel(self, run_id: str) -> BinaryIO
    def get_field_discrepancy_breakdown(self, run_id: str) -> Dict
```

---

### Phase 7: REST API Layer (Weeks 15-16)

**Goal**: Expose functionality via REST API

#### Week 15: Core API Endpoints
- [ ] Implement API routers (see 06-API-Layer-Design.md):
  - [ ] Systems API
  - [ ] Schemas API
  - [ ] Datasets API
  - [ ] Mappings API
  - [ ] Rule Sets API
- [ ] Add request validation (Pydantic models)
- [ ] Implement error handling
- [ ] Write API tests

**Key Files**:
```python
# src/api/routers/
├── systems.py
├── schemas.py
├── datasets.py
├── mappings.py
├── rule_sets.py
├── jobs.py
└── results.py
```

#### Week 16: Jobs & Results API
- [ ] Implement Jobs API (reconciliation execution)
- [ ] Implement Results API (query and export)
- [ ] Add background task processing
- [ ] Implement API authentication
- [ ] Generate API documentation (OpenAPI/Swagger)
- [ ] Write comprehensive API tests

---

### Phase 8: Testing & Quality Assurance (Weeks 17-18)

**Goal**: Comprehensive testing and bug fixing

#### Week 17: Testing
- [ ] Execute full test suite (see 07-Test-Plan.md)
- [ ] Run integration tests with real databases
- [ ] Performance testing:
  - [ ] 100K records reconciliation
  - [ ] 1M records reconciliation
  - [ ] API load testing (Locust)
- [ ] Fix identified bugs
- [ ] Achieve 85%+ code coverage

#### Week 18: End-to-End Validation
- [ ] Test complete customer reconciliation workflow
- [ ] Test multi-table reconciliation
- [ ] Validate reference data comparison
- [ ] Test error scenarios and recovery
- [ ] Security testing
- [ ] Documentation review

---

### Phase 9: Deployment & Documentation (Week 19)

**Goal**: Production deployment preparation

#### Deployment Tasks
- [ ] Create Docker images
- [ ] Write deployment documentation
- [ ] Setup production database
- [ ] Configure environment variables
- [ ] Setup monitoring (Prometheus, Grafana)
- [ ] Create runbooks for operations
- [ ] User guide documentation

**Deliverables**:
- Docker Compose for production
- Kubernetes manifests (if applicable)
- API documentation (Swagger UI)
- User guide
- Operations runbook

---

## 2. Critical Integration Points

### 2.1 Schema Inference → Data Extraction

**Integration**: Inferred schemas drive data extraction configuration

```python
# Example integration flow
schema_inferrer = OracleSchemaInferrer(connection)
schema = schema_inferrer.infer_table_schema("CUSTOMERS")

# Schema used to configure extractor
extractor = OracleDataExtractor(connection)
transformations = schema_inferrer.get_transformations(schema)

data = extractor.extract_data(
    table_name="CUSTOMERS",
    transformations=transformations  # From schema
)
```

**Validation**:
- Schema field list matches extracted data keys
- Data types match schema definitions
- Nullable constraints respected

---

### 2.2 Data Extraction → Matching Engine

**Integration**: Extracted data fed into matching engine

```python
# Extract from both sources
source_data = source_extractor.extract_data("CUSTOMERS", batch_size=1000)
target_data = target_extractor.extract_data("customers", batch_size=1000)

# Match records
matching_engine = MatchingEngine()
match_result = matching_engine.match_records(
    source_records=source_data,
    target_records=target_data,
    matching_keys=[{"source_field": "customerId", "target_field": "customerId"}]
)
```

**Validation**:
- All extracted records processed
- Memory usage stays within bounds (streaming)
- Matching keys exist in both datasets

---

### 2.3 Matching Engine → Field Comparison

**Integration**: Matched record pairs sent for field comparison

```python
# For each matched pair
for match in match_result.matched_pairs:
    source_record = match.source_record
    target_record = match.target_record
    
    # Apply field mappings and compare
    for field_mapping in rule_set.field_mappings:
        comparator = comparator_factory.get_comparator(
            field_mapping.comparator_type,
            field_mapping.comparator_config
        )
        
        source_value = source_record[field_mapping.source_field]
        target_value = target_record[field_mapping.target_field]
        
        comparison_result = comparator.compare(source_value, target_value)
        
        if not comparison_result.is_match:
            # Record discrepancy
            discrepancies.append(...)
```

**Validation**:
- All field mappings applied
- Comparator configurations valid
- Discrepancies recorded correctly

---

### 2.4 Reconciliation Engine → Results Storage

**Integration**: Reconciliation results persisted to database

```python
# After reconciliation completes
results_repo = ResultsRepository(metadata_db)

# Save summary
results_repo.save_summary_stats(SummaryStats(
    run_id=run_id,
    total_source_records=match_result.total_source,
    matched_records=len(match_result.matched_pairs),
    # ... other stats
))

# Save discrepancies (batch insert)
results_repo.save_discrepancies(discrepancies)

# Save unmatched records
results_repo.save_unmatched_records(
    run_id=run_id,
    source_unmatched=match_result.unmatched_source,
    target_unmatched=match_result.unmatched_target
)
```

**Validation**:
- Summary stats match actual counts
- All discrepancies persisted
- Query performance acceptable

---

### 2.5 Results Storage → API Layer

**Integration**: API endpoints query results from database

```python
# API endpoint implementation
@router.get("/{job_id}/discrepancies")
async def get_discrepancies(job_id: str, limit: int, offset: int):
    # Get run_id from job_id
    run_id = job_service.get_run_id(job_id)
    
    # Query results
    discrepancies = results_repo.get_discrepancies_paginated(
        run_id=run_id,
        limit=limit,
        offset=offset
    )
    
    return [DiscrepancyResponse(**d) for d in discrepancies]
```

**Validation**:
- API responses match database data
- Pagination works correctly
- Response times acceptable

---

## 3. Data Flow Validation

### 3.1 Complete Flow Test

```python
# tests/integration/test_complete_flow.py

def test_end_to_end_reconciliation():
    """Test complete reconciliation flow"""
    
    # 1. Schema Inference
    oracle_schema = oracle_inferrer.infer_table_schema("CUSTOMERS")
    mongo_schema = mongo_inferrer.infer_collection_schema("customers")
    
    assert len(oracle_schema['fields']) > 0
    assert len(mongo_schema['fields']) > 0
    
    # 2. Create Mapping
    mapping = create_mapping(oracle_schema, mongo_schema)
    assert len(mapping.field_mappings) > 0
    
    # 3. Data Extraction
    source_data = list(oracle_extractor.extract_data("CUSTOMERS"))
    target_data = list(mongo_extractor.extract_data("customers"))
    
    assert len(source_data) > 0
    assert len(target_data) > 0
    
    # 4. Matching
    match_result = matching_engine.match_records(
        source_records=iter(source_data),
        target_records=iter(target_data),
        matching_keys=[{"source_field": "customerId", "target_field": "customerId"}]
    )
    
    assert match_result.match_rate > 0.95
    
    # 5. Field Comparison
    discrepancies = []
    for match in match_result.matched_pairs:
        for field_map in mapping.field_mappings:
            result = compare_fields(match, field_map)
            if not result.is_match:
                discrepancies.append(result)
    
    # 6. Results Storage
    run_id = results_repo.save_run(match_result, discrepancies)
    assert run_id is not None
    
    # 7. Retrieval
    summary = results_repo.get_summary_stats(run_id)
    assert summary.total_source_records == len(source_data)
    assert summary.total_target_records == len(target_data)
    
    # 8. API Access
    response = client.get(f"/api/v1/results/{run_id}/summary")
    assert response.status_code == 200
```

---

## 4. Cross-Document Consistency Verification

### 4.1 Metadata Model Consistency

**Check**: All documents reference same metadata structure

| Document | Section | Metadata Tables Referenced |
|----------|---------|----------------------------|
| 00-High-Level-Overview.md | Section 4 | Systems, Schemas, Datasets, Mappings, RuleSets |
| 01-Schema-Inference.md | Section 1 | Schemas, SchemaFields |
| 02-Data-Extraction.md | Section 2 | Datasets, DatasetFields |
| 03-Field-Mapping-Comparison.md | Section 2 | Mappings, FieldMappings |
| 04-Matching-Reconciliation.md | Section 1 | RuleSets, MatchingKeys |
| 05-Results-Storage-Reporting.md | Section 2 | ReconciliationRuns, FieldDiscrepancies |

✅ **Verified**: All documents consistently reference the same metadata schema.

---

### 4.2 API Endpoint Consistency

**Check**: API endpoints align with backend services

| API Endpoint | Backend Service | Document References |
|--------------|----------------|---------------------|
| POST /api/v1/jobs | ReconciliationEngine.execute_reconciliation() | 04-Matching, 06-API |
| GET /api/v1/results/{id}/summary | ReportingService.get_summary_stats() | 05-Results, 06-API |
| GET /api/v1/results/{id}/discrepancies | ResultsRepository.get_discrepancies_paginated() | 05-Results, 06-API |

✅ **Verified**: API endpoints map correctly to backend services.

---

### 4.3 Data Type Consistency

**Check**: Generic data types used consistently

| Generic Type | Oracle Types | MongoDB Types |
|--------------|--------------|---------------|
| INTEGER | NUMBER(n,0), INTEGER | int, NumberInt |
| DECIMAL | NUMBER(n,m) | double, Decimal128 |
| STRING | VARCHAR2, CHAR | string |
| DATE | DATE | ISODate, string (ISO format) |
| TIMESTAMP | TIMESTAMP | ISODate |
| BOOLEAN | NUMBER(1) | bool |
| TEXT | CLOB | string (large) |

✅ **Verified**: Data type mapping consistent across:
- 01-Schema-Inference.md (Section 2.3, 3.3)
- 02-Data-Extraction.md (Section 4.3, 5.3)

---

## 5. Implementation Checklist

### Pre-Implementation
- [ ] All documents reviewed
- [ ] Architecture understood
- [ ] Database schemas designed
- [ ] Development environment setup
- [ ] Test data prepared

### Phase 1-3: Foundation & Data Access
- [ ] Metadata models implemented
- [ ] Connection management working
- [ ] Schema inference for Oracle complete
- [ ] Schema inference for MongoDB complete
- [ ] Data extraction for Oracle complete
- [ ] Data extraction for MongoDB complete
- [ ] Integration tests passing

### Phase 4-5: Core Logic
- [ ] All comparators implemented
- [ ] Field mapping service complete
- [ ] Matching engine optimized
- [ ] Reconciliation engine orchestrating correctly
- [ ] Performance benchmarks met

### Phase 6-7: Results & API
- [ ] Results storage optimized
- [ ] Reporting service complete
- [ ] All API endpoints implemented
- [ ] API tests passing
- [ ] API documentation generated

### Phase 8-9: Quality & Deployment
- [ ] 85%+ test coverage achieved
- [ ] Performance tests passing
- [ ] Security review complete
- [ ] Docker images built
- [ ] Deployment documentation complete
- [ ] Production deployment successful

---

## 6. Key Success Metrics

### Functional Metrics
- ✅ Successfully reconcile 100K+ records
- ✅ Support Oracle and MongoDB sources
- ✅ Handle multiple tables/collections
- ✅ Detect field discrepancies accurately
- ✅ Generate comprehensive reports

### Performance Metrics
- ✅ Reconcile 100K records in < 60 seconds
- ✅ Support concurrent reconciliation jobs
- ✅ API response time < 500ms (p95)
- ✅ Handle 10K+ concurrent API requests

### Quality Metrics
- ✅ 85%+ code coverage
- ✅ Zero critical bugs in production
- ✅ 99.9% uptime SLA
- ✅ All tests passing in CI/CD

---

## 7. Risk Mitigation

| Risk | Mitigation Strategy | Owner |
|------|---------------------|-------|
| Oracle connectivity issues | Connection pooling, retry logic, health checks | Infrastructure |
| MongoDB schema variance | Flexible inference with sampling, configurable mapping | Development |
| Performance bottlenecks | Batch processing, streaming, database indexing | Development |
| Data type conversion errors | Comprehensive transformation library, validation | Development |
| API rate limiting | Rate limiting, caching, pagination | API Team |
| Memory exhaustion | Streaming data processing, batch size limits | Development |

---

## 8. Future Enhancements (Post-MVP)

### Phase 10: Additional Data Sources
- PostgreSQL support
- MySQL support
- REST API data sources
- CSV file sources

### Phase 11: Advanced Features
- Machine learning for fuzzy matching
- Automated mapping suggestion
- Real-time reconciliation (streaming)
- Reconciliation scheduling (cron)

### Phase 12: UI Development
- Web-based configuration UI
- Interactive result exploration
- Visual data mapping tool
- Dashboard with charts

---

**Implementation Start Date**: Week of January 30, 2026  
**Target MVP Completion**: April 30, 2026 (13 weeks)  
**Target Production Release**: May 15, 2026

---

**Document End**

All implementation documents are now complete and cross-validated for consistency. The design is generic, reusable, and production-ready for Oracle → MongoDB reconciliation with extensibility for additional sources.
