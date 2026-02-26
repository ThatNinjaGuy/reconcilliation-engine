# Generic Data Reconciliation Engine - High Level Design

**Project Name**: GenRecon - Generic Data Reconciliation Platform  
**Version**: 1.0  
**Date**: January 30, 2026  
**Author**: Solutions Architecture Team

---

## 1. Executive Summary

GenRecon is a metadata-driven, API-first data reconciliation platform designed to validate data consistency across heterogeneous systems. The platform provides a generic, reusable framework for reconciling data between different source and target systems with complex transformation logic and reference data support.

**Initial Scope**: Oracle (source) ↔ MongoDB (target)  
**Future Extensibility**: CSV, Parquet, REST APIs, other databases

---

## 2. Business Objectives

### 2.1 Primary Goals
- **Generic Framework**: Single platform for reconciling any source to any target
- **Metadata-Driven**: Zero code changes for new dataset reconciliation
- **Transformation Support**: Handle complex multi-step transformations with reference data
- **API-First**: Full REST API for UI integration and automation
- **Audit & Compliance**: Complete reconciliation history and discrepancy tracking

### 2.2 Success Criteria
- Support Oracle → MongoDB reconciliation for multiple table/collection pairs
- Handle 1 million+ records per reconciliation run
- Sub-second API response for status queries
- 99.9% accuracy in discrepancy detection
- Complete audit trail for compliance

---

## 3. System Architecture

### 3.1 Architecture Principles

1. **Separation of Concerns**: Clear boundaries between connectors, metadata, transformation, and reconciliation
2. **Metadata-Driven**: All configuration externalized; no hardcoded logic
3. **Plugin Architecture**: New connectors/transforms without core changes
4. **API-First Design**: Everything accessible via REST APIs
5. **Immutable Audit**: All runs and results stored permanently

### 3.2 Architectural Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway Layer                        │
│  - REST APIs (FastAPI)                                      │
│  - Authentication & Authorization                           │
│  - Rate Limiting & Throttling                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Orchestration & Job Layer                   │
│  - Job Scheduler                                            │
│  - Job State Management                                     │
│  - Result Aggregation                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Metadata    │   │   Transformation │   │  Reconciliation  │
│   Manager     │   │      Engine      │   │     Engine       │
│               │   │                  │   │                  │
│ - Schemas     │   │ - Mapping        │   │ - Matcher        │
│ - Mappings    │   │   Interpreter    │   │ - Comparator     │
│ - Rule Sets   │   │ - Transform      │   │ - Discrepancy    │
│ - Reference   │   │   Registry       │   │   Detector       │
│   Datasets    │   │ - Validation     │   │                  │
└───────────────┘   └──────────────────┘   └──────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│    Oracle     │   │     MongoDB      │   │    Reference     │
│   Connector   │   │    Connector     │   │ Data Connector   │
│               │   │                  │   │                  │
│ - Reader      │   │ - Reader         │   │ - CSV            │
│ - Schema      │   │ - JSON Path      │   │ - DB Tables      │
│   Mapper      │   │   Extractor      │   │ - APIs           │
└───────────────┘   └──────────────────┘   └──────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
│  - Metadata Repository (PostgreSQL)                         │
│  - Results Database (PostgreSQL)                            │
│  - Discrepancy Store (PostgreSQL + S3 for large volumes)   │
│  - Audit Logs (PostgreSQL)                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Core Components Overview

### 4.1 Metadata Management Layer

**Purpose**: Store and manage all configuration metadata

**Key Entities**:
- **System**: Connection details for Oracle, MongoDB, reference data sources
- **Dataset**: Logical representation of tables/collections
- **Schema**: Field-level structure with data types and constraints
- **Mapping**: Source-to-target field transformations
- **ReferenceDataset**: Lookup/enrichment data
- **ReconciliationRuleSet**: Matching and comparison rules

**Technology**: PostgreSQL for metadata storage with JSONB for flexible schema storage

### 4.2 Connector Layer

**Purpose**: Abstract data access from different systems into canonical format

**Oracle Connector**:
- SQLAlchemy-based connection pooling
- Batch reading with configurable chunk size
- Type mapping (Oracle → Python canonical types)
- Query optimization for large tables

**MongoDB Connector**:
- PyMongo with connection pooling
- JSON path-based field extraction
- Nested document flattening
- Aggregation pipeline support for complex projections

**Canonical Row Model**: Common internal representation for all data sources

### 4.3 Transformation Engine

**Purpose**: Apply metadata-defined transformations to convert source data to target shape

**Components**:
- **Mapping Interpreter**: Parses and executes field-level mappings
- **Transform Registry**: Pluggable transformation functions
- **Reference Data Manager**: Loads and caches reference datasets
- **Validation Engine**: Pre/post-transform validations

**Built-in Transforms**:
- Direct field copy
- String operations (concat, substring, upper/lower, trim)
- Math operations (add, subtract, multiply, divide, round)
- Date operations (parse, format, diff, add/subtract)
- Reference lookups
- Conditional logic (if-then-else)
- Custom expressions (safe eval)

