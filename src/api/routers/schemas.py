"""Schemas API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import Schema
from ...core.repositories import SchemaRepository
from ...core.schemas import SchemaCreate, SchemaOut, SchemaUpdate

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=SchemaOut, status_code=status.HTTP_201_CREATED)
def create_schema(request: SchemaCreate, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    schema = Schema(**request.model_dump())
    return repo.create(schema)


@router.get("", response_model=List[SchemaOut])
def list_schemas(is_active: Optional[bool] = None, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    return repo.list(filters)


@router.get("/{schema_id}", response_model=SchemaOut)
def get_schema(schema_id: str, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    schema = repo.get_by_id(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema


@router.put("/{schema_id}", response_model=SchemaOut)
def update_schema(schema_id: str, request: SchemaUpdate, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    schema = repo.update(schema_id, request.model_dump(exclude_unset=True))
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return schema


@router.delete("/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schema(schema_id: str, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    deleted = repo.delete(schema_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schema not found")
    return None


@router.post("/{schema_id}/validate")
def validate_schema(schema_id: str, db: Session = Depends(get_db)):
    repo = SchemaRepository(db)
    schema = repo.get_by_id(schema_id)
    if not schema:
        raise HTTPException(status_code=404, detail="Schema not found")
    return repo.validate_schema(schema.fields)
