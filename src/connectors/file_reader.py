"""File dataset reader for JSON and CSV."""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BatchResult, CanonicalRow, DatasetReader
from .exceptions import ConnectionError

logger = logging.getLogger(__name__)


def _get_dict_key(d: Dict[str, Any], key: str, case_insensitive: bool = False) -> Optional[Any]:
    """Get value from dict by key, with optional case-insensitive lookup."""
    if key in d:
        return d[key]
    if case_insensitive:
        key_lower = key.lower()
        for k, v in d.items():
            if k.lower() == key_lower:
                return v
    return None


def _extract_nested(obj: Any, path: str, case_insensitive_keys: bool = False) -> Any:
    """Extract value from dict using dot-notation path. Keys matched by name; optionally case-insensitive."""
    keys = path.split(".")
    for key in keys:
        if obj is None:
            return None
        if isinstance(obj, dict):
            obj = _get_dict_key(obj, key, case_insensitive_keys)
        elif isinstance(obj, list) and key.isdigit():
            idx = int(key)
            obj = obj[idx] if idx < len(obj) else None
        else:
            return None
    return obj


class FileDatasetReader(DatasetReader):
    """Read JSON and CSV files from local filesystem."""

    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self._base_path: Optional[Path] = None
        self._rows_cache: Optional[List[Dict[str, Any]]] = None

    def connect(self) -> bool:
        base_path = self.system_config.get("base_path", "")
        if not base_path:
            raise ConnectionError("FILE system requires 'base_path' in connection_config")
        resolved = Path(base_path).expanduser().resolve()
        if not resolved.exists():
            raise ConnectionError(f"Base path does not exist: {resolved}")
        if not resolved.is_dir():
            raise ConnectionError(f"Base path must be a directory: {resolved}")
        self._base_path = resolved
        logger.info("File connector ready: %s", self._base_path)
        return True

    def disconnect(self) -> None:
        self._base_path = None
        self._rows_cache = None
        logger.info("File connector disconnected")

    def _resolve_path(self, physical_name: str) -> Path:
        if not self._base_path:
            raise ConnectionError("Not connected")
        full = (self._base_path / physical_name).resolve()
        if not full.is_relative_to(self._base_path):
            raise ConnectionError("Path outside base_path not allowed")
        return full

    def _load_rows(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        physical_name = dataset["physical_name"]
        path = self._resolve_path(physical_name)
        if not path.exists():
            raise ConnectionError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".json":
            return self._load_json(path)
        if suffix == ".csv":
            return self._load_csv(path, dataset)
        raise ConnectionError(f"Unsupported file format: {suffix}")

    def _load_json(self, path: Path) -> List[Dict[str, Any]]:
        encoding = self.system_config.get("encoding", "utf-8")
        with open(path, encoding=encoding) as f:
            data = json.load(f)
        if isinstance(data, list):
            return [r if isinstance(r, dict) else {"_value": r} for r in data]
        if isinstance(data, dict):
            array_key = self.system_config.get("array_key")
            if array_key and array_key in data:
                arr = data[array_key]
                return [r if isinstance(r, dict) else {"_value": r} for r in arr]
            return [data]
        return [{"_value": data}]

    def _load_csv(self, path: Path, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        encoding = self.system_config.get("encoding", "utf-8")
        filter_config = dataset.get("filter_config", {})
        delimiter = filter_config.get("delimiter") or self.system_config.get("delimiter", ",")
        has_header = filter_config.get("has_header", True)

        with open(path, encoding=encoding, newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            rows = list(reader)
        if not rows:
            return []
        if has_header:
            headers = rows[0]
            return [dict(zip(headers, row)) for row in rows[1:]]
        return [{"_col_" + str(i): v for i, v in enumerate(row)} for row in rows]

    def _row_to_canonical(
        self, row: Dict[str, Any], row_num: int, filter_config: Optional[Dict[str, Any]] = None
    ) -> CanonicalRow:
        filter_config = filter_config or {}
        case_insensitive = filter_config.get("case_insensitive_lookup", False)
        schema_fields = self.schema.get("fields", [])
        fields: Dict[str, Any] = {}
        for field_def in schema_fields:
            field_id = field_def.get("field_id")
            pm = field_def.get("physical_mapping", {})
            json_path = pm.get("json_path")
            csv_column = pm.get("csv_column")
            if json_path is not None:
                value = _extract_nested(row, json_path, case_insensitive_keys=case_insensitive)
            elif csv_column is not None:
                value = _get_dict_key(row, csv_column, case_insensitive)
            else:
                value = _get_dict_key(row, field_id, case_insensitive) or _get_dict_key(
                    row, field_def.get("field_name", field_id), case_insensitive
                )
            fields[field_id] = value
        return CanonicalRow(
            fields=fields,
            metadata={
                "source": "file",
                "row_number": row_num,
                "fetched_at": datetime.utcnow().isoformat(),
            },
        )

    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        start = datetime.utcnow()
        if self._rows_cache is None:
            self._rows_cache = self._load_rows(dataset)
        rows = self._rows_cache
        offset = (cursor or {}).get("offset", 0)
        chunk = rows[offset : offset + batch_size]
        filter_config = dataset.get("filter_config", {})
        canonical = [
            self._row_to_canonical(r, offset + i, filter_config) for i, r in enumerate(chunk)
        ]
        has_more = len(chunk) == batch_size and offset + batch_size < len(rows)
        next_cursor = {"offset": offset + len(chunk)} if has_more else None
        return BatchResult(
            rows=canonical,
            cursor=next_cursor,
            has_more=has_more,
            batch_metadata={
                "source": "file",
                "rows_fetched": len(chunk),
                "offset": offset,
                "duration_ms": (datetime.utcnow() - start).total_seconds() * 1000,
            },
        )

    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        if self._rows_cache is None:
            self._rows_cache = self._load_rows(dataset)
        return len(self._rows_cache)

    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        result = {"valid": True, "errors": [], "warnings": []}
        try:
            rows = self._load_rows(dataset)
        except Exception as e:
            result["valid"] = False
            result["errors"].append(str(e))
            return result
        if not rows:
            result["warnings"].append("File is empty")
            return result
        sample = rows[0]
        filter_config = dataset.get("filter_config", {})
        case_insensitive = filter_config.get("case_insensitive_lookup", False)
        schema_fields = self.schema.get("fields", [])
        for field_def in schema_fields:
            field_id = field_def.get("field_id")
            pm = field_def.get("physical_mapping", {})
            json_path = pm.get("json_path")
            csv_column = pm.get("csv_column")
            if json_path is not None:
                val = _extract_nested(sample, json_path, case_insensitive_keys=case_insensitive)
                if val is None and not field_def.get("is_nullable", True):
                    result["warnings"].append(f"Path {json_path} not found in sample")
            elif csv_column is not None:
                col_found = csv_column in sample or (
                    case_insensitive and any(k.lower() == csv_column.lower() for k in sample)
                )
                if not col_found:
                    result["valid"] = False
                    result["errors"].append(f"Column {csv_column} not found in file")
        return result