### 4.4 Reconciliation Engine

**Purpose**: Match records and detect discrepancies

**Components**:
- **Record Matcher**: Pairs source-target records using matching keys
- **Field Comparator**: Compares individual fields with configurable tolerance
- **Discrepancy Detector**: Identifies and categorizes differences
- **Result Aggregator**: Computes statistics and generates reports

**Comparison Strategies**:
- Exact match
- Numeric with tolerance
- String case-insensitive
- Date/time with window
- Custom comparators

### 4.5 Orchestration Layer

**Purpose**: Manage job lifecycle and execution

**Components**:
- **Job Scheduler**: Trigger reconciliation runs (manual/scheduled)
- **State Manager**: Track job progress (PENDING → RUNNING → COMPLETED/FAILED)
- **Worker Pool**: Parallel processing for large datasets
- **Result Collector**: Aggregate results from parallel workers

**Job Types**:
- Full reconciliation (all records)
- Incremental (delta/changed records only)
- Filtered (specific date range or ID range)

### 4.6 API Layer

**Purpose**: Expose all functionality via REST APIs

**API Categories**:
- **Metadata APIs**: CRUD for systems, schemas, mappings, rule sets
- **Job APIs**: Create, start, stop, query jobs
- **Result APIs**: Query discrepancies, download reports
- **Reference Data APIs**: Upload and manage reference datasets
- **System APIs**: Health checks, metrics

**Technology**: FastAPI with Pydantic models, OpenAPI documentation

---

## 5. Data Flow

### 5.1 End-to-End Reconciliation Flow

```
1. User/UI submits reconciliation job via API
   ↓
2. Orchestrator resolves ReconciliationRuleSet metadata
   ↓
3. Load schemas for source (Oracle) and target (MongoDB)
   ↓
4. Load mapping configuration and reference datasets
   ↓
5. Oracle Connector reads source data in batches
   ↓
6. Transformation Engine applies mappings to create "target-shaped" rows
   ↓
7. MongoDB Connector reads target data in batches
   ↓
8. Reconciliation Engine matches records using matching keys
   ↓
9. For each matched pair, compare fields using comparison rules
   ↓
10. Detect discrepancies and categorize (matched/unmatched/discrepant)
   ↓
11. Store results in Results Database
   ↓
12. Update job status to COMPLETED
   ↓
13. User queries results via API or UI
```

### 5.2 Multi-Table/Collection Reconciliation

For reconciling multiple Oracle tables → MongoDB collections:

- Define separate `ReconciliationRuleSet` for each table-collection pair
- Create a **Batch Job** that orchestrates multiple rule sets
- Execute in parallel or sequentially (configurable)
- Aggregate results across all pairs

---

## 6. Technology Stack

### 6.1 Backend

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **API Framework** | FastAPI | High performance, async support, auto-docs |
| **Language** | Python 3.11+ | Rich data ecosystem, your expertise |
| **Oracle Connectivity** | cx_Oracle + SQLAlchemy | Production-grade Oracle support |
| **MongoDB Connectivity** | PyMongo | Official MongoDB driver |
| **Data Processing** | Pandas + NumPy | Efficient in-memory processing |
| **Metadata Store** | PostgreSQL 15+ | ACID, JSONB for flexible schema |
| **Results Store** | PostgreSQL + S3 | Hybrid (DB for queries, S3 for archives) |
| **Job Scheduling** | APScheduler | Lightweight, embedded scheduler |
| **Validation** | Pydantic | Type safety, validation |
| **Testing** | Pytest + Pytest-asyncio | Comprehensive test framework |

### 6.2 DevOps & Deployment

| Component | Technology |
|-----------|------------|
| **Containerization** | Docker + Docker Compose |
| **Orchestration** | Kubernetes (future) |
| **CI/CD** | GitHub Actions / GitLab CI |
| **Monitoring** | Prometheus + Grafana |
| **Logging** | Structured logging (JSON) + ELK/Loki |
| **API Gateway** | Nginx or Traefik |

### 6.3 Frontend (Future)

- React + TypeScript for UI
- Material-UI or Ant Design
- REST client to backend APIs

---

## 7. Deployment Architecture

### 7.1 Phase 1: Monolithic Deployment

