"""File dataset reader for JSON and CSV -- streaming implementation."""

from __future__ import annotations

import csv
import io
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
    """Extract value from dict using dot-notation path."""
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
    """Streaming reader for JSON and CSV files.

    CSV files are read incrementally using byte-offset cursors -- only one
    batch of rows is held in memory at a time.  JSON files are loaded in full
    (streaming JSON arrays is uncommon at scale; CSV is the expected format
    for large KYC datasets).
    """

    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self._base_path: Optional[Path] = None
        self._csv_file: Optional[io.TextIOWrapper] = None
        self._csv_headers: Optional[List[str]] = None
        self._csv_header_end_offset: int = 0
        self._json_cache: Optional[List[Dict[str, Any]]] = None
        self._current_dataset: Optional[Dict[str, Any]] = None

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
        if self._csv_file and not self._csv_file.closed:
            self._csv_file.close()
        self._csv_file = None
        self._csv_headers = None
        self._csv_header_end_offset = 0
        self._json_cache = None
        self._current_dataset = None
        self._base_path = None
        logger.info("File connector disconnected")

    def _resolve_path(self, physical_name: str) -> Path:
        if not self._base_path:
            raise ConnectionError("Not connected")
        full = (self._base_path / physical_name).resolve()
        if not full.is_relative_to(self._base_path):
            raise ConnectionError("Path outside base_path not allowed")
        return full

    # ------------------------------------------------------------------
    # CSV streaming helpers
    # ------------------------------------------------------------------

    def _open_csv(self, dataset: Dict[str, Any]) -> None:
        """Open a CSV file and read the header row, storing the byte offset
        where data rows begin."""
        path = self._resolve_path(dataset["physical_name"])
        if not path.exists():
            raise ConnectionError(f"File not found: {path}")
        encoding = self.system_config.get("encoding", "utf-8")
        filter_config = dataset.get("filter_config", {})
        has_header = filter_config.get("has_header", True)

        f = open(path, encoding=encoding, newline="")
        try:
            if has_header:
                first_line = f.readline()
                if first_line.strip():
                    delimiter = filter_config.get("delimiter") or self.system_config.get("delimiter", ",")
                    parsed = next(csv.reader(io.StringIO(first_line), delimiter=delimiter), None)
                    self._csv_headers = parsed if parsed else []
                else:
                    self._csv_headers = []
                self._csv_header_end_offset = f.tell()
            else:
                self._csv_headers = None
                self._csv_header_end_offset = 0
        except Exception:
            f.close()
            raise

        self._csv_file = f
        self._current_dataset = dataset

    def _ensure_csv_open(self, dataset: Dict[str, Any]) -> None:
        """Ensure the CSV file is open for the correct dataset."""
        current_name = (self._current_dataset or {}).get("physical_name")
        requested_name = dataset["physical_name"]
        if self._csv_file is None or self._csv_file.closed or current_name != requested_name:
            if self._csv_file and not self._csv_file.closed:
                self._csv_file.close()
            self._open_csv(dataset)

    def _read_csv_batch(
        self, byte_offset: int, batch_size: int, dataset: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], int, bool, int]:
        """Read *batch_size* CSV rows starting from *byte_offset*.

        Returns (rows, next_byte_offset, has_more, row_count_read).

        We read raw lines and parse with csv.reader on a StringIO buffer
        because Python disables file.tell() inside a csv.reader iteration.
        """
        self._ensure_csv_open(dataset)
        assert self._csv_file is not None
        self._csv_file.seek(byte_offset)

        filter_config = dataset.get("filter_config", {})
        delimiter = filter_config.get("delimiter") or self.system_config.get("delimiter", ",")

        rows: List[Dict[str, Any]] = []
        count = 0
        while count < batch_size:
            line = self._csv_file.readline()
            if not line:
                break
            parsed = next(csv.reader(io.StringIO(line), delimiter=delimiter), None)
            if parsed is None or not any(parsed):
                continue
            if self._csv_headers:
                rows.append(dict(zip(self._csv_headers, parsed)))
            else:
                rows.append({"_col_" + str(i): v for i, v in enumerate(parsed)})
            count += 1

        next_offset = self._csv_file.tell()
        has_more = count == batch_size
        return rows, next_offset, has_more, count

    # ------------------------------------------------------------------
    # JSON helpers (non-streaming, kept for small / reference files)
    # ------------------------------------------------------------------

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

    def _ensure_json_loaded(self, dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self._json_cache is None:
            path = self._resolve_path(dataset["physical_name"])
            if not path.exists():
                raise ConnectionError(f"File not found: {path}")
            self._json_cache = self._load_json(path)
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > 500:
                logger.warning(
                    "JSON file %.1f MB loaded fully into memory. "
                    "For large datasets, use CSV format for streaming support.",
                    size_mb,
                )
        return self._json_cache

    # ------------------------------------------------------------------
    # Canonical row conversion
    # ------------------------------------------------------------------

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
                value = _get_dict_key(row, field_id, case_insensitive)
                if value is None:
                    value = _get_dict_key(row, field_def.get("field_name", field_id), case_insensitive)
            fields[field_id] = value
        return CanonicalRow(
            fields=fields,
            metadata={
                "source": "file",
                "row_number": row_num,
                "fetched_at": datetime.utcnow().isoformat(),
            },
        )

    # ------------------------------------------------------------------
    # DatasetReader interface
    # ------------------------------------------------------------------

    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        start = datetime.utcnow()
        physical_name = dataset["physical_name"]
        path = self._resolve_path(physical_name)
        suffix = path.suffix.lower()
        filter_config = dataset.get("filter_config", {})

        if suffix == ".csv":
            self._ensure_csv_open(dataset)
            byte_offset = (cursor or {}).get("byte_offset", self._csv_header_end_offset)
            row_count_so_far = (cursor or {}).get("row_count", 0)

            if byte_offset == 0:
                byte_offset = self._csv_header_end_offset

            raw_rows, next_offset, has_more, count = self._read_csv_batch(
                byte_offset, batch_size, dataset
            )
            canonical = [
                self._row_to_canonical(r, row_count_so_far + i, filter_config)
                for i, r in enumerate(raw_rows)
            ]
            next_cursor = {
                "byte_offset": next_offset,
                "row_count": row_count_so_far + count,
            } if has_more else None

        elif suffix == ".json":
            all_rows = self._ensure_json_loaded(dataset)
            offset = (cursor or {}).get("offset", 0)
            chunk = all_rows[offset: offset + batch_size]
            canonical = [
                self._row_to_canonical(r, offset + i, filter_config)
                for i, r in enumerate(chunk)
            ]
            has_more = len(chunk) == batch_size and offset + batch_size < len(all_rows)
            next_cursor = {"offset": offset + len(chunk)} if has_more else None
            count = len(chunk)
        else:
            raise ConnectionError(f"Unsupported file format: {suffix}")

        return BatchResult(
            rows=canonical,
            cursor=next_cursor,
            has_more=has_more,
            batch_metadata={
                "source": "file",
                "rows_fetched": count,
                "duration_ms": (datetime.utcnow() - start).total_seconds() * 1000,
            },
        )

    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        path = self._resolve_path(dataset["physical_name"])
        suffix = path.suffix.lower()
        if suffix == ".csv":
            encoding = self.system_config.get("encoding", "utf-8")
            filter_config = dataset.get("filter_config", {})
            has_header = filter_config.get("has_header", True)
            delimiter = filter_config.get("delimiter") or self.system_config.get("delimiter", ",")
            with open(path, encoding=encoding, newline="") as f:
                reader = csv.reader(f, delimiter=delimiter)
                if has_header:
                    next(reader, None)
                return sum(1 for row in reader if row)
        all_rows = self._ensure_json_loaded(dataset)
        return len(all_rows)

    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        result = {"valid": True, "errors": [], "warnings": []}
        path = self._resolve_path(dataset["physical_name"])
        suffix = path.suffix.lower()
        filter_config = dataset.get("filter_config", {})
        case_insensitive = filter_config.get("case_insensitive_lookup", False)

        try:
            if suffix == ".csv":
                encoding = self.system_config.get("encoding", "utf-8")
                delimiter = filter_config.get("delimiter") or self.system_config.get("delimiter", ",")
                has_header = filter_config.get("has_header", True)
                with open(path, encoding=encoding, newline="") as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    first_row = next(reader, None)
                    if first_row is None:
                        result["warnings"].append("File is empty")
                        return result
                    if has_header:
                        headers = first_row
                        data_row = next(reader, None)
                        sample = dict(zip(headers, data_row)) if data_row else dict(zip(headers, [""] * len(headers)))
                    else:
                        sample = {"_col_" + str(i): v for i, v in enumerate(first_row)}
            elif suffix == ".json":
                rows = self._load_json(path)
                if not rows:
                    result["warnings"].append("File is empty")
                    return result
                sample = rows[0]
            else:
                result["valid"] = False
                result["errors"].append(f"Unsupported file format: {suffix}")
                return result
        except Exception as e:
            result["valid"] = False
            result["errors"].append(str(e))
            return result

        schema_fields = self.schema.get("fields", [])
        for field_def in schema_fields:
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
