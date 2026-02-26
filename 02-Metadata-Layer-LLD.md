# Metadata Management Layer - Detailed Design Document

**Component**: Metadata Management Layer  
**Version**: 1.0  
**Date**: January 30, 2026  
**Dependencies**: PostgreSQL 15+

---

## 1. Component Overview

The Metadata Management Layer is the **control plane** of GenRecon. It stores all configuration that drives reconciliation behavior: system connections, schemas, mappings, reference datasets, and reconciliation rules.

**Key Principle**: Everything is metadata-driven. No hardcoded table names, field names, or transformation logic in code.

---

## 2. Database Schema Design

### 2.1 Entity Relationship Diagram

```
┌──────────────┐
│   System     │──┐
└──────────────┘  │
                  │ 1:N
                  ↓
┌──────────────┐  
│   Dataset    │──┐
└──────────────┘  │
                  │ N:1
                  ↓
┌──────────────┐
│   Schema     │
└──────────────┘
                  
┌──────────────┐       ┌──────────────┐
│   Mapping    │←─────→│ FieldMapping │
└──────────────┘  1:N  └──────────────┘
       │                       │
       │                       │ N:1
       ↓                       ↓
┌──────────────┐       ┌──────────────┐
│RuleSet       │       │  Transform   │
└──────────────┘       │   Step       │
       │               └──────────────┘
       │ 1:N                  │ N:1
       ↓                      ↓
┌──────────────┐       ┌──────────────┐
│ComparisonRule│       │  Reference   │
└──────────────┘       │   Dataset    │
                       └──────────────┘
```

### 2.2 Table Definitions

#### Table: `systems`

Stores connection information for data sources/targets.

```sql
CREATE TABLE systems (
    system_id VARCHAR(100) PRIMARY KEY,
    system_name VARCHAR(200) NOT NULL,
    system_type VARCHAR(50) NOT NULL,  -- 'ORACLE', 'MONGODB', 'FILE', 'API'
    description TEXT,
    connection_config JSONB NOT NULL,  -- Encrypted credentials
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    CONSTRAINT chk_system_type CHECK (system_type IN ('ORACLE', 'MONGODB', 'FILE', 'API'))
);

CREATE INDEX idx_systems_type ON systems(system_type);
CREATE INDEX idx_systems_active ON systems(is_active);
```

**connection_config JSONB Structure**:

Oracle:
```json
{
  "host": "oracle.example.com",
  "port": 1521,
  "service_name": "ORCL",
  "username": "recon_user",
  "password_encrypted": "AES256_encrypted_value",
  "pool_size": 10,
  "pool_max_overflow": 20,
  "encoding": "UTF-8"
}
```

MongoDB:
```json
{
  "connection_string_encrypted": "mongodb://encrypted_connection",
  "database": "core_banking",
  "auth_source": "admin",
  "replica_set": "rs0",
  "read_preference": "secondary",
  "max_pool_size": 50,
  "timeout_ms": 30000
}
```

#### Table: `schemas`

Logical field definitions for datasets.

```sql
CREATE TABLE schemas (
    schema_id VARCHAR(100) PRIMARY KEY,
    schema_name VARCHAR(200) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    fields JSONB NOT NULL,  -- Array of field definitions
    constraints JSONB,      -- Schema-level constraints
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    CONSTRAINT chk_version CHECK (version > 0)
);

CREATE INDEX idx_schemas_active ON schemas(is_active);
CREATE INDEX idx_schemas_version ON schemas(schema_id, version);
```

**fields JSONB Structure**:

