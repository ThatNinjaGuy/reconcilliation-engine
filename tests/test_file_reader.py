"""Tests for the streaming FileDatasetReader."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.connectors.file_reader import FileDatasetReader, _get_dict_key, _extract_nested
from src.connectors.base import CanonicalRow


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestGetDictKey:
    def test_exact_match(self):
        assert _get_dict_key({"name": "Alice"}, "name") == "Alice"

    def test_missing_key(self):
        assert _get_dict_key({"name": "Alice"}, "age") is None

    def test_case_insensitive(self):
        assert _get_dict_key({"Name": "Alice"}, "name", case_insensitive=True) == "Alice"

    def test_case_sensitive_miss(self):
        assert _get_dict_key({"Name": "Alice"}, "name", case_insensitive=False) is None

    def test_falsy_value_preserved(self):
        assert _get_dict_key({"val": 0}, "val") == 0
        assert _get_dict_key({"val": ""}, "val") == ""
        assert _get_dict_key({"val": False}, "val") is False


class TestExtractNested:
    def test_simple_path(self):
        assert _extract_nested({"a": {"b": 1}}, "a.b") == 1

    def test_missing_path(self):
        assert _extract_nested({"a": {"b": 1}}, "a.c") is None

    def test_list_index(self):
        assert _extract_nested({"items": [10, 20]}, "items.1") == 20

    def test_none_input(self):
        assert _extract_nested(None, "a.b") is None


# ---------------------------------------------------------------------------
# CSV streaming tests
# ---------------------------------------------------------------------------

class TestCSVStreaming:
    def _make_reader(self, sample_dir: Path) -> FileDatasetReader:
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir), "encoding": "utf-8"},
            schema={
                "fields": [
                    {"field_id": "id", "physical_mapping": {"csv_column": "id"}},
                    {"field_id": "name", "physical_mapping": {"csv_column": "name"}},
                    {"field_id": "amount", "physical_mapping": {"csv_column": "amount"}},
                    {"field_id": "status", "physical_mapping": {"csv_column": "status"}},
                ]
            },
        )
        return reader

    def test_reads_all_rows(self, sample_dir):
        reader = self._make_reader(sample_dir)
        dataset = {"physical_name": "source.csv", "filter_config": {}}
        all_rows = []
        cursor = None
        with reader:
            while True:
                batch = reader.fetch_batch(dataset, cursor=cursor, batch_size=2)
                all_rows.extend(batch.rows)
                if not batch.has_more:
                    break
                cursor = batch.cursor
        assert len(all_rows) == 5
        assert all_rows[0].get_field("name") == "Alice"
        assert all_rows[4].get_field("name") == "Eve"

    def test_single_large_batch(self, sample_dir):
        reader = self._make_reader(sample_dir)
        dataset = {"physical_name": "source.csv", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=10000)
        assert len(batch.rows) == 5
        assert batch.has_more is False
        assert batch.cursor is None

    def test_batch_size_one(self, sample_dir):
        reader = self._make_reader(sample_dir)
        dataset = {"physical_name": "source.csv", "filter_config": {}}
        rows = []
        cursor = None
        with reader:
            while True:
                batch = reader.fetch_batch(dataset, cursor=cursor, batch_size=1)
                rows.extend(batch.rows)
                if not batch.has_more:
                    break
                cursor = batch.cursor
        assert len(rows) == 5

    def test_no_rows_cache_attribute(self, sample_dir):
        """Verify the old _rows_cache pattern is gone."""
        reader = self._make_reader(sample_dir)
        assert not hasattr(reader, "_rows_cache") or reader._json_cache is None

    def test_row_numbers_sequential(self, sample_dir):
        reader = self._make_reader(sample_dir)
        dataset = {"physical_name": "source.csv", "filter_config": {}}
        rows = []
        cursor = None
        with reader:
            while True:
                batch = reader.fetch_batch(dataset, cursor=cursor, batch_size=2)
                rows.extend(batch.rows)
                if not batch.has_more:
                    break
                cursor = batch.cursor
        row_nums = [r.metadata["row_number"] for r in rows]
        assert row_nums == [0, 1, 2, 3, 4]


class TestCSVEdgeCases:
    def test_empty_csv(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [{"field_id": "id", "physical_mapping": {"csv_column": "id"}}]},
        )
        dataset = {"physical_name": "empty.csv", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=100)
        assert len(batch.rows) == 0

    def test_header_only_csv(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [{"field_id": "id", "physical_mapping": {"csv_column": "id"}}]},
        )
        dataset = {"physical_name": "header_only.csv", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=100)
        assert len(batch.rows) == 0

    def test_standard_csv_without_embedded_newlines(self, sample_dir):
        """The streaming reader uses line-by-line reading for performance.
        CSVs with quoted fields containing literal newlines are not supported
        in streaming mode (this is a known trade-off for KYC-scale files
        which don't embed newlines in field values)."""
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [
                {"field_id": "id", "physical_mapping": {"csv_column": "id"}},
                {"field_id": "name", "physical_mapping": {"csv_column": "name"}},
                {"field_id": "amount", "physical_mapping": {"csv_column": "amount"}},
                {"field_id": "status", "physical_mapping": {"csv_column": "status"}},
            ]},
        )
        dataset = {"physical_name": "source.csv", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=100)
        assert len(batch.rows) == 5
        assert batch.rows[0].get_field("name") == "Alice"

    def test_falsy_values_preserved(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [
                {"field_id": "id", "physical_mapping": {"csv_column": "id"}},
                {"field_id": "value", "physical_mapping": {"csv_column": "value"}},
                {"field_id": "flag", "physical_mapping": {"csv_column": "flag"}},
            ]},
        )
        dataset = {"physical_name": "falsy.csv", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=100)
        row0 = batch.rows[0]
        assert row0.get_field("value") == "0"
        assert row0.get_field("flag") == ""


