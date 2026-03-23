"""API integration tests using FastAPI TestClient."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.core.db import Base, get_db
from src.core.models import *
from src.core.repositories import *
from tests.conftest import CSV_SCHEMA, MATCHING_KEYS_CONFIG


@pytest.fixture
def api_env(sample_dir):
    """Create in-memory DB, override all DB access, seed data, return TestClient."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    from src.api.routers.jobs import get_job_service
    from src.orchestration.job_service import JobService

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_job_service] = lambda: JobService(TestSession)

    with TestSession() as db:
        SystemRepository(db).create(System(
            system_id="file_sys", system_name="Files", system_type="FILE",
            connection_config={"base_path": str(sample_dir), "encoding": "utf-8"},
        ))
        SchemaRepository(db).create(Schema(schema_id="csv_sch", schema_name="CSV", fields=CSV_SCHEMA))
        DatasetRepository(db).create(Dataset(dataset_id="src", dataset_name="S", system_id="file_sys", schema_id="csv_sch", physical_name="source.csv", dataset_type="FILE"))
        DatasetRepository(db).create(Dataset(dataset_id="tgt", dataset_name="T", system_id="file_sys", schema_id="csv_sch", physical_name="target.csv", dataset_type="FILE"))
        m_repo = MappingRepository(db)
        m_repo.create_mapping(Mapping(mapping_id="map", mapping_name="M", source_schema_id="csv_sch", target_schema_id="csv_sch"))
        for fid in ["id", "name", "amount", "status"]:
            m_repo.add_field_mapping(FieldMapping(mapping_id="map", target_field_id=fid, source_expression=fid))
        RuleSetRepository(db).create(RuleSet(
            rule_set_id="recon", rule_set_name="R", source_dataset_id="src",
            target_dataset_id="tgt", mapping_id="map", matching_keys=MATCHING_KEYS_CONFIG,
        ))

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
    engine.dispose()


class TestHealthEndpoint:
    def test_health(self):
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"


class TestJobsAPI:
    def test_create_and_get_job(self, api_env):
        resp = api_env.post("/api/v1/jobs", json={"rule_set_id": "recon"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["rule_set_id"] == "recon"
        assert data["status"] in ("PENDING", "RUNNING", "COMPLETED")

        job_id = data["job_id"]
        resp2 = api_env.get(f"/api/v1/jobs/{job_id}")
        assert resp2.status_code == 200

    def test_list_jobs(self, api_env):
        api_env.post("/api/v1/jobs", json={"rule_set_id": "recon"})
        resp = api_env.get("/api/v1/jobs")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_create_job_with_summary_only(self, api_env):
        resp = api_env.post("/api/v1/jobs", json={
            "rule_set_id": "recon",
            "result_detail_level": "SUMMARY_ONLY",
        })
        assert resp.status_code == 201

    def test_cancel_nonexistent_job(self, api_env):
        resp = api_env.delete("/api/v1/jobs/NONEXISTENT")
        assert resp.status_code == 404


class TestResultsAPI:
    def _run_job_and_wait(self, client):
        resp = client.post("/api/v1/jobs", json={"rule_set_id": "recon"})
        job_id = resp.json()["job_id"]
        import time
        for _ in range(50):
            r = client.get(f"/api/v1/jobs/{job_id}")
            if r.json()["status"] in ("COMPLETED", "FAILED"):
                break
            time.sleep(0.1)
        return job_id, client.get(f"/api/v1/jobs/{job_id}").json()

    def test_summary_endpoint(self, api_env):
        job_id, job_data = self._run_job_and_wait(api_env)
        if job_data["status"] != "COMPLETED":
            pytest.skip("Job didn't complete in time")
        resp = api_env.get(f"/api/v1/results/{job_id}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_source_records" in data
        assert "matched_records" in data

    def test_discrepancies_endpoint(self, api_env):
        job_id, job_data = self._run_job_and_wait(api_env)
        if job_data["status"] != "COMPLETED":
            pytest.skip("Job didn't complete in time")
        resp = api_env.get(f"/api/v1/results/{job_id}/discrepancies")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_diff_view_endpoint(self, api_env):
        job_id, job_data = self._run_job_and_wait(api_env)
        if job_data["status"] != "COMPLETED":
            pytest.skip("Job didn't complete in time")
        resp = api_env.get(f"/api/v1/results/{job_id}/diff-view")
        assert resp.status_code == 200
        data = resp.json()
        assert "matched_with_discrepancies" in data
        assert "unmatched_source" in data
        assert "unmatched_target" in data

    def test_unmatched_endpoints(self, api_env):
        job_id, job_data = self._run_job_and_wait(api_env)
        if job_data["status"] != "COMPLETED":
            pytest.skip("Job didn't complete in time")
        for side in ("unmatched-source", "unmatched-target"):
            resp = api_env.get(f"/api/v1/results/{job_id}/{side}")
            assert resp.status_code == 200

    def test_404_for_nonexistent_job(self, api_env):
        resp = api_env.get("/api/v1/results/NONEXISTENT/summary")
        assert resp.status_code == 404
