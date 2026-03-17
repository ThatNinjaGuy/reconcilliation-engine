"""SQLAlchemy models for metadata, jobs, and results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .db import Base
from ..config import DATABASE_URL


def _json_type():
    """Return JSONB for PostgreSQL, JSON for other databases."""
    db_url = DATABASE_URL.lower()
    if "postgresql" in db_url or "postgres" in db_url:
        return JSONB
    return JSON


JSONType = _json_type()


class System(Base):
    __tablename__ = "systems"

    system_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    system_name: Mapped[str] = mapped_column(String(200), nullable=False)
    system_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    connection_config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="system")


class Schema(Base):
    __tablename__ = "schemas"

    schema_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    schema_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    fields: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    constraints: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    datasets: Mapped[list["Dataset"]] = relationship(back_populates="schema")


class Dataset(Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String(200), nullable=False)
    system_id: Mapped[str] = mapped_column(
        ForeignKey("systems.system_id"), nullable=False
    )
    schema_id: Mapped[str] = mapped_column(
        ForeignKey("schemas.schema_id"), nullable=False
    )
    physical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    partition_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    filter_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    dataset_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata", JSONType
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))

    system: Mapped[System] = relationship(back_populates="datasets")
    schema: Mapped[Schema] = relationship(back_populates="datasets")


class ReferenceDataset(Base):
    __tablename__ = "reference_datasets"

    reference_dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    reference_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    key_fields: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    value_fields: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    cache_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    refresh_schedule: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))


class Mapping(Base):
    __tablename__ = "mappings"

    mapping_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    mapping_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_schema_id: Mapped[str] = mapped_column(
        ForeignKey("schemas.schema_id"), nullable=False
    )
    target_schema_id: Mapped[str] = mapped_column(
        ForeignKey("schemas.schema_id"), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    field_mapping_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    mapping_id: Mapped[str] = mapped_column(
        ForeignKey("mappings.mapping_id"), nullable=False
    )
    target_field_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_expression: Mapped[Optional[str]] = mapped_column(Text)
    transform_chain: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    pre_validations: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    post_validations: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RuleSet(Base):
    __tablename__ = "reconciliation_rule_sets"

    rule_set_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    rule_set_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.dataset_id"), nullable=False
    )
    target_dataset_id: Mapped[str] = mapped_column(
        ForeignKey("datasets.dataset_id"), nullable=False
    )
    mapping_id: Mapped[str] = mapped_column(
        ForeignKey("mappings.mapping_id"), nullable=False
    )
    matching_strategy: Mapped[str] = mapped_column(String(50), default="EXACT")
    matching_keys: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    scope_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    tolerance_config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100))


class ComparisonRule(Base):
    __tablename__ = "comparison_rules"

    comparison_rule_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    rule_set_id: Mapped[str] = mapped_column(
        ForeignKey("reconciliation_rule_sets.rule_set_id"), nullable=False
    )
    target_field_id: Mapped[str] = mapped_column(String(100), nullable=False)
    comparator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    comparator_params: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    ignore_field: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    run_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    rule_set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    total_source_records: Mapped[Optional[int]] = mapped_column(Integer)
    total_target_records: Mapped[Optional[int]] = mapped_column(Integer)
    matched_records: Mapped[Optional[int]] = mapped_column(Integer)
    matched_with_discrepancy: Mapped[Optional[int]] = mapped_column(Integer)
    unmatched_source_records: Mapped[Optional[int]] = mapped_column(Integer)
    unmatched_target_records: Mapped[Optional[int]] = mapped_column(Integer)
    summary_stats: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    run_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)


class Discrepancy(Base):
    __tablename__ = "discrepancies"

    discrepancy_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    record_key: Mapped[str] = mapped_column(String(500), nullable=False)
    field_id: Mapped[str] = mapped_column(String(100), nullable=False)
    source_value: Mapped[Optional[str]] = mapped_column(Text)
    target_value: Mapped[Optional[str]] = mapped_column(Text)
    difference: Mapped[str] = mapped_column(Text, nullable=False)
    comparator_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="ERROR")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchedRecordPair(Base):
    """Full source/target record pairs with discrepancies, for diff-view UI."""

    __tablename__ = "matched_record_pairs"

    pair_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    record_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    target_record: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    diff_field_ids: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchedRecordPairV2(Base):
    """Matched pairs with both records + metadata (for line numbers)."""

    __tablename__ = "matched_record_pairs_v2"

    pair_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    record_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source_record: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    target_record: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    source_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    target_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    diff_field_ids: Mapped[list[str]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UnmatchedRecord(Base):
    __tablename__ = "unmatched_records"

    record_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # source|target
    record_key: Mapped[Optional[str]] = mapped_column(String(500))
    record_data: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    rule_set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    progress_percent: Mapped[Optional[int]] = mapped_column(Integer)
    summary_stats: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    run_id: Mapped[Optional[str]] = mapped_column(String(100))
    filters: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType)
