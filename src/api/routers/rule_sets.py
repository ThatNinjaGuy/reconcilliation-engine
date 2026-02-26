"""Rule sets API routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...core.db import get_db
from ...core.models import RuleSet, ComparisonRule
from ...core.repositories import RuleSetRepository
from ...core.schemas import (
    RuleSetCreate,
    RuleSetOut,
    RuleSetUpdate,
    ComparisonRuleCreate,
    ComparisonRuleOut,
)

router = APIRouter(dependencies=[Depends(verify_token)])


@router.post("", response_model=RuleSetOut, status_code=status.HTTP_201_CREATED)
def create_rule_set(request: RuleSetCreate, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    rule_set = RuleSet(**request.model_dump())
    return repo.create(rule_set)


@router.get("", response_model=List[RuleSetOut])
def list_rule_sets(db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    return repo.list()


@router.get("/{rule_set_id}", response_model=RuleSetOut)
def get_rule_set(rule_set_id: str, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    rule_set = repo.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return rule_set


@router.put("/{rule_set_id}", response_model=RuleSetOut)
def update_rule_set(rule_set_id: str, request: RuleSetUpdate, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    rule_set = repo.update(rule_set_id, request.model_dump(exclude_unset=True))
    if not rule_set:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return rule_set


@router.delete("/{rule_set_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule_set(rule_set_id: str, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    deleted = repo.delete(rule_set_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return None


@router.post("/{rule_set_id}/comparison-rules", response_model=ComparisonRuleOut, status_code=status.HTTP_201_CREATED)
def add_comparison_rule(rule_set_id: str, request: ComparisonRuleCreate, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    if rule_set_id != request.rule_set_id:
        raise HTTPException(status_code=400, detail="Rule set ID mismatch")
    rule = ComparisonRule(**request.model_dump())
    return repo.add_comparison_rule(rule)


@router.get("/{rule_set_id}/comparison-rules", response_model=List[ComparisonRuleOut])
def list_comparison_rules(rule_set_id: str, db: Session = Depends(get_db)):
    repo = RuleSetRepository(db)
    return repo.list_comparison_rules(rule_set_id)
