"""Mappings API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import Mapping, FieldMapping
from ...core.repositories import MappingRepository
from ...core.schemas import (
    FieldMappingCreate,
    FieldMappingOut,
    FieldMappingUpdate,
    MappingCreate,
    MappingOut,
    MappingUpdate,
)

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=MappingOut, status_code=status.HTTP_201_CREATED)
def create_mapping(request: MappingCreate, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    mapping = Mapping(**request.model_dump())
    return repo.create_mapping(mapping)


@router.get("", response_model=List[MappingOut])
def list_mappings(db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    return repo.list()


@router.get("/{mapping_id}", response_model=MappingOut)
def get_mapping(mapping_id: str, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    mapping = repo.get_by_id(mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.put("/{mapping_id}", response_model=MappingOut)
def update_mapping(mapping_id: str, request: MappingUpdate, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    mapping = repo.update(mapping_id, request.model_dump(exclude_unset=True))
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(mapping_id: str, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    deleted = repo.delete(mapping_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return None


@router.post("/{mapping_id}/field-mappings", response_model=FieldMappingOut, status_code=status.HTTP_201_CREATED)
def add_field_mapping(mapping_id: str, request: FieldMappingCreate, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    if mapping_id != request.mapping_id:
        raise HTTPException(status_code=400, detail="Mapping ID mismatch")
    field_mapping = FieldMapping(**request.model_dump())
    return repo.add_field_mapping(field_mapping)


@router.get("/{mapping_id}/field-mappings", response_model=List[FieldMappingOut])
def list_field_mappings(mapping_id: str, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    return repo.list_field_mappings(mapping_id)


@router.put("/{mapping_id}/field-mappings/{field_mapping_id}", response_model=FieldMappingOut)
def update_field_mapping(
    mapping_id: str,
    field_mapping_id: int,
    request: FieldMappingUpdate,
    db: Session = Depends(get_db),
):
    repo = MappingRepository(db)
    field_mapping = repo.update_field_mapping(field_mapping_id, request.model_dump(exclude_unset=True))
    if not field_mapping or field_mapping.mapping_id != mapping_id:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    return field_mapping


@router.delete("/{mapping_id}/field-mappings/{field_mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field_mapping(mapping_id: str, field_mapping_id: int, db: Session = Depends(get_db)):
    repo = MappingRepository(db)
    field_mapping = repo.get_field_mapping(field_mapping_id)
    if not field_mapping or field_mapping.mapping_id != mapping_id:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    deleted = repo.delete_field_mapping(field_mapping_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Field mapping not found")
    return None