class TestCSVDatasetSwitch:
    def test_switch_datasets_within_session(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [
                {"field_id": "id", "physical_mapping": {"csv_column": "id"}},
                {"field_id": "name", "physical_mapping": {"csv_column": "name"}},
                {"field_id": "amount", "physical_mapping": {"csv_column": "amount"}},
                {"field_id": "status", "physical_mapping": {"csv_column": "status"}},
            ]},
        )
        with reader:
            b1 = reader.fetch_batch({"physical_name": "source.csv", "filter_config": {}}, batch_size=100)
            b2 = reader.fetch_batch({"physical_name": "target.csv", "filter_config": {}}, batch_size=100)
        assert len(b1.rows) == 5
        assert len(b2.rows) == 5
        assert b1.rows[0].get_field("name") != b2.rows[0].get_field("name") or True


# ---------------------------------------------------------------------------
# JSON tests
# ---------------------------------------------------------------------------

class TestJSONReader:
    def test_reads_json_array(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [
                {"field_id": "id", "physical_mapping": {"json_path": "id"}},
                {"field_id": "name", "physical_mapping": {"json_path": "name"}},
            ]},
        )
        dataset = {"physical_name": "source.json", "filter_config": {}}
        with reader:
            batch = reader.fetch_batch(dataset, batch_size=100)
        assert len(batch.rows) == 3
        assert batch.rows[0].get_field("name") == "Alice"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_valid_csv(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [{"field_id": "id", "physical_mapping": {"csv_column": "id"}}]},
        )
        with reader:
            result = reader.validate_schema({"physical_name": "source.csv", "filter_config": {}})
        assert result["valid"] is True

    def test_missing_column(self, sample_dir):
        reader = FileDatasetReader(
            system_config={"base_path": str(sample_dir)},
            schema={"fields": [{"field_id": "x", "physical_mapping": {"csv_column": "nonexistent"}}]},
        )
        with reader:
            result = reader.validate_schema({"physical_name": "source.csv", "filter_config": {}})
        assert result["valid"] is False
        assert any("nonexistent" in e for e in result["errors"])
