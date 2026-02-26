"""Results API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.repositories import ResultRepository, JobRepository
from ...core.schemas import DiscrepancyResponse, SummaryStatsResponse

router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/{job_id}/summary", response_model=SummaryStatsResponse)
def get_summary(job_id: str, db: Session = Depends(get_db)):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    run = repo.get_run(job.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Results not found")
    stats = run.summary_stats or {}
    return SummaryStatsResponse(
        run_id=run.run_id,
        rule_set_id=run.rule_set_id,
        total_source_records=stats.get("total_source_records", 0),
        total_target_records=stats.get("total_target_records", 0),
        matched_records=stats.get("matched_records", 0),
        matched_with_no_discrepancy=stats.get("matched_with_no_discrepancy", 0),
        matched_with_discrepancy=stats.get("matched_with_discrepancy", 0),
        unmatched_source_records=stats.get("unmatched_source_records", 0),
        unmatched_target_records=stats.get("unmatched_target_records", 0),
        total_field_discrepancies=stats.get("total_field_discrepancies", 0),
        match_rate_percent=stats.get("match_rate_percent", 0.0),
        accuracy_rate_percent=stats.get("accuracy_rate_percent", 0.0),
        field_discrepancy_counts=stats.get("field_discrepancy_counts", {}),
    )


@router.get("/{job_id}/discrepancies", response_model=List[DiscrepancyResponse])
def get_discrepancies(
    job_id: str,
    field_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_discrepancies(
        run_id=job.run_id,
        filters={"field_id": field_id, "severity": severity},
        limit=limit,
        offset=offset,
    )
    return [
        DiscrepancyResponse(
            record_key=rec.record_key,
            field_id=rec.field_id,
            source_value=rec.source_value,
            target_value=rec.target_value,
            difference=rec.difference,
            comparator_type=rec.comparator_type,
            severity=rec.severity,
        )
        for rec in records
    ]


@router.get("/{job_id}/unmatched-source")
def get_unmatched_source(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_unmatched(run_id=job.run_id, side="source", limit=limit, offset=offset)
    return [record.record_data for record in records]


@router.get("/{job_id}/unmatched-target")
def get_unmatched_target(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_unmatched(run_id=job.run_id, side="target", limit=limit, offset=offset)
    return [record.record_data for record in records]
