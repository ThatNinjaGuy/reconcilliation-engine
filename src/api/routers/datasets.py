"""Datasets API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import Dataset
from ...core.repositories import DatasetRepository, SystemRepository, SchemaRepository
from ...connectors.factory import ConnectorFactory
from ...core.schemas import DatasetCreate, DatasetOut, DatasetUpdate

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
def create_dataset(request: DatasetCreate, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    dataset = Dataset(**request.model_dump())
    return repo.create(dataset)


@router.get("", response_model=List[DatasetOut])
def list_datasets(
    system_id: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    repo = DatasetRepository(db)
    filters = {}
    if system_id:
        filters["system_id"] = system_id
    if is_active is not None:
        filters["is_active"] = is_active
    return repo.list(filters)


@router.get("/{dataset_id}", response_model=DatasetOut)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    dataset = repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.put("/{dataset_id}", response_model=DatasetOut)
def update_dataset(dataset_id: str, request: DatasetUpdate, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    dataset = repo.update(dataset_id, request.model_dump(exclude_unset=True))
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    repo = DatasetRepository(db)
    deleted = repo.delete(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return None


@router.get("/{dataset_id}/sample")
def sample_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset_repo = DatasetRepository(db)
    system_repo = SystemRepository(db)
    schema_repo = SchemaRepository(db)
    dataset = dataset_repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    system = system_repo.get_by_id(dataset.system_id)
    schema = schema_repo.get_by_id(dataset.schema_id)
    if not system or not schema:
        raise HTTPException(status_code=404, detail="System or schema not found")
    reader = ConnectorFactory.create_reader(system.system_type, system.connection_config, schema.fields)
    with reader:
        batch = reader.fetch_batch(
            dataset={"physical_name": dataset.physical_name, "filter_config": dataset.filter_config or {}},
            batch_size=10,
        )
    return [row.to_dict() for row in batch.rows]


@router.post("/{dataset_id}/validate")
def validate_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset_repo = DatasetRepository(db)
    system_repo = SystemRepository(db)
    schema_repo = SchemaRepository(db)
    dataset = dataset_repo.get_by_id(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    system = system_repo.get_by_id(dataset.system_id)
    schema = schema_repo.get_by_id(dataset.schema_id)
    if not system or not schema:
        raise HTTPException(status_code=404, detail="System or schema not found")
    reader = ConnectorFactory.create_reader(system.system_type, system.connection_config, schema.fields)
    with reader:
        return reader.validate_schema(
            dataset={"physical_name": dataset.physical_name, "filter_config": dataset.filter_config or {}}
        )