```json
{
  "fields": [
    {
      "field_id": "customer_id",
      "field_name": "customerId",
      "data_type": "STRING",
      "max_length": 50,
      "is_nullable": false,
      "is_key": true,
      "description": "Unique customer identifier",
      "physical_mapping": {
        "oracle_column": "CUST_ID",
        "mongo_path": "customer.id"
      }
    },
    {
      "field_id": "full_name",
      "field_name": "fullName",
      "data_type": "STRING",
      "max_length": 200,
      "is_nullable": false,
      "is_key": false,
      "physical_mapping": {
        "oracle_column": null,  -- Derived field
        "mongo_path": "customer.name.full"
      }
    },
    {
      "field_id": "account_balance",
      "field_name": "accountBalance",
      "data_type": "DECIMAL",
      "precision": 18,
      "scale": 2,
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {
        "oracle_column": "ACCT_BALANCE",
        "mongo_path": "account.balance.amount"
      }
    },
    {
      "field_id": "last_updated",
      "field_name": "lastUpdated",
      "data_type": "TIMESTAMP",
      "is_nullable": false,
      "is_key": false,
      "physical_mapping": {
        "oracle_column": "LAST_UPD_DT",
        "mongo_path": "metadata.lastUpdated"
      }
    }
  ]
}
```

**Supported Data Types**:
- STRING
- INTEGER
- DECIMAL
- BOOLEAN
- DATE
- TIMESTAMP
- ARRAY
- OBJECT (for nested structures)

#### Table: `datasets`

Represents tables, collections, files.

```sql
CREATE TABLE datasets (
    dataset_id VARCHAR(100) PRIMARY KEY,
    dataset_name VARCHAR(200) NOT NULL,
    system_id VARCHAR(100) NOT NULL,
    schema_id VARCHAR(100) NOT NULL,
    physical_name VARCHAR(500) NOT NULL,  -- Table name, collection name, file path
    dataset_type VARCHAR(50) NOT NULL,     -- 'TABLE', 'COLLECTION', 'FILE', 'VIEW'
    partition_config JSONB,                -- Partitioning strategy
    filter_config JSONB,                   -- Default filters (WHERE clause, query)
    metadata JSONB,                        -- Additional dataset-specific metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    FOREIGN KEY (system_id) REFERENCES systems(system_id),
    FOREIGN KEY (schema_id) REFERENCES schemas(schema_id),
    CONSTRAINT chk_dataset_type CHECK (dataset_type IN ('TABLE', 'COLLECTION', 'FILE', 'VIEW'))
);

CREATE INDEX idx_datasets_system ON datasets(system_id);
CREATE INDEX idx_datasets_schema ON datasets(schema_id);
CREATE INDEX idx_datasets_active ON datasets(is_active);
```

**partition_config Example**:
```json
{
  "type": "RANGE",
  "column": "created_date",
  "partitions": [
    {"name": "2026-01", "start": "2026-01-01", "end": "2026-01-31"},
    {"name": "2026-02", "start": "2026-02-01", "end": "2026-02-28"}
  ]
}
```

#### Table: `reference_datasets`

Lookup tables for transformations.

```sql
CREATE TABLE reference_datasets (
    reference_dataset_id VARCHAR(100) PRIMARY KEY,
    reference_name VARCHAR(200) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,  -- 'CSV', 'ORACLE', 'MONGODB', 'INLINE'
    source_config JSONB NOT NULL,      -- Connection/path details
    key_fields JSONB NOT NULL,         -- Fields used for lookup
    value_fields JSONB,                -- Fields to return
    cache_config JSONB,                -- Caching strategy
    refresh_schedule VARCHAR(100),     -- Cron expression for refresh
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    CONSTRAINT chk_ref_source_type CHECK (source_type IN ('CSV', 'ORACLE', 'MONGODB', 'INLINE', 'API'))
);

CREATE INDEX idx_ref_datasets_active ON reference_datasets(is_active);
```

**source_config Examples**:

CSV:
```json
{
  "file_path": "s3://bucket/reference/country_codes.csv",
  "delimiter": ",",
  "has_header": true,
  "encoding": "UTF-8"
}
```

Oracle:
```json
{
  "system_id": "oracle-ref",
  "query": "SELECT code, name, region FROM ref_countries WHERE is_active = 'Y'"
}
```

Inline:
```json
{
  "data": [
    {"code": "US", "name": "United States", "region": "NA"},
    {"code": "IN", "name": "India", "region": "APAC"}
  ]
}
```

#### Table: `mappings`

