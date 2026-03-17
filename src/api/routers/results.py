"""Results API routes."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..auth import verify_token
from ...connectors.factory import ConnectorFactory
from ...reconciliation.matcher import RecordMatcher
from ...core.db import get_db
from ...core.repositories import (
    DatasetRepository,
    JobRepository,
    MappingRepository,
    ResultRepository,
    RuleSetRepository,
    SchemaRepository,
    SystemRepository,
)
from ...core.schemas import (
    DiffViewItem,
    DiffViewResponse,
    DiscrepancyResponse,
    SummaryStatsResponse,
)
from ...transformation.mapping_interpreter import MappingInterpreter
from ...transformation.reference_manager import ReferenceDatasetManager
from ...transformation.transform_registry import TransformRegistry
from ...transformation.validators import ValidationEngine

router = APIRouter(dependencies=[Depends(verify_token)])


@router.get("/{job_id}/summary", response_model=SummaryStatsResponse)
def get_summary(job_id: str, db: Session = Depends(get_db)):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    run = repo.get_run(job.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Results not found")
    stats = run.summary_stats or {}
    return SummaryStatsResponse(
        run_id=run.run_id,
        rule_set_id=run.rule_set_id,
        total_source_records=stats.get("total_source_records", 0),
        total_target_records=stats.get("total_target_records", 0),
        matched_records=stats.get("matched_records", 0),
        matched_with_no_discrepancy=stats.get("matched_with_no_discrepancy", 0),
        matched_with_discrepancy=stats.get("matched_with_discrepancy", 0),
        unmatched_source_records=stats.get("unmatched_source_records", 0),
        unmatched_target_records=stats.get("unmatched_target_records", 0),
        total_field_discrepancies=stats.get("total_field_discrepancies", 0),
        match_rate_percent=stats.get("match_rate_percent", 0.0),
        accuracy_rate_percent=stats.get("accuracy_rate_percent", 0.0),
        field_discrepancy_counts=stats.get("field_discrepancy_counts", {}),
    )


@router.get("/{job_id}/discrepancies", response_model=List[DiscrepancyResponse])
def get_discrepancies(
    job_id: str,
    field_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_discrepancies(
        run_id=job.run_id,
        filters={"field_id": field_id, "severity": severity},
        limit=limit,
        offset=offset,
    )
    return [
        DiscrepancyResponse(
            record_key=rec.record_key,
            field_id=rec.field_id,
            source_value=rec.source_value,
            target_value=rec.target_value,
            difference=rec.difference,
            comparator_type=rec.comparator_type,
            severity=rec.severity,
        )
        for rec in records
    ]


@router.get("/{job_id}/unmatched-source")
def get_unmatched_source(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_unmatched(
        run_id=job.run_id, side="source", limit=limit, offset=offset
    )
    return [record.record_data for record in records]


@router.get("/{job_id}/diff-view", response_model=DiffViewResponse)
def get_diff_view(
    job_id: str,
    limit: int = Query(500, le=5000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """Get full side-by-side diff data for UI: matched pairs with discrepancies, unmatched source, unmatched target."""
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    rule_set = RuleSetRepository(db).get_by_id(job.rule_set_id)
    matching_keys_cfg = rule_set.matching_keys if rule_set else None

    def _compute_record_key(fields: dict, side: str) -> Optional[str]:
        """Best-effort key computation for older unmatched rows missing record_key."""
        if not matching_keys_cfg:
            return fields.get("id") if isinstance(fields, dict) else None
        mk = matching_keys_cfg
        key_normalization = {}
        if isinstance(mk, dict):
            key_normalization = mk.get("key_normalization", {}) or {}
            mk = mk.get("keys", [])
        if not isinstance(mk, list) or not mk:
            return fields.get("id") if isinstance(fields, dict) else None
        trim_whitespace = bool(key_normalization.get("trim_whitespace", False))
        parts: list[str] = []
        for key_cfg in mk:
            if not isinstance(key_cfg, dict):
                continue
            field_name = key_cfg.get(f"{side}_field")
            if not field_name:
                continue
            is_case_sensitive = key_cfg.get("is_case_sensitive", True)
            v = fields.get(field_name, "")
            v = "" if v is None else str(v)
            if trim_whitespace:
                v = v.strip()
            if not is_case_sensitive:
                v = v.lower()
            parts.append(v)
        if not parts:
            return fields.get("id") if isinstance(fields, dict) else None
        return "|".join(parts)

    def _reconstruct_full_records_for_keys(
        record_keys: list[str],
    ) -> dict[str, dict[str, Optional[dict]]]:
        """Reconstruct full source/target records for legacy runs missing matched-pair rows.

        This is only used when matched pairs are absent but discrepancies exist.
        """
        if not rule_set or not record_keys:
            return {}

        dataset_repo = DatasetRepository(db)
        schema_repo = SchemaRepository(db)
        mapping_repo = MappingRepository(db)
        system_repo = SystemRepository(db)

        source_dataset = dataset_repo.get_by_id(rule_set.source_dataset_id)
        target_dataset = dataset_repo.get_by_id(rule_set.target_dataset_id)
        if not source_dataset or not target_dataset:
            return {}

        source_schema = schema_repo.get_by_id(source_dataset.schema_id)
        target_schema = schema_repo.get_by_id(target_dataset.schema_id)
        if not source_schema or not target_schema:
            return {}

        mapping = mapping_repo.get_by_id(rule_set.mapping_id)
        if not mapping:
            return {}
        field_mappings = mapping_repo.list_field_mappings(mapping.mapping_id)

        source_system = system_repo.get_by_id(source_dataset.system_id)
        target_system = system_repo.get_by_id(target_dataset.system_id)
        if not source_system or not target_system:
            return {}

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

        def _read_all(reader, dataset):
            rows = []
            cursor = None
            with reader:
                while True:
                    batch = reader.fetch_batch(
                        dataset={
                            "physical_name": dataset.physical_name,
                            "filter_config": dataset.filter_config or {},
                        },
                        cursor=cursor,
                        batch_size=10000,
                        filters=None,
                    )
                    rows.extend(batch.rows)
                    if not batch.has_more:
                        break
                    cursor = batch.cursor
            return rows

        source_rows = _read_all(source_reader, source_dataset)
        target_rows = _read_all(target_reader, target_dataset)

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
        transformed_source_rows = interpreter.transform_batch(source_rows)

        matching_config: dict = {
            "matching_keys": rule_set.matching_keys,
            "matching_strategy": rule_set.matching_strategy,
        }
        if isinstance(rule_set.matching_keys, dict):
            mk = rule_set.matching_keys
            if "keys" in mk:
                matching_config["matching_keys"] = mk["keys"]
            if "key_normalization" in mk:
                matching_config["key_normalization"] = mk["key_normalization"]
        matcher = RecordMatcher(matching_config)

        def _index(rows, side: str):
            idx: dict[str, list] = {}
            for r in rows:
                k = matcher._extract_matching_key(r, side)
                idx.setdefault(k, []).append(r)
            return idx

        src_index = _index(transformed_source_rows, "source")
        tgt_index = _index(target_rows, "target")

        out: dict[str, dict[str, Optional[dict]]] = {}
        for k in record_keys:
            src = (src_index.get(k) or [None])[0]
            tgt = (tgt_index.get(k) or [None])[0]
            out[k] = {
                "source_record": src.fields if src else None,
                "target_record": tgt.fields if tgt else None,
                "source_metadata": src.metadata if src else None,
                "target_metadata": tgt.metadata if tgt else None,
            }
        return out

    matched_with_discrepancies: List[DiffViewItem] = []
    # Prefer V2 (includes line/row metadata); fall back to V1 if empty.
    v2_pairs = repo.get_matched_record_pairs_v2(job.run_id, limit=limit, offset=offset)
    if v2_pairs:
        for pair in v2_pairs:
            matched_with_discrepancies.append(
                DiffViewItem(
                    type="matched_discrepancy",
                    record_key=pair.record_key,
                    source_record=pair.source_record,
                    target_record=pair.target_record,
                    source_metadata=pair.source_metadata,
                    target_metadata=pair.target_metadata,
                    diff_field_ids=pair.diff_field_ids,
                )
            )
    else:
        v1_pairs = repo.get_matched_record_pairs(job.run_id, limit=limit, offset=offset)
        for pair in v1_pairs:
            matched_with_discrepancies.append(
                DiffViewItem(
                    type="matched_discrepancy",
                    record_key=pair.record_key,
                    source_record=pair.source_record,
                    target_record=pair.target_record,
                    diff_field_ids=pair.diff_field_ids,
                )
            )
        # Backward-compatibility: some older runs may have discrepancies persisted
        # but no matched_record_pairs rows. In that case, synthesize minimal diff
        # items from the discrepancies table so the UI's Diff View isn't empty.
        if not v1_pairs:
            disc_rows = repo.get_discrepancies(
                run_id=job.run_id,
                filters={"field_id": None, "severity": None},
                limit=limit,
                offset=offset,
            )
            by_key: dict[str, set[str]] = {}
            for d in disc_rows:
                by_key.setdefault(d.record_key, set()).add(d.field_id)
            reconstructed = _reconstruct_full_records_for_keys(list(by_key.keys()))
            for key, field_ids in by_key.items():
                rec = reconstructed.get(key, {})
                matched_with_discrepancies.append(
                    DiffViewItem(
                        type="matched_discrepancy",
                        record_key=key,
                        source_record=rec.get("source_record"),
                        target_record=rec.get("target_record"),
                        source_metadata=rec.get("source_metadata"),
                        target_metadata=rec.get("target_metadata"),
                        diff_field_ids=sorted(field_ids),
                    )
                )

    unmatched_source: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "source", limit=limit, offset=offset):
        src_fields = (
            rec.record_data.get("fields", rec.record_data)
            if isinstance(rec.record_data, dict)
            else {}
        )
        unmatched_source.append(
            DiffViewItem(
                type="unmatched_source",
                record_key=rec.record_key or _compute_record_key(src_fields, "source"),
                source_record=src_fields,
                source_metadata=rec.record_data.get("metadata"),
                target_record=None,
                diff_field_ids=None,
            )
        )

    unmatched_target: List[DiffViewItem] = []
    for rec in repo.get_unmatched(job.run_id, "target", limit=limit, offset=offset):
        tgt_fields = (
            rec.record_data.get("fields", rec.record_data)
            if isinstance(rec.record_data, dict)
            else {}
        )
        unmatched_target.append(
            DiffViewItem(
                type="unmatched_target",
                record_key=rec.record_key or _compute_record_key(tgt_fields, "target"),
                source_record=None,
                target_record=tgt_fields,
                target_metadata=rec.record_data.get("metadata"),
                diff_field_ids=None,
            )
        )

    return DiffViewResponse(
        matched_with_discrepancies=matched_with_discrepancies,
        unmatched_source=unmatched_source,
        unmatched_target=unmatched_target,
    )


@router.get("/{job_id}/unmatched-target")
def get_unmatched_target(
    job_id: str,
    limit: int = Query(100, le=10000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    job_repo = JobRepository(db)
    job = job_repo.get_by_id(job_id)
    if not job or not job.run_id:
        raise HTTPException(status_code=404, detail="Results not found")
    repo = ResultRepository(db)
    records = repo.get_unmatched(
        run_id=job.run_id, side="target", limit=limit, offset=offset
    )
    return [record.record_data for record in records]
