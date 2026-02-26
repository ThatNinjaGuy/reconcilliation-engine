# Connector Layer - Detailed Design Document

**Component**: Data Connector Layer  
**Version**: 1.0  
**Date**: January 30, 2026  
**Dependencies**: cx_Oracle, PyMongo, SQLAlchemy

---

## 1. Component Overview

The Connector Layer abstracts data access from heterogeneous systems (Oracle, MongoDB) into a unified **Canonical Row Model**. This layer ensures that the rest of the platform (transformation, reconciliation engines) works with consistent data structures regardless of source type.

**Key Responsibilities**:
- Connect to external systems using system-specific protocols
- Read data in batches for memory efficiency
- Map physical schemas to logical schemas
- Type conversion and normalization
- Error handling and connection pooling

---

## 2. Architecture

### 2.1 Design Pattern: Strategy + Factory

```python
                    ┌──────────────────────┐
                    │  ConnectorFactory    │
                    └──────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
            ┌───────▼──────┐  ┌───────▼──────┐
            │ OracleReader │  │  MongoReader │
            └──────────────┘  └──────────────┘
                    │                 │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ CanonicalRow    │
                    └─────────────────┘
```

### 2.2 Base Interface

```python
# src/connectors/base.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class CanonicalRow:
    """
    Unified internal representation of a data row.
    All connectors must produce this format.
    """
    fields: Dict[str, Any]  # field_id -> value mapping
    metadata: Dict[str, Any] = None  # Source metadata (row number, timestamp, etc.)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def get_field(self, field_id: str, default: Any = None) -> Any:
        """Get field value with optional default"""
        return self.fields.get(field_id, default)
    
    def set_field(self, field_id: str, value: Any):
        """Set field value"""
        self.fields[field_id] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Export as dictionary"""
        return {
            "fields": self.fields,
            "metadata": self.metadata
        }

@dataclass
class BatchResult:
    """Result of a batch read operation"""
    rows: List[CanonicalRow]
    cursor: Optional[Any]  # Cursor for next batch
    has_more: bool
    batch_metadata: Dict[str, Any]  # Stats: row count, read time, etc.

class DatasetReader(ABC):
    """
    Abstract base class for all dataset readers.
    Implements the Strategy pattern.
    """
    
    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        """
        Initialize reader with system connection and schema information.
        
        Args:
            system_config: Decrypted connection configuration
            schema: Logical schema definition from metadata
        """
        self.system_config = system_config
        self.schema = schema
        self.connection = None
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source.
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close connection to the data source"""
        pass
    
    @abstractmethod
    def fetch_batch(
        self, 
        dataset: Dict[str, Any], 
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None
    ) -> BatchResult:
        """
        Fetch a batch of records from the dataset.
        
        Args:
            dataset: Dataset metadata (physical_name, partition_config, etc.)
            cursor: Cursor from previous batch (None for first batch)
            batch_size: Number of records per batch
            filters: Optional runtime filters (date range, ID range, etc.)
        
        Returns:
            BatchResult containing canonical rows and next cursor
        """
        pass
    
    @abstractmethod
    def get_row_count(
        self, 
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Get total row count for the dataset.
        
        Args:
            dataset: Dataset metadata
            filters: Optional filters
        
        Returns:
            Total number of rows
        """
        pass
    
    @abstractmethod
    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that logical schema matches physical schema.
        
        Args:
            dataset: Dataset metadata
        
        Returns:
            Validation result with warnings/errors
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
```

---

## 3. Oracle Connector

### 3.1 Implementation

