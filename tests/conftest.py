"""Shared test fixtures for the GenRecon test suite."""

from __future__ import annotations

import csv
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite:///")
os.environ.setdefault("RECON_ENCRYPTION_KEY", "dGVzdC1rZXktZm9yLXRlc3RzLW9ubHktMzJieXQ=")

from src.core.db import Base
from src.core.models import *
from src.core.repositories import *
from src.connectors.base import CanonicalRow


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_engine():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine)


# ---------------------------------------------------------------------------
# Temp directory with sample CSV / JSON files
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_dir():
    """Create a temp directory with sample source/target CSV and JSON files."""
    d = tempfile.mkdtemp(prefix="genrecon_test_")
    path = Path(d)

    source_csv = [
        ["id", "name", "amount", "status"],
        ["1", "Alice", "100.00", "active"],
        ["2", "Bob", "250.75", "active"],
        ["3", "Carol", "300.00", "active"],
        ["4", "Dave", "400.00", "active"],
        ["5", "Eve", "500.00", "active"],
    ]
    target_csv = [
        ["id", "name", "amount", "status"],
        ["1", "Alice", "100.00", "active"],
        ["2", "Bob", "250.80", "active"],
        ["3", "Carol Smith", "300.00", "active"],
        ["5", "Eve", "500.00", "inactive"],
        ["6", "Frank", "600.00", "active"],
    ]

    with open(path / "source.csv", "w", newline="") as f:
        csv.writer(f).writerows(source_csv)
    with open(path / "target.csv", "w", newline="") as f:
        csv.writer(f).writerows(target_csv)

    source_json = [
        {"id": "1", "name": "Alice", "amount": 100},
        {"id": "2", "name": "Bob", "amount": 250.75},
        {"id": "3", "name": "Carol", "amount": 300},
    ]
    target_json = [
        {"id": "1", "name": "Alice", "amount": 100},
        {"id": "2", "name": "Bob", "amount": 250.80},
        {"id": "4", "name": "Dave", "amount": 400},
    ]
    with open(path / "source.json", "w") as f:
        json.dump(source_json, f)
    with open(path / "target.json", "w") as f:
        json.dump(target_json, f)

    # CSV with falsy values (0, empty string)
    falsy_csv = [
        ["id", "value", "flag"],
        ["1", "0", ""],
        ["2", "hello", "true"],
    ]
    with open(path / "falsy.csv", "w", newline="") as f:
        csv.writer(f).writerows(falsy_csv)

    # CSV with quoted fields containing newlines
    with open(path / "quoted.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "description"])
        w.writerow(["1", "line1\nline2"])
        w.writerow(["2", "simple"])

    # Empty CSV
    with open(path / "empty.csv", "w") as f:
        pass

    # Header-only CSV
    with open(path / "header_only.csv", "w", newline="") as f:
        csv.writer(f).writerow(["id", "name"])

    yield path
    shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Common schema definitions
# ---------------------------------------------------------------------------

CSV_SCHEMA = {
    "fields": [
        {"field_id": "id", "field_name": "id", "data_type": "STRING", "is_key": True, "physical_mapping": {"csv_column": "id"}},
        {"field_id": "name", "field_name": "name", "data_type": "STRING", "is_key": False, "physical_mapping": {"csv_column": "name"}},
        {"field_id": "amount", "field_name": "amount", "data_type": "STRING", "is_key": False, "physical_mapping": {"csv_column": "amount"}},
        {"field_id": "status", "field_name": "status", "data_type": "STRING", "is_key": False, "physical_mapping": {"csv_column": "status"}},
    ]
}

JSON_SCHEMA = {
    "fields": [
        {"field_id": "id", "field_name": "id", "data_type": "STRING", "is_key": True, "physical_mapping": {"json_path": "id"}},
        {"field_id": "name", "field_name": "name", "data_type": "STRING", "is_key": False, "physical_mapping": {"json_path": "name"}},
        {"field_id": "amount", "field_name": "amount", "data_type": "STRING", "is_key": False, "physical_mapping": {"json_path": "amount"}},
    ]
}

MATCHING_KEYS_CONFIG = {
    "keys": [{"source_field": "id", "target_field": "id", "is_case_sensitive": True}]
}


def make_canonical_row(fields: Dict[str, Any], **meta_overrides) -> CanonicalRow:
    meta = {"source": "test", "row_number": 0, "fetched_at": "2025-01-01T00:00:00"}
    meta.update(meta_overrides)
    return CanonicalRow(fields=fields, metadata=meta)
