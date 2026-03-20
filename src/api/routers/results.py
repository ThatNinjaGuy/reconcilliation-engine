"""Results API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.repositories import (
    JobRepository,
    ResultRepository,
    RuleSetRepository,
)
from ...core.schemas import (
    DiffViewItem,
    DiffViewResponse,
    DiscrepancyResponse,
    SummaryStatsResponse,
)

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
    records = repo.get_unmatched(
        run_id=job.run_id, side="source", limit=limit, offset=offset
    )
    return [record.record_data for record in records]


def _compute_record_key(fields: dict, side: str, matching_keys_cfg) -> Optional[str]:
    """Compute record key from fields using matching key configuration."""
    if not matching_keys_cfg:
        return fields.get("id") if isinstance(fields, dict) else None
    mk = matching_keys_cfg
    key_normalization = {}
    if isinstance(mk, dict):
        key_normalization = mk.get("key_normalization", {}) or {}
        mk = mk.get("keys", [])
    if not isinstance(mk, list) or not mk:
        return fields.get("id") if isinstance(fields, dict) else None
    trim_whitespace = bool(key_normalization.get("trim_whitespace", False))
    parts: list[str] = []
    for key_cfg in mk:
        if not isinstance(key_cfg, dict):
            continue
        field_name = key_cfg.get(f"{side}_field")
        if not field_name:
            continue
        is_case_sensitive = key_cfg.get("is_case_sensitive", True)
        v = fields.get(field_name, "")
        v = "" if v is None else str(v)
        if trim_whitespace:
            v = v.strip()
        if not is_case_sensitive:
            v = v.lower()
        parts.append(v)
    if not parts:
        return fields.get("id") if isinstance(fields, dict) else None
    return "|".join(parts)


@router.get("/{job_id}/diff-view", response_model=DiffViewResponse)
def get_diff_view(
    job_id: str,
    limit: int = Query(500, le=5000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """Side-by-side diff: matched pairs with discrepancies, unmatched source, unmatched target."""
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    rule_set = RuleSetRepository(db).get_by_id(job.rule_set_id)
    matching_keys_cfg = rule_set.matching_keys if rule_set else None

    pairs = repo.get_matched_record_pairs(job.run_id, limit=limit, offset=offset)
    matched_with_discrepancies: List[DiffViewItem] = [
        DiffViewItem(
            type="matched_discrepancy",
            record_key=pair.record_key,
            source_record=pair.source_record,
            target_record=pair.target_record,
            source_metadata=pair.source_metadata,
            target_metadata=pair.target_metadata,
            diff_field_ids=pair.diff_field_ids,
        )
        for pair in pairs
    ]

    unmatched_source: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "source", limit=limit, offset=offset):
        src_fields = (
            rec.record_data.get("fields", rec.record_data)
            if isinstance(rec.record_data, dict)
            else {}
        )
        unmatched_source.append(
            DiffViewItem(
                type="unmatched_source",
                record_key=rec.record_key or _compute_record_key(src_fields, "source", matching_keys_cfg),
                source_record=src_fields,
                source_metadata=rec.record_data.get("metadata") if isinstance(rec.record_data, dict) else None,
                target_record=None,
                diff_field_ids=None,
            )
        )

    unmatched_target: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "target", limit=limit, offset=offset):
        tgt_fields = (
            rec.record_data.get("fields", rec.record_data)
            if isinstance(rec.record_data, dict)
            else {}
        )
        unmatched_target.append(
            DiffViewItem(
                type="unmatched_target",
                record_key=rec.record_key or _compute_record_key(tgt_fields, "target", matching_keys_cfg),
                source_record=None,
                target_record=tgt_fields,
                target_metadata=rec.record_data.get("metadata") if isinstance(rec.record_data, dict) else None,
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
    records = repo.get_unmatched(
        run_id=job.run_id, side="target", limit=limit, offset=offset
    )
    return [record.record_data for record in records]