```python
# src/connectors/oracle_reader.py

import cx_Oracle
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, date
from decimal import Decimal

from .base import DatasetReader, CanonicalRow, BatchResult

logger = logging.getLogger(__name__)

class OracleDatasetReader(DatasetReader):
    """
    Oracle database connector using cx_Oracle and SQLAlchemy.
    """
    
    # Oracle to Python type mapping
    ORACLE_TYPE_MAP = {
        'VARCHAR2': str,
        'CHAR': str,
        'NVARCHAR2': str,
        'NUMBER': Decimal,
        'INTEGER': int,
        'FLOAT': float,
        'DATE': datetime,
        'TIMESTAMP': datetime,
        'CLOB': str,
        'BLOB': bytes
    }
    
    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self.engine = None
        self.connection_pool = None
    
    def connect(self) -> bool:
        """Establish Oracle connection using SQLAlchemy"""
        try:
            # Build connection string
            host = self.system_config['host']
            port = self.system_config['port']
            service_name = self.system_config.get('service_name')
            sid = self.system_config.get('sid')
            username = self.system_config['username']
            password = self.system_config['password']
            
            # DSN construction
            if service_name:
                dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
            else:
                dsn = cx_Oracle.makedsn(host, port, sid=sid)
            
            # Connection string for SQLAlchemy
            connection_string = f"oracle+cx_oracle://{username}:{password}@{dsn}"
            
            # Create engine with connection pooling
            pool_size = self.system_config.get('pool_size', 10)
            max_overflow = self.system_config.get('pool_max_overflow', 20)
            
            self.engine = create_engine(
                connection_string,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,  # Verify connections before using
                echo=False
            )
            
            # Test connection
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 FROM DUAL"))
                result.fetchone()
            
            logger.info(f"Successfully connected to Oracle: {host}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Oracle: {str(e)}")
            raise ConnectionError(f"Oracle connection failed: {str(e)}")
    
    def disconnect(self):
        """Close Oracle connection"""
        if self.engine:
            self.engine.dispose()
            logger.info("Oracle connection closed")
    
    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None
    ) -> BatchResult:
        """
        Fetch batch of records from Oracle table.
        
        Cursor format: {"offset": int, "last_id": Any}
        """
        start_time = datetime.now()
        
        # Extract dataset info
        table_name = dataset['physical_name']
        filter_config = dataset.get('filter_config', {})
        
        # Initialize cursor
        offset = cursor['offset'] if cursor else 0
        
        # Build SELECT query
        query = self._build_select_query(
            table_name=table_name,
            schema=self.schema,
            offset=offset,
            batch_size=batch_size,
            base_filters=filter_config,
            runtime_filters=filters
        )
        
        # Execute query
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            column_names = result.keys()
        
        # Convert to CanonicalRows
        canonical_rows = []
        for idx, row in enumerate(rows):
            canonical_row = self._convert_to_canonical(
                row=row,
                column_names=column_names,
                row_number=offset + idx
            )
            canonical_rows.append(canonical_row)
        
        # Prepare next cursor
        has_more = len(rows) == batch_size
        next_cursor = {"offset": offset + len(rows)} if has_more else None
        
        # Batch metadata
        batch_metadata = {
            "source": "oracle",
            "table": table_name,
            "rows_fetched": len(rows),
            "offset": offset,
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        return BatchResult(
            rows=canonical_rows,
            cursor=next_cursor,
            has_more=has_more,
            batch_metadata=batch_metadata
        )
    
    def _build_select_query(
        self,
        table_name: str,
        schema: Dict[str, Any],
        offset: int,
        batch_size: int,
        base_filters: Dict[str, Any],
        runtime_filters: Optional[Dict[str, Any]]
    ) -> str:
        """Build optimized SELECT query with pagination"""
        
        # Extract columns from schema
        fields = schema['fields']
        select_columns = []
        
        for field in fields:
            oracle_column = field['physical_mapping'].get('oracle_column')
            if oracle_column:
                # Use alias for consistency
                select_columns.append(f"{oracle_column} AS {field['field_id']}")
        
        select_clause = ", ".join(select_columns)
        
        # Build WHERE clause
        where_clauses = []
        
        # Base filters from dataset config
        if base_filters and base_filters.get('where_clause'):
            where_clauses.append(base_filters['where_clause'])
        
        # Runtime filters
        if runtime_filters:
            if 'date_from' in runtime_filters and 'date_column' in runtime_filters:
                where_clauses.append(
                    f"{runtime_filters['date_column']} >= "
                    f"TO_DATE('{runtime_filters['date_from']}', 'YYYY-MM-DD')"
                )
            if 'date_to' in runtime_filters and 'date_column' in runtime_filters:
                where_clauses.append(
                    f"{runtime_filters['date_column']} <= "
                    f"TO_DATE('{runtime_filters['date_to']}', 'YYYY-MM-DD')"
                )
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Pagination using OFFSET/FETCH (Oracle 12c+)
        query = f"""
            SELECT {select_clause}
            FROM {table_name}
            {where_clause}
            ORDER BY ROWID
            OFFSET {offset} ROWS
            FETCH NEXT {batch_size} ROWS ONLY
        """
        
        return query
    
    def _convert_to_canonical(
        self,
        row: Any,
        column_names: List[str],
        row_number: int
    ) -> CanonicalRow:
        """Convert Oracle row to CanonicalRow"""
        
        fields = {}
        for idx, column_name in enumerate(column_names):
            value = row[idx]
            
            # Type conversion
            if isinstance(value, cx_Oracle.LOB):
                value = value.read()
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                # Keep as Decimal for precision
                pass
            
            fields[column_name] = value
        
        metadata = {
            "source": "oracle",
            "row_number": row_number,
            "fetched_at": datetime.now().isoformat()
        }
        
        return CanonicalRow(fields=fields, metadata=metadata)
    
    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get total row count"""
        
        table_name = dataset['physical_name']
        filter_config = dataset.get('filter_config', {})
        
        # Build WHERE clause
        where_clauses = []
        if filter_config and filter_config.get('where_clause'):
            where_clauses.append(filter_config['where_clause'])
        
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        query = f"SELECT COUNT(*) as cnt FROM {table_name} {where_clause}"
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            count = result.fetchone()[0]
        
        return count
    
    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate logical schema against Oracle table schema.
        Checks:
        - All mapped columns exist in table
        - Data types are compatible
        - Key columns exist
        """
        
        table_name = dataset['physical_name']
        schema_fields = self.schema['fields']
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Get Oracle table schema
        query = f"""
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = UPPER('{table_name}')
        """
        
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            oracle_columns = {row[0]: row for row in result.fetchall()}
        
        # Validate each schema field
        for field in schema_fields:
            oracle_column = field['physical_mapping'].get('oracle_column')
            
            if not oracle_column:
                # Derived field, skip physical validation
                continue
            
            if oracle_column.upper() not in oracle_columns:
                validation_result['valid'] = False
                validation_result['errors'].append(
                    f"Column {oracle_column} not found in table {table_name}"
                )
                continue
            
            oracle_col_info = oracle_columns[oracle_column.upper()]
            oracle_type = oracle_col_info[1]
            
            # Type compatibility check (simplified)
            expected_python_type = self.ORACLE_TYPE_MAP.get(oracle_type)
            # Add logic to compare with field['data_type']
        
        return validation_result

    def test_connection(self) -> Dict[str, Any]:
        """Test Oracle connection and return diagnostics"""
        try:
            self.connect()
            
            with self.engine.connect() as conn:
                # Get Oracle version
                result = conn.execute(text("SELECT * FROM v$version WHERE banner LIKE 'Oracle%'"))
                version = result.fetchone()[0]
                
                # Get current user
                result = conn.execute(text("SELECT USER FROM DUAL"))
                user = result.fetchone()[0]
            
            return {
                "status": "success",
                "version": version,
                "user": user,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            self.disconnect()
```