Source-to-target field mapping definitions.

```sql
CREATE TABLE mappings (
    mapping_id VARCHAR(100) PRIMARY KEY,
    mapping_name VARCHAR(200) NOT NULL,
    source_schema_id VARCHAR(100) NOT NULL,
    target_schema_id VARCHAR(100) NOT NULL,
    description TEXT,
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    FOREIGN KEY (source_schema_id) REFERENCES schemas(schema_id),
    FOREIGN KEY (target_schema_id) REFERENCES schemas(schema_id),
    CONSTRAINT chk_mapping_version CHECK (version > 0)
);

CREATE INDEX idx_mappings_source ON mappings(source_schema_id);
CREATE INDEX idx_mappings_target ON mappings(target_schema_id);
CREATE INDEX idx_mappings_active ON mappings(is_active);
```

#### Table: `field_mappings`

Individual field transformation definitions.

```sql
CREATE TABLE field_mappings (
    field_mapping_id SERIAL PRIMARY KEY,
    mapping_id VARCHAR(100) NOT NULL,
    target_field_id VARCHAR(100) NOT NULL,
    source_expression TEXT,            -- Simple expression or null if using transform_chain
    transform_chain JSONB,             -- Ordered transformations
    pre_validations JSONB,             -- Pre-transform validations
    post_validations JSONB,            -- Post-transform validations
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (mapping_id) REFERENCES mappings(mapping_id) ON DELETE CASCADE
);

CREATE INDEX idx_field_mappings_mapping ON field_mappings(mapping_id);
CREATE INDEX idx_field_mappings_active ON field_mappings(is_active);
```

**transform_chain JSONB Structure**:

```json
{
  "steps": [
    {
      "step_order": 1,
      "transform_type": "concat",
      "params": {
        "source_fields": ["FIRST_NAME", "LAST_NAME"],
        "separator": " ",
        "trim": true
      }
    },
    {
      "step_order": 2,
      "transform_type": "upper_case",
      "params": {}
    }
  ]
}
```

**Pre/Post Validations Structure**:

```json
{
  "validations": [
    {
      "validation_type": "not_null",
      "params": {
        "fields": ["FIRST_NAME", "LAST_NAME"]
      },
      "error_action": "FAIL"  -- 'FAIL', 'WARN', 'SKIP'
    },
    {
      "validation_type": "max_length",
      "params": {
        "length": 200
      },
      "error_action": "WARN"
    }
  ]
}
```

#### Table: `reconciliation_rule_sets`

Complete reconciliation configuration.

```sql
CREATE TABLE reconciliation_rule_sets (
    rule_set_id VARCHAR(100) PRIMARY KEY,
    rule_set_name VARCHAR(200) NOT NULL,
    source_dataset_id VARCHAR(100) NOT NULL,
    target_dataset_id VARCHAR(100) NOT NULL,
    mapping_id VARCHAR(100) NOT NULL,
    matching_strategy VARCHAR(50) DEFAULT 'EXACT',  -- 'EXACT', 'FUZZY'
    matching_keys JSONB NOT NULL,                   -- Keys for record pairing
    scope_config JSONB,                             -- Filters, time windows
    tolerance_config JSONB,                         -- Default tolerances
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    
    FOREIGN KEY (source_dataset_id) REFERENCES datasets(dataset_id),
    FOREIGN KEY (target_dataset_id) REFERENCES datasets(dataset_id),
    FOREIGN KEY (mapping_id) REFERENCES mappings(mapping_id),
    CONSTRAINT chk_matching_strategy CHECK (matching_strategy IN ('EXACT', 'FUZZY'))
);

CREATE INDEX idx_rule_sets_source ON reconciliation_rule_sets(source_dataset_id);
CREATE INDEX idx_rule_sets_target ON reconciliation_rule_sets(target_dataset_id);
CREATE INDEX idx_rule_sets_active ON reconciliation_rule_sets(is_active);
```

**matching_keys JSONB**:
```json
{
  "keys": [
    {
      "source_field": "CUST_ID",
      "target_field": "customerId",
      "is_case_sensitive": true
    }
  ],
  "composite": false
}
```

