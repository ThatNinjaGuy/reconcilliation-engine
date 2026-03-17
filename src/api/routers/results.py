"""Results API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.repositories import ResultRepository, JobRepository
from ...core.schemas import DiffViewItem, DiffViewResponse, DiscrepancyResponse, SummaryStatsResponse

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


@router.get("/{job_id}/diff-view", response_model=DiffViewResponse)
def get_diff_view(
    job_id: str,
    limit: int = Query(500, le=5000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """Get full side-by-side diff data for UI: matched pairs with discrepancies, unmatched source, unmatched target."""
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)

    matched_with_discrepancies: List[DiffViewItem] = []
    # Prefer V2 (includes line/row metadata); fall back to V1 if empty.
    v2_pairs = repo.get_matched_record_pairs_v2(job.run_id, limit=limit, offset=offset)
    if v2_pairs:
        for pair in v2_pairs:
            matched_with_discrepancies.append(
                DiffViewItem(
                    type="matched_discrepancy",
                    record_key=pair.record_key,
                    source_record=pair.source_record,
                    target_record=pair.target_record,
                    source_metadata=pair.source_metadata,
                    target_metadata=pair.target_metadata,
                    diff_field_ids=pair.diff_field_ids,
                )
            )
    else:
        for pair in repo.get_matched_record_pairs(job.run_id, limit=limit, offset=offset):
            matched_with_discrepancies.append(
                DiffViewItem(
                    type="matched_discrepancy",
                    record_key=pair.record_key,
                    source_record=pair.source_record,
                    target_record=pair.target_record,
                    diff_field_ids=pair.diff_field_ids,
                )
            )

    unmatched_source: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "source", limit=limit, offset=offset):
        unmatched_source.append(
            DiffViewItem(
                type="unmatched_source",
                record_key=rec.record_key,
                source_record=rec.record_data.get("fields", rec.record_data),
                source_metadata=rec.record_data.get("metadata"),
                target_record=None,
                diff_field_ids=None,
            )
        )

    unmatched_target: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "target", limit=limit, offset=offset):
        unmatched_target.append(
            DiffViewItem(
                type="unmatched_target",
                record_key=rec.record_key,
                source_record=None,
                target_record=rec.record_data.get("fields", rec.record_data),
                target_metadata=rec.record_data.get("metadata"),
                diff_field_ids=None,
            )
        )

    return DiffViewResponse(
        matched_with_discrepancies=matched_with_discrepancies,
        unmatched_source=unmatched_source,
        unmatched_target=unmatched_target,
    )


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