---

## 4. MongoDB Connector

### 4.1 Implementation

```python
# src/connectors/mongo_reader.py

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from bson import ObjectId

from .base import DatasetReader, CanonicalRow, BatchResult

logger = logging.getLogger(__name__)

class MongoDatasetReader(DatasetReader):
    """
    MongoDB connector using PyMongo.
    Handles nested documents and JSON path extraction.
    """
    
    # MongoDB to Python type mapping
    MONGO_TYPE_MAP = {
        'string': str,
        'int': int,
        'long': int,
        'double': float,
        'decimal': float,
        'bool': bool,
        'date': datetime,
        'objectId': str,
        'array': list,
        'object': dict
    }
    
    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self.client = None
        self.database = None
    
    def connect(self) -> bool:
        """Establish MongoDB connection"""
        try:
            connection_string = self.system_config['connection_string']
            database_name = self.system_config['database']
            
            # Connection options
            max_pool_size = self.system_config.get('max_pool_size', 50)
            timeout_ms = self.system_config.get('timeout_ms', 30000)
            
            # Create client
            self.client = MongoClient(
                connection_string,
                maxPoolSize=max_pool_size,
                serverSelectionTimeoutMS=timeout_ms
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database
            self.database = self.client[database_name]
            
            logger.info(f"Successfully connected to MongoDB: {database_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise ConnectionError(f"MongoDB connection failed: {str(e)}")
    
    def disconnect(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
    
    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None
    ) -> BatchResult:
        """
        Fetch batch of documents from MongoDB collection.
        
        Cursor format: {"last_id": ObjectId}
        """
        start_time = datetime.now()
        
        # Extract dataset info
        collection_name = dataset['physical_name']
        filter_config = dataset.get('filter_config', {})
        
        # Get collection
        collection = self.database[collection_name]
        
        # Build query
        query = self._build_query(
            base_filters=filter_config,
            runtime_filters=filters,
            cursor=cursor
        )
        
        # Build projection (for efficiency)
        projection = self._build_projection(self.schema)
        
        # Execute query
        documents = list(collection.find(query, projection).limit(batch_size))
        
        # Convert to CanonicalRows
        canonical_rows = []
        for idx, doc in enumerate(documents):
            canonical_row = self._convert_to_canonical(doc, idx)
            canonical_rows.append(canonical_row)
        
        # Prepare next cursor
        has_more = len(documents) == batch_size
        next_cursor = None
        if has_more and documents:
            last_id = documents[-1].get('_id')
            next_cursor = {"last_id": last_id}
        
        # Batch metadata
        batch_metadata = {
            "source": "mongodb",
            "collection": collection_name,
            "rows_fetched": len(documents),
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        return BatchResult(
            rows=canonical_rows,
            cursor=next_cursor,
            has_more=has_more,
            batch_metadata=batch_metadata
        )
    
    def _build_query(
        self,
        base_filters: Dict[str, Any],
        runtime_filters: Optional[Dict[str, Any]],
        cursor: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build MongoDB query document"""
        
        query = {}
        
        # Base filters from dataset config
        if base_filters and base_filters.get('query'):
            query.update(base_filters['query'])
        
        # Cursor-based pagination
        if cursor and 'last_id' in cursor:
            query['_id'] = {'$gt': cursor['last_id']}
        
        # Runtime filters
        if runtime_filters:
            if 'date_from' in runtime_filters and 'date_field' in runtime_filters:
                date_field = runtime_filters['date_field']
                query[date_field] = query.get(date_field, {})
                query[date_field]['$gte'] = datetime.fromisoformat(runtime_filters['date_from'])
            
            if 'date_to' in runtime_filters and 'date_field' in runtime_filters:
                date_field = runtime_filters['date_field']
                query[date_field] = query.get(date_field, {})
                query[date_field]['$lte'] = datetime.fromisoformat(runtime_filters['date_to'])
        
        return query
    
    def _build_projection(self, schema: Dict[str, Any]) -> Dict[str, int]:
        """Build MongoDB projection to fetch only required fields"""
        
        projection = {}
        fields = schema['fields']
        
        for field in fields:
            mongo_path = field['physical_mapping'].get('mongo_path')
            if mongo_path:
                # Convert dot notation to nested dict (simplified)
                # For now, just project top-level or use aggregation
                projection[mongo_path] = 1
        
        projection['_id'] = 1  # Always include _id for cursor
        
        return projection
    
    def _convert_to_canonical(self, document: Dict[str, Any], row_number: int) -> CanonicalRow:
        """
        Convert MongoDB document to CanonicalRow.
        Handles nested path extraction.
        """
        
        fields = {}
        schema_fields = self.schema['fields']
        
        for field in schema_fields:
            mongo_path = field['physical_mapping'].get('mongo_path')
            if mongo_path:
                # Extract value using JSON path
                value = self._extract_nested_value(document, mongo_path)
                
                # Type conversion
                value = self._convert_value(value, field['data_type'])
                
                fields[field['field_id']] = value
        
        metadata = {
            "source": "mongodb",
            "_id": str(document.get('_id')),
            "row_number": row_number,
            "fetched_at": datetime.now().isoformat()
        }
        
        return CanonicalRow(fields=fields, metadata=metadata)
    
    def _extract_nested_value(self, document: Dict[str, Any], path: str) -> Any:
        """
        Extract value from nested document using dot notation.
        
        Example: "customer.address.city" from {"customer": {"address": {"city": "Mumbai"}}}
        """
        keys = path.split('.')
        value = document
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                value = None
            
            if value is None:
                break
        
        return value
    
    def _convert_value(self, value: Any, target_type: str) -> Any:
        """Convert MongoDB value to target type"""
        
        if value is None:
            return None
        
        if target_type == 'STRING':
            if isinstance(value, ObjectId):
                return str(value)
            return str(value)
        
        elif target_type == 'INTEGER':
            return int(value)
        
        elif target_type == 'DECIMAL':
            return float(value)
        
        elif target_type == 'TIMESTAMP':
            if isinstance(value, datetime):
                return value.isoformat()
            return value
        
        elif target_type == 'BOOLEAN':
            return bool(value)
        
        return value
    
    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Get document count"""
        
        collection_name = dataset['physical_name']
        filter_config = dataset.get('filter_config', {})
        
        collection = self.database[collection_name]
        
        query = self._build_query(
            base_filters=filter_config,
            runtime_filters=filters,
            cursor=None
        )
        
        count = collection.count_documents(query)
        return count
    
    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate logical schema against MongoDB collection.
        Samples documents to infer schema.
        """
        
        collection_name = dataset['physical_name']
        schema_fields = self.schema['fields']
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        collection = self.database[collection_name]
        
        # Sample documents
        sample_docs = list(collection.find().limit(100))
        
        if not sample_docs:
            validation_result['warnings'].append(
                f"Collection {collection_name} is empty, cannot validate schema"
            )
            return validation_result
        
        # Check each schema field exists in sample
        for field in schema_fields:
            mongo_path = field['physical_mapping'].get('mongo_path')
            
            if not mongo_path:
                continue
            
            found_count = 0
            for doc in sample_docs:
                value = self._extract_nested_value(doc, mongo_path)
                if value is not None:
                    found_count += 1
            
            if found_count == 0:
                validation_result['errors'].append(
                    f"Path {mongo_path} not found in any sample documents"
                )
                validation_result['valid'] = False
            elif found_count < len(sample_docs) * 0.5:
                validation_result['warnings'].append(
                    f"Path {mongo_path} found in only {found_count}/{len(sample_docs)} documents"
                )
        
        return validation_result
```

