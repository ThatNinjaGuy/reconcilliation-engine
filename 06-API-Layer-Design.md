# API Layer - REST API Specification

**Component**: REST API Layer  
**Version**: 1.0  
**Date**: January 30, 2026  
**Framework**: FastAPI

---

## 1. API Architecture

### 1.1 Base Configuration

```python
# src/api/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

app = FastAPI(
    title="GenRecon API",
    description="Generic Data Reconciliation Platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from .routers import systems, schemas, datasets, mappings, rule_sets, jobs, results

app.include_router(systems.router, prefix="/api/v1/systems", tags=["Systems"])
app.include_router(schemas.router, prefix="/api/v1/schemas", tags=["Schemas"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["Datasets"])
app.include_router(mappings.router, prefix="/api/v1/mappings", tags=["Mappings"])
app.include_router(rule_sets.router, prefix="/api/v1/rule-sets", tags=["Rule Sets"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["Jobs"])
app.include_router(results.router, prefix="/api/v1/results", tags=["Results"])

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "genrecon-api"}
```

---

## 2. Jobs API (Core Reconciliation API)

### 2.1 Endpoints

```python
# src/api/routers/jobs.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class JobCreateRequest(BaseModel):
    """Request to create reconciliation job"""
    rule_set_id: str
    filters: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None  # Cron expression for scheduled jobs

class JobResponse(BaseModel):
    """Job details response"""
    job_id: str
    rule_set_id: str
    status: str  # PENDING, RUNNING, COMPLETED, FAILED
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress_percent: Optional[int] = None
    summary_stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks
):
    """
    Create and start a reconciliation job.
    
    The job runs asynchronously. Use GET /jobs/{job_id} to check status.
    """
    # Create job record
    job_id = job_service.create_job(
        rule_set_id=request.rule_set_id,
        filters=request.filters
    )
    
    # Start job in background
    background_tasks.add_task(job_service.execute_job, job_id)
    
    return JobResponse(
        job_id=job_id,
        rule_set_id=request.rule_set_id,
        status="PENDING",
        created_at=datetime.now().isoformat()
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status and summary"""
    job = job_service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.get("", response_model=List[JobResponse])
async def list_jobs(
    rule_set_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    """List reconciliation jobs with filters"""
    jobs = job_service.list_jobs(
        rule_set_id=rule_set_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    return jobs

@router.delete("/{job_id}", status_code=204)
async def cancel_job(job_id: str):
    """Cancel a running job"""
    success = job_service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    
    return None
```

---

## 3. Results API

```python
# src/api/routers/results.py

from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class DiscrepancyResponse(BaseModel):
    """Field discrepancy response"""
    record_key: str
    field_id: str
    source_value: str
    target_value: str
    difference: str
    comparator_type: str
    severity: str

class SummaryStatsResponse(BaseModel):
    """Summary statistics for a run"""
    run_id: str
    rule_set_id: str
    total_source_records: int
    total_target_records: int
    matched_records: int
    matched_with_no_discrepancy: int
    matched_with_discrepancy: int
    unmatched_source_records: int
    unmatched_target_records: int
    total_field_discrepancies: int
    match_rate_percent: float
    accuracy_rate_percent: float
    field_discrepancy_counts: Dict[str, int]

@router.get("/{job_id}/summary", response_model=SummaryStatsResponse)
async def get_summary(job_id: str):
    """Get summary statistics for a completed job"""
    summary = result_service.get_summary(job_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Results not found")
    
    return summary

@router.get("/{job_id}/discrepancies", response_model=List[DiscrepancyResponse])
async def get_discrepancies(
    job_id: str,
    field_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=10000),
    offset: int = Query(0)
):
    """Get field discrepancies with pagination"""
    discrepancies = result_service.get_discrepancies(
        job_id=job_id,
        field_id=field_id,
        severity=severity,
        limit=limit,
        offset=offset
    )
    
    return discrepancies

@router.get("/{job_id}/unmatched-source")
async def get_unmatched_source(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0)
):
    """Get unmatched source records"""
    records = result_service.get_unmatched_source(
        job_id=job_id,
        limit=limit,
        offset=offset
    )
    
    return records

@router.get("/{job_id}/unmatched-target")
async def get_unmatched_target(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0)
):
    """Get unmatched target records"""
    records = result_service.get_unmatched_target(
        job_id=job_id,
        limit=limit,
        offset=offset
    )
    
    return records

@router.get("/{job_id}/export")
async def export_results(job_id: str, format: str = Query("csv")):
    """
    Export results to CSV or Excel.
    
    Returns downloadable file.
    """
    if format not in ["csv", "excel"]:
        raise HTTPException(status_code=400, detail="Invalid format")
    
    # Generate export file
    file_stream = result_service.export_results(job_id, format)
    
    filename = f"reconciliation_{job_id}.{format}"
    media_type = "text/csv" if format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    return StreamingResponse(
        file_stream,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

---

## 4. Complete API Endpoint Summary

### 4.1 Systems API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/systems` | Create system |
| GET | `/api/v1/systems` | List systems |
| GET | `/api/v1/systems/{system_id}` | Get system |
| PUT | `/api/v1/systems/{system_id}` | Update system |
| DELETE | `/api/v1/systems/{system_id}` | Delete system |
| POST | `/api/v1/systems/{system_id}/test` | Test connection |

