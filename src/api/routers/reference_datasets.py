"""Reference datasets API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import ReferenceDataset
from ...core.repositories import ReferenceDatasetRepository
from ...core.schemas import (
    ReferenceDatasetCreate,
    ReferenceDatasetOut,
    ReferenceDatasetUpdate,
)

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=ReferenceDatasetOut, status_code=status.HTTP_201_CREATED)
def create_reference_dataset(request: ReferenceDatasetCreate, db: Session = Depends(get_db)):
    repo = ReferenceDatasetRepository(db)
    ref = ReferenceDataset(**request.model_dump())
    return repo.create(ref)


@router.get("", response_model=List[ReferenceDatasetOut])
def list_reference_datasets(is_active: Optional[bool] = None, db: Session = Depends(get_db)):
    repo = ReferenceDatasetRepository(db)
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    return repo.list(filters)


@router.get("/{reference_dataset_id}", response_model=ReferenceDatasetOut)
def get_reference_dataset(reference_dataset_id: str, db: Session = Depends(get_db)):
    repo = ReferenceDatasetRepository(db)
    ref = repo.get_by_id(reference_dataset_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Reference dataset not found")
    return ref


@router.put("/{reference_dataset_id}", response_model=ReferenceDatasetOut)
def update_reference_dataset(
    reference_dataset_id: str,
    request: ReferenceDatasetUpdate,
    db: Session = Depends(get_db),
):
    repo = ReferenceDatasetRepository(db)
    ref = repo.update(reference_dataset_id, request.model_dump(exclude_unset=True))
    if not ref:
        raise HTTPException(status_code=404, detail="Reference dataset not found")
    return ref


@router.delete("/{reference_dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reference_dataset(reference_dataset_id: str, db: Session = Depends(get_db)):
    repo = ReferenceDatasetRepository(db)
    deleted = repo.delete(reference_dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reference dataset not found")
    return None