---

## 5. Connector Factory

```python
# src/connectors/factory.py

from typing import Dict, Any
from .base import DatasetReader
from .oracle_reader import OracleDatasetReader
from .mongo_reader import MongoDatasetReader

class ConnectorFactory:
    """
    Factory for creating appropriate connector instances.
    Implements the Factory pattern.
    """
    
    _readers = {
        'ORACLE': OracleDatasetReader,
        'MONGODB': MongoDatasetReader,
        # Future: 'FILE': FileDatasetReader, 'API': APIDatasetReader
    }
    
    @classmethod
    def create_reader(
        cls,
        system_type: str,
        system_config: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> DatasetReader:
        """
        Create appropriate reader for system type.
        
        Args:
            system_type: 'ORACLE', 'MONGODB', etc.
            system_config: Decrypted connection configuration
            schema: Logical schema definition
        
        Returns:
            DatasetReader instance
        
        Raises:
            ValueError: If system_type not supported
        """
        reader_class = cls._readers.get(system_type)
        
        if not reader_class:
            raise ValueError(f"Unsupported system type: {system_type}")
        
        return reader_class(system_config, schema)
    
    @classmethod
    def register_reader(cls, system_type: str, reader_class: type):
        """
        Register a new reader type (for extensibility).
        
        Args:
            system_type: System type identifier
            reader_class: DatasetReader subclass
        """
        cls._readers[system_type] = reader_class
```