### 4.2 Schemas API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/schemas` | Create schema |
| GET | `/api/v1/schemas` | List schemas |
| GET | `/api/v1/schemas/{schema_id}` | Get schema |
| PUT | `/api/v1/schemas/{schema_id}` | Update schema |
| DELETE | `/api/v1/schemas/{schema_id}` | Delete schema |

### 4.3 Datasets API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/datasets` | Create dataset |
| GET | `/api/v1/datasets` | List datasets |
| GET | `/api/v1/datasets/{dataset_id}` | Get dataset |
| PUT | `/api/v1/datasets/{dataset_id}` | Update dataset |
| DELETE | `/api/v1/datasets/{dataset_id}` | Delete dataset |
| GET | `/api/v1/datasets/{dataset_id}/sample` | Get sample data |
| POST | `/api/v1/datasets/{dataset_id}/validate` | Validate schema |

### 4.4 Mappings API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/mappings` | Create mapping |
| GET | `/api/v1/mappings` | List mappings |
| GET | `/api/v1/mappings/{mapping_id}` | Get mapping |
| PUT | `/api/v1/mappings/{mapping_id}` | Update mapping |
| DELETE | `/api/v1/mappings/{mapping_id}` | Delete mapping |
| POST | `/api/v1/mappings/{mapping_id}/field-mappings` | Add field mapping |
| PUT | `/api/v1/mappings/{mapping_id}/field-mappings/{id}` | Update field mapping |
| DELETE | `/api/v1/mappings/{mapping_id}/field-mappings/{id}` | Delete field mapping |

### 4.5 Reference Datasets API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/reference-datasets` | Create reference dataset |
| GET | `/api/v1/reference-datasets` | List reference datasets |
| GET | `/api/v1/reference-datasets/{ref_id}` | Get reference dataset |
| PUT | `/api/v1/reference-datasets/{ref_id}` | Update reference dataset |
| DELETE | `/api/v1/reference-datasets/{ref_id}` | Delete reference dataset |
| POST | `/api/v1/reference-datasets/{ref_id}/refresh` | Force refresh |

### 4.6 Rule Sets API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/rule-sets` | Create rule set |
| GET | `/api/v1/rule-sets` | List rule sets |
| GET | `/api/v1/rule-sets/{rule_set_id}` | Get rule set |
| PUT | `/api/v1/rule-sets/{rule_set_id}` | Update rule set |
| DELETE | `/api/v1/rule-sets/{rule_set_id}` | Delete rule set |
| POST | `/api/v1/rule-sets/{rule_set_id}/comparison-rules` | Add comparison rule |

### 4.7 Jobs API (Reconciliation Execution)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs` | Create and start job |
| GET | `/api/v1/jobs` | List jobs |
| GET | `/api/v1/jobs/{job_id}` | Get job status |
| DELETE | `/api/v1/jobs/{job_id}` | Cancel job |

### 4.8 Results API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/results/{job_id}/summary` | Get summary stats |
| GET | `/api/v1/results/{job_id}/discrepancies` | Get discrepancies (paginated) |
| GET | `/api/v1/results/{job_id}/unmatched-source` | Get unmatched source records |
| GET | `/api/v1/results/{job_id}/unmatched-target` | Get unmatched target records |
| GET | `/api/v1/results/{job_id}/export` | Export results (CSV/Excel) |

---

## 5. API Usage Example

### 5.1 Complete Workflow via API

