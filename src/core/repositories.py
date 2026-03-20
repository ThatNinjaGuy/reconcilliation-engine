"""Repository layer for metadata and results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session

from .models import (
    System,
    Schema,
    Dataset,
    Mapping,
    FieldMapping,
    RuleSet,
    ComparisonRule,
    ReferenceDataset,
    Job,
    ReconciliationRun,
    Discrepancy,
    MatchedRecordPair,
    UnmatchedRecord,
)
from .security import CredentialManager


class SystemRepository:
    def __init__(self, db: Session):
        self.db = db
        self.credential_manager = CredentialManager()

    def create(self, system: System) -> System:
        system.connection_config = self.credential_manager.encrypt_config(system.connection_config)
        self.db.add(system)
        self.db.commit()
        self.db.refresh(system)
        return system

    def get_by_id(self, system_id: str) -> Optional[System]:
        system = self.db.get(System, system_id)
        if not system:
            return None
        system.connection_config = self.credential_manager.decrypt_config(system.connection_config)
        return system

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[System]:
        stmt = select(System)
        if filters and "system_type" in filters:
            stmt = stmt.where(System.system_type == filters["system_type"])
        if filters and "is_active" in filters:
            stmt = stmt.where(System.is_active == filters["is_active"])
        systems = self.db.execute(stmt).scalars().all()
        for system in systems:
            system.connection_config = self.credential_manager.decrypt_config(system.connection_config)
        return systems

    def update(self, system_id: str, updates: Dict[str, Any]) -> Optional[System]:
        if "connection_config" in updates and updates["connection_config"] is not None:
            updates["connection_config"] = self.credential_manager.encrypt_config(updates["connection_config"])
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(update(System).where(System.system_id == system_id).values(**updates))
        self.db.commit()
        return self.get_by_id(system_id)

    def delete(self, system_id: str) -> bool:
        result = self.db.execute(delete(System).where(System.system_id == system_id))
        self.db.commit()
        return result.rowcount > 0


class SchemaRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, schema: Schema) -> Schema:
        self.validate_schema(schema.fields)
        self.db.add(schema)
        self.db.commit()
        self.db.refresh(schema)
        return schema

    def get_by_id(self, schema_id: str) -> Optional[Schema]:
        return self.db.get(Schema, schema_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Schema]:
        stmt = select(Schema)
        if filters and "is_active" in filters:
            stmt = stmt.where(Schema.is_active == filters["is_active"])
        return self.db.execute(stmt).scalars().all()

    def update(self, schema_id: str, updates: Dict[str, Any]) -> Optional[Schema]:
        if "fields" in updates and updates["fields"] is not None:
            self.validate_schema(updates["fields"])
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(update(Schema).where(Schema.schema_id == schema_id).values(**updates))
        self.db.commit()
        return self.get_by_id(schema_id)

    def delete(self, schema_id: str) -> bool:
        result = self.db.execute(delete(Schema).where(Schema.schema_id == schema_id))
        self.db.commit()
        return result.rowcount > 0

    def validate_schema(self, schema_fields: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(schema_fields, list):
            fields = schema_fields
        else:
            fields = schema_fields.get("fields", [])
        field_ids = [field.get("field_id") for field in fields]
        if len(field_ids) != len(set(field_ids)):
            raise ValueError("Schema field_id values must be unique")
        key_fields = [f for f in fields if f.get("is_key")]
        if not key_fields:
            raise ValueError("Schema must define at least one key field")
        for field in fields:
            data_type = field.get("data_type")
            if data_type == "DECIMAL":
                if field.get("precision") is None or field.get("scale") is None:
                    raise ValueError("DECIMAL fields require precision and scale")
        return {"valid": True}


class DatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, dataset: Dataset) -> Dataset:
        self.db.add(dataset)
        self.db.commit()
        self.db.refresh(dataset)
        return dataset

    def get_by_id(self, dataset_id: str) -> Optional[Dataset]:
        return self.db.get(Dataset, dataset_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Dataset]:
        stmt = select(Dataset)
        if filters and "system_id" in filters:
            stmt = stmt.where(Dataset.system_id == filters["system_id"])
        if filters and "is_active" in filters:
            stmt = stmt.where(Dataset.is_active == filters["is_active"])
        return self.db.execute(stmt).scalars().all()

    def update(self, dataset_id: str, updates: Dict[str, Any]) -> Optional[Dataset]:
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(update(Dataset).where(Dataset.dataset_id == dataset_id).values(**updates))
        self.db.commit()
        return self.get_by_id(dataset_id)

    def delete(self, dataset_id: str) -> bool:
        result = self.db.execute(delete(Dataset).where(Dataset.dataset_id == dataset_id))
        self.db.commit()
        return result.rowcount > 0


class ReferenceDatasetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, ref: ReferenceDataset) -> ReferenceDataset:
        self.db.add(ref)
        self.db.commit()
        self.db.refresh(ref)
        return ref

    def get_by_id(self, reference_dataset_id: str) -> Optional[ReferenceDataset]:
        return self.db.get(ReferenceDataset, reference_dataset_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[ReferenceDataset]:
        stmt = select(ReferenceDataset)
        if filters and "is_active" in filters:
            stmt = stmt.where(ReferenceDataset.is_active == filters["is_active"])
        return self.db.execute(stmt).scalars().all()

    def update(self, reference_dataset_id: str, updates: Dict[str, Any]) -> Optional[ReferenceDataset]:
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(
            update(ReferenceDataset)
            .where(ReferenceDataset.reference_dataset_id == reference_dataset_id)
            .values(**updates)
        )
        self.db.commit()
        return self.get_by_id(reference_dataset_id)

    def delete(self, reference_dataset_id: str) -> bool:
        result = self.db.execute(
            delete(ReferenceDataset).where(ReferenceDataset.reference_dataset_id == reference_dataset_id)
        )
        self.db.commit()
        return result.rowcount > 0


class MappingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_mapping(self, mapping: Mapping) -> Mapping:
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping

    def get_by_id(self, mapping_id: str) -> Optional[Mapping]:
        return self.db.get(Mapping, mapping_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Mapping]:
        stmt = select(Mapping)
        if filters and "is_active" in filters:
            stmt = stmt.where(Mapping.is_active == filters["is_active"])
        return self.db.execute(stmt).scalars().all()

    def update(self, mapping_id: str, updates: Dict[str, Any]) -> Optional[Mapping]:
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(update(Mapping).where(Mapping.mapping_id == mapping_id).values(**updates))
        self.db.commit()
        return self.get_by_id(mapping_id)

    def delete(self, mapping_id: str) -> bool:
        result = self.db.execute(delete(Mapping).where(Mapping.mapping_id == mapping_id))
        self.db.commit()
        return result.rowcount > 0

    def add_field_mapping(self, field_mapping: FieldMapping) -> FieldMapping:
        self.db.add(field_mapping)
        self.db.commit()
        self.db.refresh(field_mapping)
        return field_mapping

    def update_field_mapping(self, field_mapping_id: int, updates: Dict[str, Any]) -> Optional[FieldMapping]:
        self.db.execute(
            update(FieldMapping)
            .where(FieldMapping.field_mapping_id == field_mapping_id)
            .values(**updates)
        )
        self.db.commit()
        return self.db.get(FieldMapping, field_mapping_id)

    def delete_field_mapping(self, field_mapping_id: int) -> bool:
        result = self.db.execute(
            delete(FieldMapping).where(FieldMapping.field_mapping_id == field_mapping_id)
        )
        self.db.commit()
        return result.rowcount > 0

    def list_field_mappings(self, mapping_id: str) -> List[FieldMapping]:
        stmt = select(FieldMapping).where(FieldMapping.mapping_id == mapping_id)
        return self.db.execute(stmt).scalars().all()

    def get_field_mapping(self, field_mapping_id: int) -> Optional[FieldMapping]:
        return self.db.get(FieldMapping, field_mapping_id)


class RuleSetRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, rule_set: RuleSet) -> RuleSet:
        self.db.add(rule_set)
        self.db.commit()
        self.db.refresh(rule_set)
        return rule_set

    def get_by_id(self, rule_set_id: str) -> Optional[RuleSet]:
        return self.db.get(RuleSet, rule_set_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[RuleSet]:
        stmt = select(RuleSet)
        if filters and "is_active" in filters:
            stmt = stmt.where(RuleSet.is_active == filters["is_active"])
        return self.db.execute(stmt).scalars().all()

    def update(self, rule_set_id: str, updates: Dict[str, Any]) -> Optional[RuleSet]:
        updates["updated_at"] = datetime.utcnow()
        self.db.execute(update(RuleSet).where(RuleSet.rule_set_id == rule_set_id).values(**updates))
        self.db.commit()
        return self.get_by_id(rule_set_id)

    def delete(self, rule_set_id: str) -> bool:
        result = self.db.execute(delete(RuleSet).where(RuleSet.rule_set_id == rule_set_id))
        self.db.commit()
        return result.rowcount > 0

    def add_comparison_rule(self, rule: ComparisonRule) -> ComparisonRule:
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def list_comparison_rules(self, rule_set_id: str) -> List[ComparisonRule]:
        stmt = select(ComparisonRule).where(ComparisonRule.rule_set_id == rule_set_id)
        return self.db.execute(stmt).scalars().all()


class JobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, job: Job) -> Job:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: str) -> Optional[Job]:
        return self.db.get(Job, job_id)

    def list(self, filters: Optional[Dict[str, Any]] = None) -> List[Job]:
        stmt = select(Job)
        if filters and "rule_set_id" in filters:
            stmt = stmt.where(Job.rule_set_id == filters["rule_set_id"])
        if filters and "status" in filters:
            stmt = stmt.where(Job.status == filters["status"])
        return self.db.execute(stmt).scalars().all()

    def update(self, job_id: str, updates: Dict[str, Any]) -> Optional[Job]:
        self.db.execute(update(Job).where(Job.job_id == job_id).values(**updates))
        self.db.commit()
        return self.get_by_id(job_id)


class ResultRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_run(self, run: ReconciliationRun) -> ReconciliationRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def save_discrepancies(self, discrepancies: List[Discrepancy]) -> None:
        if discrepancies:
            self.db.add_all(discrepancies)
            self.db.commit()

    def save_matched_record_pairs(self, pairs: List[MatchedRecordPair]) -> None:
        if pairs:
            self.db.add_all(pairs)
            self.db.commit()

    def save_unmatched_records(self, records: List[UnmatchedRecord]) -> None:
        if records:
            self.db.add_all(records)
            self.db.commit()

    def save_partition_results(
        self,
        discrepancies: List[Discrepancy],
        matched_pairs: List[MatchedRecordPair],
        unmatched_records: List[UnmatchedRecord],
    ) -> None:
        """Persist one partition's results and release ORM objects from session."""
        if discrepancies:
            self.db.add_all(discrepancies)
        if matched_pairs:
            self.db.add_all(matched_pairs)
        if unmatched_records:
            self.db.add_all(unmatched_records)
        if discrepancies or matched_pairs or unmatched_records:
            self.db.commit()
            self.db.expire_all()

    def get_run(self, run_id: str) -> Optional[ReconciliationRun]:
        return self.db.get(ReconciliationRun, run_id)

    def get_discrepancies(self, run_id: str, filters: Dict[str, Any], limit: int, offset: int) -> List[Discrepancy]:
        stmt = select(Discrepancy).where(Discrepancy.run_id == run_id)
        if filters.get("field_id"):
            stmt = stmt.where(Discrepancy.field_id == filters["field_id"])
        if filters.get("severity"):
            stmt = stmt.where(Discrepancy.severity == filters["severity"])
        stmt = stmt.limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    def get_unmatched(self, run_id: str, side: str, limit: int, offset: int) -> List[UnmatchedRecord]:
        stmt = (
            select(UnmatchedRecord)
            .where(UnmatchedRecord.run_id == run_id)
            .where(UnmatchedRecord.side == side)
            .limit(limit)
            .offset(offset)
        )
        return self.db.execute(stmt).scalars().all()

    def get_matched_record_pairs(
        self, run_id: str, limit: int = 10000, offset: int = 0
    ) -> List[MatchedRecordPair]:
        stmt = (
            select(MatchedRecordPair)
            .where(MatchedRecordPair.run_id == run_id)
            .limit(limit)
            .offset(offset)
        )
        return self.db.execute(stmt).scalars().all()