**scope_config Example**:
```json
{
  "source_filter": "created_date >= '2026-01-01'",
  "target_filter": "metadata.createdDate >= ISODate('2026-01-01')",
  "max_records": 1000000
}
```

#### Table: `comparison_rules`

Field-level comparison configuration.

```sql
CREATE TABLE comparison_rules (
    comparison_rule_id SERIAL PRIMARY KEY,
    rule_set_id VARCHAR(100) NOT NULL,
    target_field_id VARCHAR(100) NOT NULL,
    comparator_type VARCHAR(50) NOT NULL,  -- 'EXACT', 'NUMERIC_TOLERANCE', 'DATE_WINDOW', etc.
    comparator_params JSONB,
    ignore_field BOOLEAN DEFAULT FALSE,     -- Skip this field in comparison
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (rule_set_id) REFERENCES reconciliation_rule_sets(rule_set_id) ON DELETE CASCADE,
    CONSTRAINT chk_comparator_type CHECK (comparator_type IN (
        'EXACT', 'NUMERIC_TOLERANCE', 'DATE_WINDOW', 'CASE_INSENSITIVE', 
        'REGEX', 'CUSTOM', 'NULL_EQUALS_EMPTY'
    ))
);

CREATE INDEX idx_comparison_rules_ruleset ON comparison_rules(rule_set_id);
```

**comparator_params Examples**:

```json
// Numeric tolerance
{
  "tolerance": 0.01,
  "tolerance_type": "ABSOLUTE"  // or 'PERCENTAGE'
}

// Date window
{
  "window_seconds": 60
}

// Regex
{
  "pattern": "^[A-Z]{2}\\d{6}$"
}
```

---

## 3. API Endpoints

All metadata is accessible via REST APIs.

### 3.1 System APIs

```
POST   /api/v1/systems                    - Create system
GET    /api/v1/systems                    - List systems
GET    /api/v1/systems/{system_id}        - Get system details
PUT    /api/v1/systems/{system_id}        - Update system
DELETE /api/v1/systems/{system_id}        - Delete system
POST   /api/v1/systems/{system_id}/test   - Test connection
```

**Request Body (POST /api/v1/systems)**:
```json
{
  "system_id": "oracle-core",
  "system_name": "Core Banking Oracle DB",
  "system_type": "ORACLE",
  "description": "Production Oracle database for core banking",
  "connection_config": {
    "host": "oracle.prod.example.com",
    "port": 1521,
    "service_name": "COREDB",
    "username": "recon_user",
    "password": "SecurePassword123",
    "pool_size": 10
  }
}
```

**Response**:
```json
{
  "status": "success",
  "data": {
    "system_id": "oracle-core",
    "created_at": "2026-01-30T01:30:00Z"
  }
}
```

### 3.2 Schema APIs

```
POST   /api/v1/schemas                    - Create schema
GET    /api/v1/schemas                    - List schemas
GET    /api/v1/schemas/{schema_id}        - Get schema details
PUT    /api/v1/schemas/{schema_id}        - Update schema
DELETE /api/v1/schemas/{schema_id}        - Delete schema
POST   /api/v1/schemas/{schema_id}/validate - Validate schema definition
```

### 3.3 Dataset APIs

```
POST   /api/v1/datasets                   - Create dataset
GET    /api/v1/datasets                   - List datasets
GET    /api/v1/datasets/{dataset_id}      - Get dataset details
PUT    /api/v1/datasets/{dataset_id}      - Update dataset
DELETE /api/v1/datasets/{dataset_id}      - Delete dataset
GET    /api/v1/datasets/{dataset_id}/sample - Fetch sample data
```

### 3.4 Mapping APIs