---

## 6. Usage Example

```python
# Example: Using connectors in reconciliation flow

from src.connectors.factory import ConnectorFactory
from src.metadata.repositories import SystemRepository, DatasetRepository, SchemaRepository

# 1. Load metadata
system_repo = SystemRepository(db_session)
dataset_repo = DatasetRepository(db_session)
schema_repo = SchemaRepository(db_session)

# 2. Get source (Oracle) dataset
source_dataset = dataset_repo.get_by_id("customer_oracle")
source_system = system_repo.get_by_id(source_dataset.system_id)
source_schema = schema_repo.get_by_id(source_dataset.schema_id)

# 3. Create Oracle reader
oracle_reader = ConnectorFactory.create_reader(
    system_type=source_system.system_type,
    system_config=source_system.connection_config,  # Already decrypted
    schema=source_schema
)

# 4. Read data in batches
batch_size = 10000
cursor = None

with oracle_reader:
    while True:
        batch_result = oracle_reader.fetch_batch(
            dataset=source_dataset,
            cursor=cursor,
            batch_size=batch_size
        )
        
        # Process canonical rows
        for row in batch_result.rows:
            print(row.fields)
        
        # Check if more data
        if not batch_result.has_more:
            break
        
        cursor = batch_result.cursor
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/connectors/test_oracle_reader.py

import pytest
from src.connectors.oracle_reader import OracleDatasetReader
from src.connectors.base import CanonicalRow

@pytest.fixture
def oracle_config():
    return {
        "host": "localhost",
        "port": 1521,
        "service_name": "XEPDB1",
        "username": "test_user",
        "password": "test_pass",
        "pool_size": 5
    }

@pytest.fixture
def test_schema():
    return {
        "schema_id": "customer_schema",
        "fields": [
            {
                "field_id": "customer_id",
                "data_type": "STRING",
                "physical_mapping": {"oracle_column": "CUST_ID"}
            },
            {
                "field_id": "full_name",
                "data_type": "STRING",
                "physical_mapping": {"oracle_column": "FULL_NAME"}
            }
        ]
    }

def test_oracle_connection(oracle_config, test_schema):
    """Test Oracle connection establishment"""
    reader = OracleDatasetReader(oracle_config, test_schema)
    assert reader.connect() == True
    reader.disconnect()

def test_oracle_fetch_batch(oracle_config, test_schema):
    """Test batch fetching from Oracle"""
    reader = OracleDatasetReader(oracle_config, test_schema)
    
    dataset = {
        "physical_name": "CUSTOMERS",
        "filter_config": {}
    }
    
    with reader:
        result = reader.fetch_batch(dataset, batch_size=100)
        
        assert len(result.rows) <= 100
        assert all(isinstance(row, CanonicalRow) for row in result.rows)
        assert "source" in result.batch_metadata
```

