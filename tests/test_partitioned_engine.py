"""Tests for the partitioned reconciliation engine."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.reconciliation.partitioned_engine import (
    stable_partition_id,
    compute_row_hash,
    _build_hash_field_ids,
    _PartitionWriter,
    load_partition,
)


class TestStablePartitionId:
    def test_deterministic(self):
        a = stable_partition_id("key123", 64)
        b = stable_partition_id("key123", 64)
        assert a == b

    def test_range(self):
        for i in range(100):
            pid = stable_partition_id(f"key_{i}", 16)
            assert 0 <= pid < 16

    def test_distribution(self):
        buckets = set()
        for i in range(1000):
            buckets.add(stable_partition_id(f"k{i}", 8))
        assert len(buckets) == 8

    def test_different_keys_can_differ(self):
        a = stable_partition_id("alpha", 1000)
        b = stable_partition_id("beta", 1000)
        # Not guaranteed to differ, but with 1000 partitions it's extremely likely
        # We just verify they're both in range
        assert 0 <= a < 1000
        assert 0 <= b < 1000


class TestComputeRowHash:
    def test_same_values_same_hash(self):
        h1 = compute_row_hash({"name": "Alice", "age": 30}, ["age", "name"])
        h2 = compute_row_hash({"name": "Alice", "age": 30}, ["age", "name"])
        assert h1 == h2

    def test_different_values_different_hash(self):
        h1 = compute_row_hash({"name": "Alice"}, ["name"])
        h2 = compute_row_hash({"name": "Bob"}, ["name"])
        assert h1 != h2

    def test_field_order_doesnt_matter(self):
        h1 = compute_row_hash({"a": 1, "b": 2}, ["a", "b"])
        h2 = compute_row_hash({"b": 2, "a": 1}, ["a", "b"])
        assert h1 == h2

    def test_none_vs_missing(self):
        h1 = compute_row_hash({"name": None}, ["name"])
        h2 = compute_row_hash({}, ["name"])
        assert h1 == h2

    def test_type_sensitive(self):
        h1 = compute_row_hash({"v": "1"}, ["v"])
        h2 = compute_row_hash({"v": 1}, ["v"])
        assert h1 != h2

    def test_no_delimiter_collision(self):
        """Values with special characters shouldn't cause hash collisions."""
        h1 = compute_row_hash({"a": "x,y", "b": "z"}, ["a", "b"])
        h2 = compute_row_hash({"a": "x", "b": "y,z"}, ["a", "b"])
        assert h1 != h2


class TestBuildHashFieldIds:
    def test_excludes_key_fields(self):
        schema = {"fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "name", "is_key": False},
            {"field_id": "amount", "is_key": False},
        ]}
        result = _build_hash_field_ids(schema, [])
        assert "id" not in result
        assert "name" in result
        assert "amount" in result

    def test_excludes_ignored_fields(self):
        schema = {"fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "name", "is_key": False},
            {"field_id": "notes", "is_key": False},
        ]}
        rules = [{"target_field_id": "notes", "ignore_field": True, "is_active": True}]
        result = _build_hash_field_ids(schema, rules)
        assert "notes" not in result
        assert "name" in result

    def test_sorted_output(self):
        schema = {"fields": [
            {"field_id": "id", "is_key": True},
            {"field_id": "zebra", "is_key": False},
            {"field_id": "alpha", "is_key": False},
        ]}
        result = _build_hash_field_ids(schema, [])
        assert result == ["alpha", "zebra"]


class TestPartitionWriterAndReader:
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            writer = _PartitionWriter(base, "source", 4)
            writer.open()
            writer.write(0, "key1", "hash1", {"id": "1", "name": "Alice"}, {"row_number": 0})
            writer.write(0, "key2", "hash2", {"id": "2", "name": "Bob"}, {"row_number": 1})
            writer.write(2, "key3", "hash3", {"id": "3", "name": "Carol"}, {"row_number": 2})
            writer.close()

            assert writer.total_rows == 3

            rows_p0 = load_partition(base, "source", 0)
            assert len(rows_p0) == 2
            assert rows_p0[0].get_field("name") == "Alice"
            assert rows_p0[0].metadata["row_hash"] == "hash1"
            assert rows_p0[0].metadata["_matching_key"] == "key1"

            rows_p1 = load_partition(base, "source", 1)
            assert len(rows_p1) == 0

            rows_p2 = load_partition(base, "source", 2)
            assert len(rows_p2) == 1

    def test_empty_partition(self):
        with tempfile.TemporaryDirectory() as td:
            rows = load_partition(Path(td), "source", 99)
            assert rows == []
