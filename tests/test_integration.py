"""Integration tests: full reconciliation pipeline end-to-end."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.db import Base
from src.core.models import *
from src.core.repositories import *
from src.orchestration.job_service import JobService
from tests.conftest import CSV_SCHEMA, MATCHING_KEYS_CONFIG


def _setup_file_recon(db, sample_dir: Path, source_file="source.csv", target_file="target.csv"):
    """Create all metadata objects needed for a FILE reconciliation."""
    sys_repo = SystemRepository(db)
    sys_repo.create(System(
        system_id="file_sys",
        system_name="Test Files",
        system_type="FILE",
        connection_config={"base_path": str(sample_dir), "encoding": "utf-8"},
    ))

    schema_repo = SchemaRepository(db)
    schema_repo.create(Schema(schema_id="csv_sch", schema_name="CSV", fields=CSV_SCHEMA))

    ds_repo = DatasetRepository(db)
    ds_repo.create(Dataset(dataset_id="src_ds", dataset_name="Source", system_id="file_sys", schema_id="csv_sch", physical_name=source_file, dataset_type="FILE"))
    ds_repo.create(Dataset(dataset_id="tgt_ds", dataset_name="Target", system_id="file_sys", schema_id="csv_sch", physical_name=target_file, dataset_type="FILE"))

    map_repo = MappingRepository(db)
    map_repo.create_mapping(Mapping(mapping_id="csv_map", mapping_name="M", source_schema_id="csv_sch", target_schema_id="csv_sch"))
    for fid in ["id", "name", "amount", "status"]:
        map_repo.add_field_mapping(FieldMapping(mapping_id="csv_map", target_field_id=fid, source_expression=fid))

    RuleSetRepository(db).create(RuleSet(
        rule_set_id="csv_recon",
        rule_set_name="CSV Recon",
        source_dataset_id="src_ds",
        target_dataset_id="tgt_ds",
        mapping_id="csv_map",
        matching_keys=MATCHING_KEYS_CONFIG,
    ))


@pytest.fixture
def recon_env(sample_dir):
    """Full environment: in-memory DB + sample files + metadata."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)
    with factory() as db:
        _setup_file_recon(db, sample_dir)
    return factory, sample_dir


class TestFullPipelineFILE:
    """End-to-end tests using the partitioned engine (FILE + FILE)."""

    def test_basic_reconciliation(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        assert job.status == "COMPLETED"
        assert job.error_message is None

        stats = job.summary_stats
        assert stats["total_source_records"] == 5
        assert stats["total_target_records"] == 5
        assert stats["matched_records"] == 4
        assert stats["unmatched_source_records"] == 1
        assert stats["unmatched_target_records"] == 1

    def test_discrepancies_detected(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        stats = job.summary_stats
        assert stats["matched_with_discrepancy"] > 0

        with factory() as db:
            repo = ResultRepository(db)
            discs = repo.get_discrepancies(job.run_id, {}, 100, 0)
            assert len(discs) > 0
            disc_fields = {d.field_id for d in discs}
            assert disc_fields & {"name", "amount", "status"}

    def test_matched_pairs_persisted(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        with factory() as db:
            repo = ResultRepository(db)
            pairs = repo.get_matched_record_pairs(job.run_id)
            assert len(pairs) == job.summary_stats["matched_with_discrepancy"]
            for p in pairs:
                assert p.source_record is not None
                assert p.target_record is not None
                assert p.source_metadata is not None
                assert len(p.diff_field_ids) > 0

    def test_unmatched_records_persisted(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        with factory() as db:
            repo = ResultRepository(db)
            src_unmatched = repo.get_unmatched(job.run_id, "source", 100, 0)
            tgt_unmatched = repo.get_unmatched(job.run_id, "target", 100, 0)
            assert len(src_unmatched) == job.summary_stats["unmatched_source_records"]
            assert len(tgt_unmatched) == job.summary_stats["unmatched_target_records"]
            for u in src_unmatched:
                assert u.record_key is not None
                assert u.record_data is not None

    def test_hash_optimization_skips_identical_records(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        stats = job.summary_stats
        no_disc = stats["matched_with_no_discrepancy"]
        with_disc = stats["matched_with_discrepancy"]
        assert no_disc + with_disc == stats["matched_records"]
        assert no_disc > 0

    def test_stats_math_consistent(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        stats = svc.get_job(job_id).summary_stats
        assert stats["matched_records"] + stats["unmatched_source_records"] == stats["total_source_records"]
        assert stats["matched_with_no_discrepancy"] + stats["matched_with_discrepancy"] == stats["matched_records"]


class TestSummaryOnlyMode:
    def test_no_detail_rows_persisted(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon", result_detail_level="SUMMARY_ONLY")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        assert job.status == "COMPLETED"
        assert job.result_detail_level == "SUMMARY_ONLY"
        assert job.summary_stats["matched_records"] == 4

        with factory() as db:
            repo = ResultRepository(db)
            assert len(repo.get_matched_record_pairs(job.run_id)) == 0
            assert len(repo.get_discrepancies(job.run_id, {}, 100, 0)) == 0
            assert len(repo.get_unmatched(job.run_id, "source", 100, 0)) == 0

    def test_summary_stats_still_accurate(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)

        full_id = svc.create_job("csv_recon")
        svc.execute_job(full_id)
        full_stats = svc.get_job(full_id).summary_stats

        summary_id = svc.create_job("csv_recon", result_detail_level="SUMMARY_ONLY")
        svc.execute_job(summary_id)
        summary_stats = svc.get_job(summary_id).summary_stats

        for key in ["total_source_records", "total_target_records", "matched_records",
                     "matched_with_discrepancy", "unmatched_source_records", "unmatched_target_records"]:
            assert full_stats[key] == summary_stats[key], f"{key} differs: {full_stats[key]} vs {summary_stats[key]}"


class TestTempFileCleanup:
    def test_temp_dir_cleaned_on_success(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        import glob
        temp_dirs = glob.glob(os.path.join(os.environ.get("RECON_TEMP_DIR", "/tmp"), f"recon_{job_id}"))
        assert len(temp_dirs) == 0


class TestRunRecordLifecycle:
    def test_run_created_early_and_updated(self, recon_env):
        factory, _ = recon_env
        svc = JobService(factory)
        job_id = svc.create_job("csv_recon")
        svc.execute_job(job_id)

        job = svc.get_job(job_id)
        with factory() as db:
            repo = ResultRepository(db)
            run = repo.get_run(job.run_id)
            assert run is not None
            assert run.status == "COMPLETED"
            assert run.completed_at is not None
            assert run.summary_stats is not None