### 7.2 Integration Tests

```python
# tests/connectors/test_connector_integration.py

def test_oracle_to_mongo_flow(db_session):
    """Test reading from Oracle and MongoDB with same schema"""
    
    # Setup: Create metadata for Oracle and Mongo datasets with same logical schema
    # ...
    
    # Create readers
    oracle_reader = ConnectorFactory.create_reader("ORACLE", oracle_config, schema)
    mongo_reader = ConnectorFactory.create_reader("MONGODB", mongo_config, schema)
    
    # Fetch from both
    with oracle_reader, mongo_reader:
        oracle_batch = oracle_reader.fetch_batch(oracle_dataset, batch_size=10)
        mongo_batch = mongo_reader.fetch_batch(mongo_dataset, batch_size=10)
        
        # Both should produce CanonicalRows with same field_ids
        assert set(oracle_batch.rows[0].fields.keys()) == set(mongo_batch.rows[0].fields.keys())
```

---

## 8. Performance Optimization

### 8.1 Connection Pooling

- Oracle: SQLAlchemy connection pool (configured per system)
- MongoDB: PyMongo connection pool (max_pool_size parameter)

### 8.2 Batch Size Tuning

- Default: 10,000 rows per batch
- Configurable per dataset or job
- Memory consideration: `batch_size * avg_row_size < available_memory`

### 8.3 Indexing Requirements

**Oracle**:
- Matching key columns must have indexes
- Composite index on (matching_key, filter_column) for filtered queries

**MongoDB**:
- Compound index on matching key fields
- Index on date fields used in filters
- Use covered queries where possible (projection from index only)

---

## 9. Error Handling

```python
# src/connectors/exceptions.py

class ConnectorError(Exception):
    """Base exception for connector errors"""
    pass

class ConnectionError(ConnectorError):
    """Failed to establish connection"""
    pass

class QueryError(ConnectorError):
    """Query execution failed"""
    pass

class SchemaValidationError(ConnectorError):
    """Schema validation failed"""
    pass

class DataConversionError(ConnectorError):
    """Failed to convert data type"""
    pass
```

---

**Document End**

*Next Component*: Transformation Engine Design