```
POST   /api/v1/mappings                   - Create mapping
GET    /api/v1/mappings                   - List mappings
GET    /api/v1/mappings/{mapping_id}      - Get mapping details
PUT    /api/v1/mappings/{mapping_id}      - Update mapping
DELETE /api/v1/mappings/{mapping_id}      - Delete mapping
POST   /api/v1/mappings/{mapping_id}/field-mappings - Add field mapping
PUT    /api/v1/mappings/{mapping_id}/field-mappings/{field_mapping_id} - Update field mapping
DELETE /api/v1/mappings/{mapping_id}/field-mappings/{field_mapping_id} - Delete field mapping
```

### 3.5 Reference Dataset APIs

```
POST   /api/v1/reference-datasets         - Create reference dataset
GET    /api/v1/reference-datasets         - List reference datasets
GET    /api/v1/reference-datasets/{ref_id} - Get reference dataset details
PUT    /api/v1/reference-datasets/{ref_id} - Update reference dataset
DELETE /api/v1/reference-datasets/{ref_id} - Delete reference dataset
POST   /api/v1/reference-datasets/{ref_id}/refresh - Force refresh cached data
```

### 3.6 Rule Set APIs

```
POST   /api/v1/rule-sets                  - Create rule set
GET    /api/v1/rule-sets                  - List rule sets
GET    /api/v1/rule-sets/{rule_set_id}    - Get rule set details
PUT    /api/v1/rule-sets/{rule_set_id}    - Update rule set
DELETE /api/v1/rule-sets/{rule_set_id}    - Delete rule set
POST   /api/v1/rule-sets/{rule_set_id}/comparison-rules - Add comparison rule
```

---

## 4. Implementation Details

### 4.1 Core Classes

```python
# src/metadata/models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class SystemType(str, Enum):
    ORACLE = "ORACLE"
    MONGODB = "MONGODB"
    FILE = "FILE"
    API = "API"

class System(BaseModel):
    system_id: str
    system_name: str
    system_type: SystemType
    description: Optional[str] = None
    connection_config: Dict[str, Any]
    is_active: bool = True

class DataType(str, Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"

class SchemaField(BaseModel):
    field_id: str
    field_name: str
    data_type: DataType
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_nullable: bool = True
    is_key: bool = False
    description: Optional[str] = None
    physical_mapping: Dict[str, Any]

class Schema(BaseModel):
    schema_id: str
    schema_name: str
    description: Optional[str] = None
    version: int = 1
    fields: List[SchemaField]
    constraints: Optional[Dict[str, Any]] = None
    is_active: bool = True

class Dataset(BaseModel):
    dataset_id: str
    dataset_name: str
    system_id: str
    schema_id: str
    physical_name: str
    dataset_type: str
    partition_config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: bool = True

class TransformStep(BaseModel):
    step_order: int
    transform_type: str
    params: Dict[str, Any]

class ValidationRule(BaseModel):
    validation_type: str
    params: Dict[str, Any]
    error_action: str = "FAIL"  # FAIL, WARN, SKIP

class FieldMapping(BaseModel):
    field_mapping_id: Optional[int] = None
    mapping_id: str
    target_field_id: str
    source_expression: Optional[str] = None
    transform_chain: Optional[List[TransformStep]] = None
    pre_validations: Optional[List[ValidationRule]] = None
    post_validations: Optional[List[ValidationRule]] = None
    is_active: bool = True

class Mapping(BaseModel):
    mapping_id: str
    mapping_name: str
    source_schema_id: str
    target_schema_id: str
    description: Optional[str] = None
    version: int = 1
    is_active: bool = True

class MatchingKey(BaseModel):
    source_field: str
    target_field: str
    is_case_sensitive: bool = True

class ReconciliationRuleSet(BaseModel):
    rule_set_id: str
    rule_set_name: str
    source_dataset_id: str
    target_dataset_id: str
    mapping_id: str
    matching_strategy: str = "EXACT"
    matching_keys: List[MatchingKey]
    scope_config: Optional[Dict[str, Any]] = None
    tolerance_config: Optional[Dict[str, Any]] = None
    is_active: bool = True

class ComparisonRule(BaseModel):
    comparison_rule_id: Optional[int] = None
    rule_set_id: str
    target_field_id: str
    comparator_type: str
    comparator_params: Optional[Dict[str, Any]] = None
    ignore_field: bool = False
    is_active: bool = True
```

