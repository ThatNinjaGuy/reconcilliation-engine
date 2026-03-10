"""Pydantic schemas for API request/response."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class SystemType(str, Enum):
    ORACLE = "ORACLE"
    MONGODB = "MONGODB"
    FILE = "FILE"
    API = "API"


class DataType(str, Enum):
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIMESTAMP = "TIMESTAMP"
    ARRAY = "ARRAY"
    OBJECT = "OBJECT"


class DatasetType(str, Enum):
    TABLE = "TABLE"
    COLLECTION = "COLLECTION"
    FILE = "FILE"
    VIEW = "VIEW"


class MatchingStrategy(str, Enum):
    EXACT = "EXACT"
    FUZZY = "FUZZY"


class ComparatorType(str, Enum):
    EXACT = "EXACT"
    NUMERIC_TOLERANCE = "NUMERIC_TOLERANCE"
    DATE_WINDOW = "DATE_WINDOW"
    CASE_INSENSITIVE = "CASE_INSENSITIVE"
    REGEX = "REGEX"
    CUSTOM = "CUSTOM"
    NULL_EQUALS_EMPTY = "NULL_EQUALS_EMPTY"


class SystemBase(BaseModel):
    system_id: str
    system_name: str
    system_type: SystemType
    description: Optional[str] = None
    connection_config: Dict[str, Any]
    is_active: bool = True


class SystemCreate(SystemBase):
    pass


class SystemUpdate(BaseModel):
    system_name: Optional[str] = None
    description: Optional[str] = None
    connection_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SystemOut(SystemBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SchemaField(BaseModel):
    field_id: str
    field_name: str
    data_type: DataType
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    is_nullable: bool = True
    is_key: bool = False
    description: Optional[str] = None
    physical_mapping: Dict[str, Any]


class SchemaBase(BaseModel):
    schema_id: str
    schema_name: str
    description: Optional[str] = None
    version: int = 1
    fields: Dict[str, Any]
    constraints: Optional[Dict[str, Any]] = None
    is_active: bool = True


class SchemaCreate(SchemaBase):
    pass


class SchemaUpdate(BaseModel):
    schema_name: Optional[str] = None
    description: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SchemaOut(SchemaBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DatasetBase(BaseModel):
    dataset_id: str
    dataset_name: str
    system_id: str
    schema_id: str
    physical_name: str
    dataset_type: DatasetType
    partition_config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None
    dataset_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("dataset_metadata", "metadata"),
        serialization_alias="metadata",
    )
    is_active: bool = True

    model_config = ConfigDict(populate_by_name=True)


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    dataset_name: Optional[str] = None
    physical_name: Optional[str] = None
    partition_config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None
    dataset_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        validation_alias=AliasChoices("dataset_metadata", "metadata"),
        serialization_alias="metadata",
    )
    is_active: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class DatasetOut(DatasetBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReferenceDatasetBase(BaseModel):
    reference_dataset_id: str
    reference_name: str
    description: Optional[str] = None
    source_type: str
    source_config: Dict[str, Any]
    key_fields: Dict[str, Any]
    value_fields: Optional[Dict[str, Any]] = None
    cache_config: Optional[Dict[str, Any]] = None
    refresh_schedule: Optional[str] = None
    is_active: bool = True


class ReferenceDatasetCreate(ReferenceDatasetBase):
    pass


class ReferenceDatasetUpdate(BaseModel):
    reference_name: Optional[str] = None
    description: Optional[str] = None
    source_config: Optional[Dict[str, Any]] = None
    key_fields: Optional[Dict[str, Any]] = None
    value_fields: Optional[Dict[str, Any]] = None
    cache_config: Optional[Dict[str, Any]] = None
    refresh_schedule: Optional[str] = None
    is_active: Optional[bool] = None


class ReferenceDatasetOut(ReferenceDatasetBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class MappingBase(BaseModel):
    mapping_id: str
    mapping_name: str
    source_schema_id: str
    target_schema_id: str
    description: Optional[str] = None
    version: int = 1
    is_active: bool = True


class MappingCreate(MappingBase):
    pass


class MappingUpdate(BaseModel):
    mapping_name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MappingOut(MappingBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FieldMappingBase(BaseModel):
    mapping_id: str
    target_field_id: str
    source_expression: Optional[str] = None
    transform_chain: Optional[Dict[str, Any]] = None
    pre_validations: Optional[Dict[str, Any]] = None
    post_validations: Optional[Dict[str, Any]] = None
    is_active: bool = True


class FieldMappingCreate(FieldMappingBase):
    pass


class FieldMappingUpdate(BaseModel):
    target_field_id: Optional[str] = None
    source_expression: Optional[str] = None
    transform_chain: Optional[Dict[str, Any]] = None
    pre_validations: Optional[Dict[str, Any]] = None
    post_validations: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class FieldMappingOut(FieldMappingBase):
    field_mapping_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RuleSetBase(BaseModel):
    rule_set_id: str
    rule_set_name: str
    source_dataset_id: str
    target_dataset_id: str
    mapping_id: str
    matching_strategy: MatchingStrategy = MatchingStrategy.EXACT
    matching_keys: Dict[str, Any]
    scope_config: Optional[Dict[str, Any]] = None
    tolerance_config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class RuleSetCreate(RuleSetBase):
    pass


class RuleSetUpdate(BaseModel):
    rule_set_name: Optional[str] = None
    matching_strategy: Optional[MatchingStrategy] = None
    matching_keys: Optional[Dict[str, Any]] = None
    scope_config: Optional[Dict[str, Any]] = None
    tolerance_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RuleSetOut(RuleSetBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ComparisonRuleBase(BaseModel):
    rule_set_id: str
    target_field_id: str
    comparator_type: ComparatorType
    comparator_params: Optional[Dict[str, Any]] = None
    ignore_field: bool = False
    is_active: bool = True


class ComparisonRuleCreate(ComparisonRuleBase):
    pass


class ComparisonRuleOut(ComparisonRuleBase):
    comparison_rule_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class JobCreateRequest(BaseModel):
    rule_set_id: str
    filters: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    job_id: str
    rule_set_id: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percent: Optional[int] = None
    summary_stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    run_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DiscrepancyResponse(BaseModel):
    record_key: str
    field_id: str
    source_value: Optional[str] = None
    target_value: Optional[str] = None
    difference: str
    comparator_type: str
    severity: str


class SummaryStatsResponse(BaseModel):
    run_id: str
    rule_set_id: str
    total_source_records: int
    total_target_records: int
    matched_records: int
    matched_with_no_discrepancy: int
    matched_with_discrepancy: int
    unmatched_source_records: int
    unmatched_target_records: int
    total_field_discrepancies: int
    match_rate_percent: float
    accuracy_rate_percent: float
    field_discrepancy_counts: Dict[str, int]