```
┌─────────────────────────────────────────────────────┐
│                  Docker Container                   │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         FastAPI Application                  │  │
│  │  - API Server                                │  │
│  │  - Orchestrator                              │  │
│  │  - Job Workers (threads/processes)           │  │
│  └──────────────────────────────────────────────┘  │
│                       ↓                             │
│  ┌──────────────────────────────────────────────┐  │
│  │         PostgreSQL Database                  │  │
│  │  - Metadata                                  │  │
│  │  - Results                                   │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 7.2 Phase 2: Distributed Deployment (Future)

- Separate API, Orchestrator, and Worker services
- Message queue (RabbitMQ/Redis) for job distribution
- Horizontal scaling of workers
- Shared PostgreSQL and distributed cache (Redis)

---

## 8. Security & Compliance

### 8.1 Authentication & Authorization

- API key-based authentication for service-to-service
- JWT tokens for user sessions (future UI)
- Role-based access control (RBAC):
  - Admin: Full access
  - Operator: Run jobs, view results
  - Viewer: Read-only access

### 8.2 Data Security

- Credentials encrypted at rest (Fernet/AES-256)
- TLS for all external connections (Oracle, MongoDB, APIs)
- Secrets management via environment variables or Vault
- PII/sensitive field masking in logs and results

### 8.3 Audit & Compliance

- Immutable audit log for all API calls
- Reconciliation run history (metadata, config, results)
- Discrepancy retention policy (configurable)
- Export capabilities for compliance reporting

---

## 9. Scalability & Performance

### 9.1 Design for Scale

| Aspect | Strategy |
|--------|----------|
| **Large Tables** | Batch processing (10k-100k rows/batch) |
| **Parallel Processing** | Multi-threaded workers per job |
| **Oracle Performance** | Indexed matching keys, partition pruning |
| **MongoDB Performance** | Compound indexes on matching keys |
| **Memory Management** | Streaming/chunked reads, no full table loads |
| **Caching** | Reference datasets cached per job run |

### 9.2 Performance Targets

- **Throughput**: 100k records/minute (single worker)
- **Latency**: <100ms API response for status queries
- **Concurrency**: 10 concurrent reconciliation jobs
- **Data Volume**: Up to 10M records per job (phase 1)

---

## 10. Extensibility Points

### 10.1 New Connectors

Add CSV, Parquet, REST API connectors by:
1. Implementing `DatasetReader` interface
2. Registering in connector factory
3. Defining system type in metadata

No changes to transformation or reconciliation engines required.

### 10.2 New Transformations

Add custom transforms by:
1. Implementing transform function signature
2. Registering in `TransformRegistry`
3. Using in mapping metadata

### 10.3 New Comparison Strategies

Add custom comparators by:
1. Implementing `Comparator` interface
2. Registering in comparison registry
3. Referencing in rule set metadata

---

## 11. Project Phases

### Phase 1: Core Platform (8 weeks)
- Metadata model and database schema
- Oracle and MongoDB connectors
- Basic transformation engine (10 transforms)
- Reconciliation engine (exact match, numeric tolerance)
- REST APIs for metadata and job management
- CLI for testing

### Phase 2: Advanced Features (4 weeks)
- Reference data support
- Complex transformations (multi-step, conditional)
- Advanced comparators (fuzzy, case-insensitive)
- Scheduled jobs
- Result export (CSV, Excel)

### Phase 3: Production Readiness (4 weeks)
- Authentication & authorization
- Monitoring and alerting
- Performance optimization
- Documentation and training
- UI prototype

### Phase 4: Scale & Extend (Ongoing)
- Additional connectors (CSV, Parquet)
- Distributed architecture
- Full-featured UI
- ML-powered fuzzy matching

---

## 12. Risk & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Large data volumes** | Performance degradation | Implement batching, partitioning, parallel processing |
| **Schema evolution** | Broken mappings | Version schemas and mappings, validation on load |
| **Network failures** | Job failures | Retry logic, checkpoint/resume capability |
| **Memory exhaustion** | System crash | Streaming processing, memory limits per worker |
| **Oracle/Mongo downtime** | Cannot reconcile | Queue jobs, retry with exponential backoff |
| **Metadata corruption** | System unusable | Database backups, validation on write |

---

## 13. Success Metrics

### 13.1 Technical Metrics
- API uptime: 99.9%
- Job success rate: >95%
- Average job completion time: <10 minutes for 1M records
- API p95 latency: <200ms

### 13.2 Business Metrics
- Number of active rule sets
- Total records reconciled per day
- Average discrepancy rate per rule set
- Time saved vs manual reconciliation

---

## 14. Assumptions & Constraints

### 14.1 Assumptions
- Oracle and MongoDB instances are accessible from deployment environment
- Matching keys exist and are indexed in both systems
- Data volumes fit in-memory processing with batching
- Reference datasets are relatively small (<1M rows)

### 14.2 Constraints
- Initial version: Oracle and MongoDB only
- Single-region deployment
- Manual job triggering (scheduled jobs in Phase 2)
- No real-time/streaming reconciliation (batch only)

---

## 15. Appendix: Glossary

- **Canonical Row**: Internal representation of a data row, agnostic to source system
- **Dataset**: Logical representation of a table, collection, or file
- **Discrepancy**: Difference detected between source and target field values
- **Field Mapping**: Definition of how to transform source field(s) to target field
- **Matching Key**: Field(s) used to pair source and target records
- **Metadata**: Configuration data that drives reconciliation behavior
- **ReconciliationRuleSet**: Complete configuration for one reconciliation scenario
- **Reference Dataset**: Lookup table used during transformations
- **Schema**: Logical field structure (names, types, constraints)
- **System**: External data source or target (Oracle, MongoDB, etc.)
- **Transform Chain**: Ordered sequence of transformations applied to a field

---

**Document End**

*Next Steps*: Review this HLD with stakeholders, then proceed to detailed component design documents.
