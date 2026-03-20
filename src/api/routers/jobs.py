"""Jobs API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from ..auth import verify_token
from ...core.db import SessionLocal
from ...core.schemas import JobCreateRequest, JobResponse
from ...orchestration.job_service import JobService

router = APIRouter(dependencies=[Depends(verify_token)])


def get_job_service() -> JobService:
    return JobService(SessionLocal)


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    request: JobCreateRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service),
):
    job_id = job_service.create_job(
        rule_set_id=request.rule_set_id,
        filters=request.filters,
        result_detail_level=request.result_detail_level.value,
    )
    background_tasks.add_task(job_service.execute_job, job_id)
    job = job_service.get_job(job_id)
    return job


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("", response_model=List[JobResponse])
def list_jobs(
    rule_set_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, le=500),
    offset: int = Query(0),
    job_service: JobService = Depends(get_job_service),
):
    return job_service.list_jobs(rule_set_id=rule_set_id, status=status_filter, limit=limit, offset=offset)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_job(job_id: str, job_service: JobService = Depends(get_job_service)):
    success = job_service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
    return None
