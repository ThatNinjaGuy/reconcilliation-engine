"""Job orchestration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from sqlalchemy.orm import sessionmaker

from ..connectors.factory import ConnectorFactory
from ..connectors.base import CanonicalRow
from ..core.models import Job, ReconciliationRun, Discrepancy, UnmatchedRecord
from ..core.repositories import (
    SystemRepository,
    DatasetRepository,
    SchemaRepository,
    MappingRepository,
    RuleSetRepository,
    JobRepository,
    ResultRepository,
)
from ..reconciliation.engine import ReconciliationEngine
from ..transformation.mapping_interpreter import MappingInterpreter
from ..transformation.reference_manager import ReferenceDatasetManager
from ..transformation.transform_registry import TransformRegistry
from ..transformation.validators import ValidationEngine

logger = logging.getLogger(__name__)


class JobService:
    """Service for managing reconciliation jobs."""

    def __init__(self, session_factory: sessionmaker):
        self.session_factory = session_factory

    def create_job(self, rule_set_id: str, filters: Optional[Dict[str, Any]] = None) -> str:
        with self.session_factory() as db:
            job_repo = JobRepository(db)
            job_id = f"JOB_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}_{uuid.uuid4().hex[:6]}"
            job = Job(
                job_id=job_id,
                rule_set_id=rule_set_id,
                status="PENDING",
                created_at=datetime.utcnow(),
                filters=filters,
            )
            job_repo.create(job)
            return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.session_factory() as db:
            return JobRepository(db).get_by_id(job_id)

    def list_jobs(
        self,
        rule_set_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        with self.session_factory() as db:
            filters: Dict[str, Any] = {}
            if rule_set_id:
                filters["rule_set_id"] = rule_set_id
            if status:
                filters["status"] = status
            jobs = JobRepository(db).list(filters)
            return jobs[offset: offset + limit]

    def cancel_job(self, job_id: str) -> bool:
        with self.session_factory() as db:
            job_repo = JobRepository(db)
            job = job_repo.get_by_id(job_id)
            if not job or job.status not in {"PENDING", "RUNNING"}:
                return False
            job_repo.update(job_id, {"status": "CANCELLED", "completed_at": datetime.utcnow()})
            return True

    def execute_job(self, job_id: str) -> None:
        with self.session_factory() as db:
            job_repo = JobRepository(db)
            job = job_repo.get_by_id(job_id)
            if not job:
                logger.error("Job not found: %s", job_id)
                return
            if job.status == "CANCELLED":
                return

            job_repo.update(
                job_id,
                {"status": "RUNNING", "started_at": datetime.utcnow(), "progress_percent": 5},
            )

            try:
                rule_set_repo = RuleSetRepository(db)
                dataset_repo = DatasetRepository(db)
                schema_repo = SchemaRepository(db)
                mapping_repo = MappingRepository(db)
                system_repo = SystemRepository(db)
                result_repo = ResultRepository(db)

                rule_set = rule_set_repo.get_by_id(job.rule_set_id)
                if not rule_set:
                    raise ValueError("Rule set not found")

                source_dataset = dataset_repo.get_by_id(rule_set.source_dataset_id)
                target_dataset = dataset_repo.get_by_id(rule_set.target_dataset_id)
                if not source_dataset or not target_dataset:
                    raise ValueError("Datasets not found")

                source_schema = schema_repo.get_by_id(source_dataset.schema_id)
                target_schema = schema_repo.get_by_id(target_dataset.schema_id)
                if not source_schema or not target_schema:
                    raise ValueError("Schemas not found")

                mapping = mapping_repo.get_by_id(rule_set.mapping_id)
                if not mapping:
                    raise ValueError("Mapping not found")
                field_mappings = mapping_repo.list_field_mappings(mapping.mapping_id)
                comparison_rules = rule_set_repo.list_comparison_rules(rule_set.rule_set_id)

                source_system = system_repo.get_by_id(source_dataset.system_id)
                target_system = system_repo.get_by_id(target_dataset.system_id)
                if not source_system or not target_system:
                    raise ValueError("Systems not found")

                # Read source data
                source_reader = ConnectorFactory.create_reader(
                    system_type=source_system.system_type,
                    system_config=source_system.connection_config,
                    schema=source_schema.fields,
                )
                target_reader = ConnectorFactory.create_reader(
                    system_type=target_system.system_type,
                    system_config=target_system.connection_config,
                    schema=target_schema.fields,
                )

                source_rows = self._read_all(source_reader, source_dataset, job.filters)
                job_repo.update(job_id, {"progress_percent": 35})

                reference_manager = ReferenceDatasetManager()
                transform_registry = TransformRegistry()
                validation_engine = ValidationEngine()
                mapping_payload = {
                    "mapping_id": mapping.mapping_id,
                    "mapping_name": mapping.mapping_name,
                    "source_schema_id": mapping.source_schema_id,
                    "target_schema_id": mapping.target_schema_id,
                    "description": mapping.description,
                    "version": mapping.version,
                }
                field_mapping_payloads = [
                    {
                        "field_mapping_id": fm.field_mapping_id,
                        "mapping_id": fm.mapping_id,
                        "target_field_id": fm.target_field_id,
                        "source_expression": fm.source_expression,
                        "transform_chain": fm.transform_chain,
                        "pre_validations": fm.pre_validations,
                        "post_validations": fm.post_validations,
                        "is_active": fm.is_active,
                    }
                    for fm in field_mappings
                ]
                interpreter = MappingInterpreter(
                    mapping=mapping_payload,
                    field_mappings=field_mapping_payloads,
                    reference_manager=reference_manager,
                    transform_registry=transform_registry,
                    validation_engine=validation_engine,
                )
                transformed_rows = interpreter.transform_batch(source_rows)
                job_repo.update(job_id, {"progress_percent": 55})

                target_rows = self._read_all(target_reader, target_dataset, job.filters)
                job_repo.update(job_id, {"progress_percent": 70})

                comparison_rule_payloads = [
                    {
                        "comparison_rule_id": cr.comparison_rule_id,
                        "rule_set_id": cr.rule_set_id,
                        "target_field_id": cr.target_field_id,
                        "comparator_type": cr.comparator_type,
                        "comparator_params": cr.comparator_params,
                        "ignore_field": cr.ignore_field,
                        "is_active": cr.is_active,
                    }
                    for cr in comparison_rules
                ]
                matching_keys = rule_set.matching_keys
                if isinstance(matching_keys, dict) and "keys" in matching_keys:
                    matching_keys = matching_keys["keys"]
                recon_engine = ReconciliationEngine(
                    rule_set={
                        "rule_set_id": rule_set.rule_set_id,
                        "matching_keys": matching_keys,
                        "matching_strategy": rule_set.matching_strategy,
                    },
                    target_schema=target_schema.fields,
                    comparison_rules=comparison_rule_payloads,
                )
                result = recon_engine.reconcile(transformed_rows, target_rows)

                run_id = f"RUN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
                run = ReconciliationRun(
                    run_id=run_id,
                    rule_set_id=rule_set.rule_set_id,
                    status="COMPLETED",
                    started_at=datetime.fromisoformat(result.run_metadata["started_at"]),
                    completed_at=datetime.fromisoformat(result.run_metadata["completed_at"]),
                    total_source_records=result.summary_stats["total_source_records"],
                    total_target_records=result.summary_stats["total_target_records"],
                    matched_records=result.summary_stats["matched_records"],
                    matched_with_discrepancy=result.summary_stats["matched_with_discrepancy"],
                    unmatched_source_records=result.summary_stats["unmatched_source_records"],
                    unmatched_target_records=result.summary_stats["unmatched_target_records"],
                    summary_stats=result.summary_stats,
                    run_metadata=result.run_metadata,
                )
                result_repo.save_run(run)

                discrepancies = []
                for record_disc in result.record_discrepancies:
                    for field_disc in record_disc.field_discrepancies:
                        discrepancies.append(
                            Discrepancy(
                                run_id=run_id,
                                record_key=field_disc.key,
                                field_id=field_disc.field_id,
                                source_value=str(field_disc.source_value),
                                target_value=str(field_disc.target_value),
                                difference=field_disc.difference,
                                comparator_type=field_disc.comparator_type,
                                severity=field_disc.severity,
                            )
                        )
                if discrepancies:
                    result_repo.save_discrepancies(discrepancies)

                unmatched_records = []
                for row in result.match_result.unmatched_source:
                    unmatched_records.append(
                        UnmatchedRecord(
                            run_id=run_id,
                            side="source",
                            record_key=None,
                            record_data=row.to_dict(),
                        )
                    )
                for row in result.match_result.unmatched_target:
                    unmatched_records.append(
                        UnmatchedRecord(
                            run_id=run_id,
                            side="target",
                            record_key=None,
                            record_data=row.to_dict(),
                        )
                    )
                if unmatched_records:
                    result_repo.save_unmatched_records(unmatched_records)

                job_repo.update(
                    job_id,
                    {
                        "status": "COMPLETED",
                        "completed_at": datetime.utcnow(),
                        "progress_percent": 100,
                        "summary_stats": result.summary_stats,
                        "run_id": run_id,
                    },
                )
            except Exception as exc:
                logger.exception("Job failed: %s", job_id)
                job_repo.update(
                    job_id,
                    {
                        "status": "FAILED",
                        "completed_at": datetime.utcnow(),
                        "error_message": str(exc),
                        "progress_percent": 100,
                    },
                )

    def _read_all(self, reader, dataset, filters: Optional[Dict[str, Any]]) -> List[CanonicalRow]:
        batch_size = 10000
        rows: List[CanonicalRow] = []
        cursor = None
        with reader:
            while True:
                batch = reader.fetch_batch(
                    dataset={"physical_name": dataset.physical_name, "filter_config": dataset.filter_config or {}},
                    cursor=cursor,
                    batch_size=batch_size,
                    filters=filters,
                )
                rows.extend(batch.rows)
                if not batch.has_more:
                    break
                cursor = batch.cursor
        return rows