```bash
# 1. Create Oracle system
curl -X POST http://localhost:8000/api/v1/systems \
  -H "Content-Type: application/json" \
  -d '{
    "system_id": "oracle-core",
    "system_name": "Core Banking Oracle",
    "system_type": "ORACLE",
    "connection_config": {
      "host": "oracle.example.com",
      "port": 1521,
      "service_name": "COREDB",
      "username": "recon_user",
      "password": "SecurePass123"
    }
  }'

# 2. Create MongoDB system
curl -X POST http://localhost:8000/api/v1/systems \
  -H "Content-Type: application/json" \
  -d '{
    "system_id": "mongo-core",
    "system_name": "Core Banking MongoDB",
    "system_type": "MONGODB",
    "connection_config": {
      "connection_string": "mongodb://user:pass@mongo.example.com:27017",
      "database": "core_banking"
    }
  }'

# 3. Create schema (simplified)
curl -X POST http://localhost:8000/api/v1/schemas \
  -H "Content-Type: application/json" \
  -d @customer_schema.json

# 4. Create datasets
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "customer_oracle",
    "dataset_name": "Oracle Customers",
    "system_id": "oracle-core",
    "schema_id": "customer_schema",
    "physical_name": "CUSTOMERS",
    "dataset_type": "TABLE"
  }'

curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": "customer_mongo",
    "dataset_name": "MongoDB Customers",
    "system_id": "mongo-core",
    "schema_id": "customer_schema",
    "physical_name": "customers",
    "dataset_type": "COLLECTION"
  }'

# 5. Create mapping
curl -X POST http://localhost:8000/api/v1/mappings \
  -H "Content-Type: application/json" \
  -d @customer_mapping.json

# 6. Create rule set
curl -X POST http://localhost:8000/api/v1/rule-sets \
  -H "Content-Type: application/json" \
  -d '{
    "rule_set_id": "customer_recon",
    "rule_set_name": "Customer Reconciliation",
    "source_dataset_id": "customer_oracle",
    "target_dataset_id": "customer_mongo",
    "mapping_id": "customer_mapping",
    "matching_keys": [
      {"source_field": "customerId", "target_field": "customerId"}
    ]
  }'

# 7. Create and run reconciliation job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "rule_set_id": "customer_recon"
  }'

# Response:
# {
#   "job_id": "JOB_20260130_013000_12345",
#   "rule_set_id": "customer_recon",
#   "status": "PENDING",
#   "created_at": "2026-01-30T01:30:00Z"
# }

# 8. Check job status (poll until COMPLETED)
curl http://localhost:8000/api/v1/jobs/JOB_20260130_013000_12345

# 9. Get results summary
curl http://localhost:8000/api/v1/results/JOB_20260130_013000_12345/summary

# Response:
# {
#   "run_id": "RUN_20260130_013000_67890",
#   "total_source_records": 100000,
#   "total_target_records": 100000,
#   "matched_records": 99500,
#   "matched_with_no_discrepancy": 98000,
#   "matched_with_discrepancy": 1500,
#   "unmatched_source_records": 500,
#   "unmatched_target_records": 500,
#   "match_rate_percent": 99.5,
#   "accuracy_rate_percent": 98.5
# }

# 10. Get discrepancies (paginated)
curl "http://localhost:8000/api/v1/results/JOB_20260130_013000_12345/discrepancies?limit=100&offset=0"

# 11. Export results
curl "http://localhost:8000/api/v1/results/JOB_20260130_013000_12345/export?format=csv" \
  -o reconciliation_results.csv
```

---

## 6. Error Handling

### 6.1 Standard Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": {
      "field": "system_id",
      "reason": "System ID already exists"
    },
    "timestamp": "2026-01-30T01:30:00Z"
  }
}
```

### 6.2 HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | Successful GET |
| 201 | Successful POST (resource created) |
| 204 | Successful DELETE (no content) |
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 409 | Conflict (e.g., duplicate ID) |
| 500 | Internal server error |

---

## 7. Authentication & Authorization

```python
# src/api/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token"""
    token = credentials.credentials
    
    # Implement your token verification logic
    # For now, simple API key check
    if token != os.environ.get("API_KEY"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return token

# Use in endpoints:
@router.get("", dependencies=[Depends(verify_token)])
async def protected_endpoint():
    return {"message": "Authenticated"}
```

---

**Document End**

*Next Document*: Comprehensive Test Plan