### 4.2 Repository Pattern

```python
# src/metadata/repositories.py

from typing import List, Optional
from sqlalchemy.orm import Session
from .models import System, Schema, Dataset, Mapping, ReconciliationRuleSet

class SystemRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, system: System) -> System:
        """Create new system"""
        # Encrypt credentials before storing
        encrypted_config = self._encrypt_credentials(system.connection_config)
        # Insert into database
        # Return created system
        pass
    
    def get_by_id(self, system_id: str) -> Optional[System]:
        """Retrieve system by ID"""
        # Fetch from database
        # Decrypt credentials
        # Return System object
        pass
    
    def list(self, filters: Dict[str, Any] = None) -> List[System]:
        """List systems with optional filters"""
        pass
    
    def update(self, system_id: str, updates: Dict[str, Any]) -> System:
        """Update system"""
        pass
    
    def delete(self, system_id: str) -> bool:
        """Delete system"""
        pass
    
    def test_connection(self, system_id: str) -> Dict[str, Any]:
        """Test system connectivity"""
        pass

class SchemaRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, schema: Schema) -> Schema:
        """Create new schema"""
        pass
    
    def get_by_id(self, schema_id: str) -> Optional[Schema]:
        """Retrieve schema by ID"""
        pass
    
    def list(self, filters: Dict[str, Any] = None) -> List[Schema]:
        """List schemas"""
        pass
    
    def validate(self, schema: Schema) -> Dict[str, Any]:
        """Validate schema definition"""
        # Check field types
        # Validate constraints
        # Return validation result
        pass

class DatasetRepository:
    # Similar pattern...
    pass

class MappingRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def create_mapping(self, mapping: Mapping) -> Mapping:
        """Create mapping"""
        pass
    
    def add_field_mapping(self, field_mapping: FieldMapping) -> FieldMapping:
        """Add field mapping to existing mapping"""
        pass
    
    def get_mapping_with_fields(self, mapping_id: str) -> Dict[str, Any]:
        """Get mapping with all field mappings"""
        # Return mapping + list of field_mappings
        pass

class RuleSetRepository:
    # Similar pattern...
    pass
```

### 4.3 Security: Credential Encryption

```python
# src/metadata/security.py

from cryptography.fernet import Fernet
import os
import json

class CredentialManager:
    def __init__(self):
        # Load encryption key from environment or key management service
        self.key = os.environ.get('RECON_ENCRYPTION_KEY').encode()
        self.cipher = Fernet(self.key)
    
    def encrypt_config(self, config: Dict[str, Any]) -> str:
        """Encrypt connection configuration"""
        # Identify sensitive fields
        sensitive_fields = ['password', 'password_encrypted', 
                          'connection_string', 'api_key', 'token']
        
        encrypted_config = config.copy()
        for field in sensitive_fields:
            if field in encrypted_config:
                value = encrypted_config[field]
                encrypted_value = self.cipher.encrypt(value.encode()).decode()
                encrypted_config[f"{field}_encrypted"] = encrypted_value
                del encrypted_config[field]
        
        return json.dumps(encrypted_config)
    
    def decrypt_config(self, encrypted_config: str) -> Dict[str, Any]:
        """Decrypt connection configuration"""
        config = json.loads(encrypted_config)
        
        decrypted_config = {}
        for key, value in config.items():
            if key.endswith('_encrypted'):
                original_key = key.replace('_encrypted', '')
                decrypted_value = self.cipher.decrypt(value.encode()).decode()
                decrypted_config[original_key] = decrypted_value
            else:
                decrypted_config[key] = value
        
        return decrypted_config
```

---

## 5. Validation Rules

### 5.1 Schema Validation

When creating/updating schemas:
- All field IDs must be unique within schema
- Data types must be from supported list
- Precision/scale required for DECIMAL types
- At least one key field must be defined
- Physical mappings must be valid for system type

### 5.2 Mapping Validation

