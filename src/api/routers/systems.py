"""Systems API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import System
from ...core.repositories import SystemRepository
from ...core.schemas import SystemCreate, SystemOut, SystemUpdate
from ...connectors.factory import ConnectorFactory

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=SystemOut, status_code=status.HTTP_201_CREATED)
def create_system(request: SystemCreate, db: Session = Depends(get_db)):
    repo = SystemRepository(db)
    system = System(**request.model_dump())
    created = repo.create(system)
    created.connection_config = _mask_connection_config(created.connection_config)
    return created


@router.get("", response_model=List[SystemOut])
def list_systems(
    system_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    repo = SystemRepository(db)
    filters = {}
    if system_type:
        filters["system_type"] = system_type
    if is_active is not None:
        filters["is_active"] = is_active
    systems = repo.list(filters)
    for system in systems:
        system.connection_config = _mask_connection_config(system.connection_config)
    return systems


@router.get("/{system_id}", response_model=SystemOut)
def get_system(system_id: str, db: Session = Depends(get_db)):
    repo = SystemRepository(db)
    system = repo.get_by_id(system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    system.connection_config = _mask_connection_config(system.connection_config)
    return system


@router.put("/{system_id}", response_model=SystemOut)
def update_system(system_id: str, request: SystemUpdate, db: Session = Depends(get_db)):
    repo = SystemRepository(db)
    system = repo.update(system_id, request.model_dump(exclude_unset=True))
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    system.connection_config = _mask_connection_config(system.connection_config)
    return system


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system(system_id: str, db: Session = Depends(get_db)):
    repo = SystemRepository(db)
    deleted = repo.delete(system_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="System not found")
    return None


@router.post("/{system_id}/test")
def test_system_connection(system_id: str, db: Session = Depends(get_db)):
    repo = SystemRepository(db)
    system = repo.get_by_id(system_id)
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    reader = ConnectorFactory.create_reader(
        system_type=system.system_type,
        system_config=system.connection_config,
        schema={"fields": []},
    )
    try:
        reader.connect()
        return {"status": "success", "system_id": system_id}
    finally:
        reader.disconnect()


def _mask_connection_config(config: dict) -> dict:
    masked = dict(config)
    sensitive = {"password", "connection_string", "api_key", "token", "secret"}
    for key in list(masked.keys()):
        if key in sensitive or key.endswith("_encrypted"):
            masked[key] = "***"
    return masked
