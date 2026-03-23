"""Partitioned reconciliation engine for memory-bounded processing.

Designed for large file-based datasets (100M+ rows).  The algorithm:

  Pass 1  – Stream source file, transform each row, compute matching key +
            row hash, write to one of P partition files (keyed by hash(key) % P).
  Pass 1b – Stream target file, compute matching key + row hash, partition
            identically.
  Pass 2  – For each partition: load both sides, match by key, compare
            row-hashes (skip field comparison when equal), detect discrepancies,
            persist results, release memory.

Peak memory is O(max_partition_size) instead of O(total_dataset_size).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import RECON_TEMP_DIR, RECON_PARTITION_COUNT
from ..connectors.base import CanonicalRow, DatasetReader
from ..core.models import (
    Discrepancy,
    MatchedRecordPair,
    ReconciliationRun,
    UnmatchedRecord,
)
from ..core.repositories import JobRepository, ResultRepository
from ..transformation.mapping_interpreter import MappingInterpreter
from .comparator import FieldComparator
from .discrepancy_detector import DiscrepancyDetector, RecordDiscrepancy
from .matcher import MatchedPair, MatchResult, RecordMatcher

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def stable_partition_id(key: str, num_partitions: int) -> int:
    """Deterministic partition assignment using MD5 (consistent across runs)."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % num_partitions