When creating mappings:
- Source and target schemas must exist and be active
- Transform chain steps must reference valid transforms
- Source expressions must be valid (safe eval)
- Validation rules must reference valid validators
- No circular dependencies in multi-step transforms

### 5.3 Rule Set Validation

When creating rule sets:
- Source and target datasets must exist and be active
- Datasets must belong to different systems (cannot reconcile Oracle to Oracle)
- Mapping must connect source schema to target schema
- Matching keys must exist in both schemas
- Comparison rules must reference target schema fields

---

## 6. Testing Strategy

### 6.1 Unit Tests

```python
# tests/metadata/test_repositories.py

import pytest
from src.metadata.repositories import SystemRepository
from src.metadata.models import System, SystemType

def test_create_system(db_session):
    """Test system creation"""
    repo = SystemRepository(db_session)
    
    system = System(
        system_id="test-oracle",
        system_name="Test Oracle",
        system_type=SystemType.ORACLE,
        connection_config={
            "host": "localhost",
            "port": 1521,
            "username": "test",
            "password": "test123"
        }
    )
    
    created = repo.create(system)
    assert created.system_id == "test-oracle"
    assert "password_encrypted" in created.connection_config
    assert "password" not in created.connection_config

def test_get_system(db_session):
    """Test system retrieval"""
    repo = SystemRepository(db_session)
    system = repo.get_by_id("test-oracle")
    
    assert system is not None
    assert system.system_id == "test-oracle"
    # Credentials should be decrypted on retrieval
    assert "password" in system.connection_config
```

### 6.2 Integration Tests

```python
# tests/metadata/test_metadata_api.py

from fastapi.testclient import TestClient

def test_create_system_api(client: TestClient):
    """Test system creation via API"""
    response = client.post("/api/v1/systems", json={
        "system_id": "oracle-test",
        "system_name": "Test Oracle",
        "system_type": "ORACLE",
        "connection_config": {
            "host": "localhost",
            "port": 1521,
            "username": "test",
            "password": "test123"
        }
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["system_id"] == "oracle-test"

def test_list_systems_api(client: TestClient):
    """Test listing systems"""
    response = client.get("/api/v1/systems")
    assert response.status_code == 200
    assert len(response.json()["data"]) > 0
```

---

## 7. Performance Considerations

### 7.1 Caching Strategy

- Cache schema definitions in memory (Redis) after first load
- Invalidate cache on schema update
- Cache reference datasets per job run
- Use PostgreSQL prepared statements for repeated queries

### 7.2 Indexing Strategy

- Composite index on (system_id, is_active) for datasets
- Composite index on (mapping_id, is_active) for field_mappings
- Full-text index on description fields for search
- JSONB GIN indexes on frequently queried JSON fields

### 7.3 Query Optimization

```sql
-- Example: Efficiently fetch complete rule set with all dependencies
SELECT 
    rs.*,
    sd.dataset_name as source_dataset_name,
    td.dataset_name as target_dataset_name,
    m.mapping_name,
    s_schema.fields as source_fields,
    t_schema.fields as target_fields
FROM reconciliation_rule_sets rs
JOIN datasets sd ON rs.source_dataset_id = sd.dataset_id
JOIN datasets td ON rs.target_dataset_id = td.dataset_id
JOIN mappings m ON rs.mapping_id = m.mapping_id
JOIN schemas s_schema ON sd.schema_id = s_schema.schema_id
JOIN schemas t_schema ON td.schema_id = t_schema.schema_id
WHERE rs.rule_set_id = 'customer_recon_v1'
  AND rs.is_active = TRUE;
```

---

## 8. Migration & Versioning

### 8.1 Schema Versioning

- Schemas have version numbers
- Mappings reference specific schema versions
- Support parallel versions (v1 and v2 active simultaneously)
- Automated migration scripts for version upgrades

### 8.2 Database Migrations

Use Alembic for database migrations:

```bash
# Create migration
alembic revision --autogenerate -m "Add comparison_rules table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

**Document End**

*Next Component*: Connector Layer Design