def compute_row_hash(fields: Dict[str, Any], hash_field_ids: List[str]) -> str:
    """Deterministic hash of selected field values for fast equality check.

    Uses JSON serialization with sorted keys to avoid ambiguity from repr()
    or delimiter collisions.
    """
    snapshot = {fid: fields.get(fid) for fid in hash_field_ids}
    canonical = json.dumps(snapshot, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.md5(canonical.encode("utf-8")).hexdigest()


def _build_hash_field_ids(
    target_schema: Dict[str, Any],
    comparison_rules: List[Dict[str, Any]],
) -> List[str]:
    """Return sorted list of field_ids to include in the row hash.

    Excludes key fields and fields marked ignore_field in comparison rules.
    """
    ignore_fields = {
        r["target_field_id"]
        for r in comparison_rules
        if r.get("is_active", True) and r.get("ignore_field", False)
    }
    key_fields = {
        f["field_id"]
        for f in target_schema.get("fields", [])
        if f.get("is_key", False)
    }
    return sorted(
        f["field_id"]
        for f in target_schema.get("fields", [])
        if f["field_id"] not in ignore_fields and f["field_id"] not in key_fields
    )


# ---------------------------------------------------------------------------
# Partition writer / reader
# ---------------------------------------------------------------------------

class _PartitionWriter:
    """Manages P JSONL partition files for one side (source or target)."""

    def __init__(self, base_dir: Path, side: str, num_partitions: int):
        self.base_dir = base_dir
        self.side = side
        self.num_partitions = num_partitions
        self._files: Dict[int, Any] = {}
        self._counts: Dict[int, int] = {}

    def open(self) -> None:
        part_dir = self.base_dir / self.side
        part_dir.mkdir(parents=True, exist_ok=True)
        for pid in range(self.num_partitions):
            path = part_dir / f"part_{pid:04d}.jsonl"
            self._files[pid] = open(path, "w", encoding="utf-8")
            self._counts[pid] = 0

    def write(self, partition_id: int, key: str, row_hash: str, fields: Dict, metadata: Dict) -> None:
        line = json.dumps(
            {"key": key, "hash": row_hash, "fields": fields, "metadata": metadata},
            default=str,
            separators=(",", ":"),
        )
        self._files[partition_id].write(line + "\n")
        self._counts[partition_id] = self._counts.get(partition_id, 0) + 1

    def close(self) -> None:
        for f in self._files.values():
            f.close()
        self._files.clear()

    @property
    def total_rows(self) -> int:
        return sum(self._counts.values())


def load_partition(base_dir: Path, side: str, partition_id: int) -> List[CanonicalRow]:
    """Load all rows from a single partition file back into CanonicalRow objects."""
    path = base_dir / side / f"part_{partition_id:04d}.jsonl"
    rows: List[CanonicalRow] = []
    if not path.exists():
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            meta = obj.get("metadata", {})
            meta["row_hash"] = obj["hash"]
            meta["_matching_key"] = obj["key"]
            rows.append(CanonicalRow(fields=obj["fields"], metadata=meta))
    return rows


# ---------------------------------------------------------------------------
# Aggregate stats accumulator
# ---------------------------------------------------------------------------

@dataclass
class _AggregateStats:
    total_source: int = 0
    total_target: int = 0
    matched: int = 0
    matched_no_discrepancy: int = 0
    matched_with_discrepancy: int = 0
    unmatched_source: int = 0
    unmatched_target: int = 0
    total_field_discrepancies: int = 0
    field_discrepancy_counts: Dict[str, int] = field(default_factory=dict)

    def add_partition(
        self,
        match_result: MatchResult,
        record_discrepancies: List[RecordDiscrepancy],
        hash_skip_count: int,
    ) -> None:
        self.total_source += match_result.match_stats["total_source"]
        self.total_target += match_result.match_stats["total_target"]
        self.matched += len(match_result.matched_pairs)
        self.unmatched_source += len(match_result.unmatched_source)
        self.unmatched_target += len(match_result.unmatched_target)
        self.matched_with_discrepancy += len(record_discrepancies)
        self.matched_no_discrepancy += hash_skip_count

        for rd in record_discrepancies:
            for fd in rd.field_discrepancies:
                self.field_discrepancy_counts[fd.field_id] = (
                    self.field_discrepancy_counts.get(fd.field_id, 0) + 1
                )
                self.total_field_discrepancies += 1

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "total_source_records": self.total_source,
            "total_target_records": self.total_target,
            "matched_records": self.matched,
            "matched_with_no_discrepancy": self.matched_no_discrepancy,
            "matched_with_discrepancy": self.matched_with_discrepancy,
            "unmatched_source_records": self.unmatched_source,
            "unmatched_target_records": self.unmatched_target,
            "total_field_discrepancies": self.total_field_discrepancies,
            "field_discrepancy_counts": self.field_discrepancy_counts,
            "match_rate_percent": (self.matched / max(self.total_source, 1)) * 100,
            "accuracy_rate_percent": (
                self.matched_no_discrepancy / max(self.matched, 1)
            ) * 100,
        }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_partitioned_reconciliation(
    *,
    job_id: str,
    run_id: str,
    source_reader: DatasetReader,
    target_reader: DatasetReader,
    source_dataset: Dict[str, Any],
    target_dataset: Dict[str, Any],
    interpreter: MappingInterpreter,
    matching_config: Dict[str, Any],
    target_schema: Dict[str, Any],
    comparison_rules: List[Dict[str, Any]],
    result_detail_level: str,
    job_repo: JobRepository,
    result_repo: ResultRepository,
) -> Dict[str, Any]:
    """Execute a full partitioned reconciliation for FILE datasets.

    Returns the summary_stats dict.
    """
    num_partitions = RECON_PARTITION_COUNT
    temp_base = Path(RECON_TEMP_DIR) / f"recon_{job_id}"

    matcher = RecordMatcher(matching_config)
    comparator = FieldComparator()
    detector = DiscrepancyDetector(
        target_schema=target_schema,
        comparison_rules=comparison_rules,
        comparator=comparator,
    )
    hash_field_ids = _build_hash_field_ids(target_schema, comparison_rules)
    agg = _AggregateStats()
    start_time = datetime.utcnow()

    try:
        temp_base.mkdir(parents=True, exist_ok=True)

        # Save run record early so partition results have a valid run_id
        run = ReconciliationRun(
            run_id=run_id,
            rule_set_id=matching_config.get("rule_set_id", ""),
            status="RUNNING",
            started_at=start_time,
        )
        result_repo.save_run(run)

        # ---- Pass 1: partition source ----
        logger.info("Pass 1: partitioning source data into %d partitions", num_partitions)
        src_writer = _PartitionWriter(temp_base, "source", num_partitions)
        src_writer.open()
        try:
            with source_reader:
                cursor = None
                while True:
                    batch = source_reader.fetch_batch(
                        dataset=source_dataset, cursor=cursor, batch_size=10000,
                    )
                    for row in batch.rows:
                        transformed = interpreter.transform_row(row)
                        key = matcher.extract_matching_key(transformed, "source")
                        row_hash = compute_row_hash(transformed.fields, hash_field_ids)
                        pid = stable_partition_id(key, num_partitions)
                        src_writer.write(pid, key, row_hash, transformed.fields, transformed.metadata)
                    if not batch.has_more:
                        break
                    cursor = batch.cursor
        finally:
            src_writer.close()

        logger.info("Source partitioned: %d rows", src_writer.total_rows)
        job_repo.update(job_id, {"progress_percent": 30})

        # ---- Pass 1b: partition target ----
        logger.info("Pass 1b: partitioning target data into %d partitions", num_partitions)
        tgt_writer = _PartitionWriter(temp_base, "target", num_partitions)
        tgt_writer.open()
        try:
            with target_reader:
                cursor = None
                while True:
                    batch = target_reader.fetch_batch(
                        dataset=target_dataset, cursor=cursor, batch_size=10000,
                    )
                    for row in batch.rows:
                        key = matcher.extract_matching_key(row, "target")
                        row_hash = compute_row_hash(row.fields, hash_field_ids)
                        pid = stable_partition_id(key, num_partitions)
                        tgt_writer.write(pid, key, row_hash, row.fields, row.metadata)
                    if not batch.has_more:
                        break
                    cursor = batch.cursor
        finally:
            tgt_writer.close()

        logger.info("Target partitioned: %d rows", tgt_writer.total_rows)
        job_repo.update(job_id, {"progress_percent": 50})

        # ---- Pass 2: reconcile each partition ----
        logger.info("Pass 2: reconciling %d partitions", num_partitions)
        for pid in range(num_partitions):
            src_rows = load_partition(temp_base, "source", pid)
            tgt_rows = load_partition(temp_base, "target", pid)

            if not src_rows and not tgt_rows:
                continue

            match_result = matcher.match(src_rows, tgt_rows)

            # Row-hash pre-comparison (Step 3)
            hash_skip_count = 0
            pairs_needing_comparison: List[MatchedPair] = []
            for pair in match_result.matched_pairs:
                src_hash = pair.source_row.metadata.get("row_hash")
                tgt_hash = pair.target_row.metadata.get("row_hash")
                if src_hash and tgt_hash and src_hash == tgt_hash:
                    hash_skip_count += 1
                else:
                    pairs_needing_comparison.append(pair)

            record_discrepancies = detector.detect(pairs_needing_comparison)
            compared_no_discrepancy = len(pairs_needing_comparison) - len(record_discrepancies)
            agg.add_partition(match_result, record_discrepancies, hash_skip_count + compared_no_discrepancy)

            # Persist partition results (Step 5: incremental)
            if result_detail_level == "FULL":
                p_discrepancies: List[Discrepancy] = []
                p_matched_pairs: List[MatchedRecordPair] = []
                p_unmatched: List[UnmatchedRecord] = []

                for rd in record_discrepancies:
                    diff_ids = [fd.field_id for fd in rd.field_discrepancies]
                    p_matched_pairs.append(
                        MatchedRecordPair(
                            run_id=run_id,
                            record_key=rd.key,
                            source_record=rd.source_record,
                            target_record=rd.target_record,
                            source_metadata=rd.source_metadata,
                            target_metadata=rd.target_metadata,
                            diff_field_ids=diff_ids,
                        )
                    )
                    for fd in rd.field_discrepancies:
                        p_discrepancies.append(
                            Discrepancy(
                                run_id=run_id,
                                record_key=fd.key,
                                field_id=fd.field_id,
                                source_value=str(fd.source_value),
                                target_value=str(fd.target_value),
                                difference=fd.difference,
                                comparator_type=fd.comparator_type,
                                severity=fd.severity,
                            )
                        )

                for row in match_result.unmatched_source:
                    p_unmatched.append(
                        UnmatchedRecord(
                            run_id=run_id,
                            side="source",
                            record_key=row.metadata.get("_matching_key", ""),
                            record_data=row.to_dict(),
                        )
                    )
                for row in match_result.unmatched_target:
                    p_unmatched.append(
                        UnmatchedRecord(
                            run_id=run_id,
                            side="target",
                            record_key=row.metadata.get("_matching_key", ""),
                            record_data=row.to_dict(),
                        )
                    )

                result_repo.save_partition_results(p_discrepancies, p_matched_pairs, p_unmatched)

            # Free partition memory
            del src_rows, tgt_rows, match_result, pairs_needing_comparison, record_discrepancies

            progress = 50 + int((pid + 1) / num_partitions * 45)
            if pid % max(1, num_partitions // 20) == 0:
                job_repo.update(job_id, {"progress_percent": min(progress, 95)})

        # ---- Finalize ----
        end_time = datetime.utcnow()
        summary_stats = agg.to_summary_dict()
        run_metadata = {
            "rule_set_id": matching_config.get("rule_set_id", ""),
            "started_at": start_time.isoformat(),
            "completed_at": end_time.isoformat(),
            "duration_ms": (end_time - start_time).total_seconds() * 1000,
            "num_partitions": num_partitions,
            "source_rows_partitioned": src_writer.total_rows,
            "target_rows_partitioned": tgt_writer.total_rows,
        }

        # Update the existing run record (created early with RUNNING status)
        db = result_repo.db
        existing_run = db.get(ReconciliationRun, run_id)
        if existing_run:
            existing_run.status = "COMPLETED"
            existing_run.completed_at = end_time
            existing_run.total_source_records = summary_stats["total_source_records"]
            existing_run.total_target_records = summary_stats["total_target_records"]
            existing_run.matched_records = summary_stats["matched_records"]
            existing_run.matched_with_discrepancy = summary_stats["matched_with_discrepancy"]
            existing_run.unmatched_source_records = summary_stats["unmatched_source_records"]
            existing_run.unmatched_target_records = summary_stats["unmatched_target_records"]
            existing_run.summary_stats = summary_stats
            existing_run.run_metadata = run_metadata
            db.commit()

        logger.info(
            "Partitioned reconciliation complete: %d matched, %d discrepant, %d unmatched-src, %d unmatched-tgt",
            summary_stats["matched_records"],
            summary_stats["matched_with_discrepancy"],
            summary_stats["unmatched_source_records"],
            summary_stats["unmatched_target_records"],
        )
        return summary_stats

    finally:
        if temp_base.exists():
            shutil.rmtree(temp_base, ignore_errors=True)
            logger.info("Cleaned up temp directory: %s", temp_base)
