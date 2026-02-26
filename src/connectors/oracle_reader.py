"""Oracle dataset reader implementation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import logging

from sqlalchemy import create_engine, text

try:
    import oracledb as cx_Oracle
except Exception:  # pragma: no cover - import guard
    cx_Oracle = None

from .base import BatchResult, CanonicalRow, DatasetReader
from .exceptions import ConnectionError, QueryError

logger = logging.getLogger(__name__)


class OracleDatasetReader(DatasetReader):
    """Oracle connector using SQLAlchemy and oracledb."""

    ORACLE_TYPE_MAP = {
        "VARCHAR2": str,
        "CHAR": str,
        "NVARCHAR2": str,
        "NUMBER": Decimal,
        "INTEGER": int,
        "FLOAT": float,
        "DATE": datetime,
        "TIMESTAMP": datetime,
        "CLOB": str,
        "BLOB": bytes,
    }

    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self.engine = None

    def connect(self) -> bool:
        if cx_Oracle is None:
            raise ConnectionError("oracledb driver is not available")
        try:
            host = self.system_config["host"]
            port = self.system_config["port"]
            service_name = self.system_config.get("service_name")
            sid = self.system_config.get("sid")
            username = self.system_config["username"]
            password = self.system_config["password"]

            if service_name:
                dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
            else:
                dsn = cx_Oracle.makedsn(host, port, sid=sid)

            connection_string = f"oracle+oracledb://{username}:{password}@{dsn}"
            pool_size = self.system_config.get("pool_size", 10)
            max_overflow = self.system_config.get("pool_max_overflow", 20)

            self.engine = create_engine(
                connection_string,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                future=True,
            )

            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1 FROM DUAL")).fetchone()

            logger.info("Oracle connection established")
            return True
        except Exception as exc:
            logger.exception("Oracle connection failed")
            raise ConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        if self.engine:
            self.engine.dispose()
            logger.info("Oracle connection closed")

    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        start_time = datetime.utcnow()
        table_name = dataset["physical_name"]
        filter_config = dataset.get("filter_config", {})
        offset = cursor["offset"] if cursor else 0

        query = self._build_select_query(
            table_name=table_name,
            schema=self.schema,
            offset=offset,
            batch_size=batch_size,
            base_filters=filter_config,
            runtime_filters=filters,
        )

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                column_names = result.keys()
        except Exception as exc:
            raise QueryError(str(exc)) from exc

        canonical_rows: List[CanonicalRow] = []
        for idx, row in enumerate(rows):
            canonical_rows.append(
                self._convert_to_canonical(
                    row=row,
                    column_names=list(column_names),
                    row_number=offset + idx,
                )
            )

        has_more = len(rows) == batch_size
        next_cursor = {"offset": offset + len(rows)} if has_more else None

        batch_metadata = {
            "source": "oracle",
            "table": table_name,
            "rows_fetched": len(rows),
            "offset": offset,
            "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
        }

        return BatchResult(
            rows=canonical_rows,
            cursor=next_cursor,
            has_more=has_more,
            batch_metadata=batch_metadata,
        )

    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        table_name = dataset["physical_name"]
        filter_config = dataset.get("filter_config", {})
        where_clauses = []
        if filter_config and filter_config.get("where_clause"):
            where_clauses.append(filter_config["where_clause"])
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT COUNT(*) FROM {table_name} {where_clause}"
        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return int(result.fetchone()[0])

    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        table_name = dataset["physical_name"]
        schema_fields = self.schema["fields"]
        validation_result = {"valid": True, "errors": [], "warnings": []}

        query = """
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = UPPER(:table_name)
        """
        with self.engine.connect() as conn:
            result = conn.execute(text(query), {"table_name": table_name})
            oracle_columns = {row[0]: row for row in result.fetchall()}

        for field in schema_fields:
            oracle_column = field["physical_mapping"].get("oracle_column")
            if not oracle_column:
                continue
            if oracle_column.upper() not in oracle_columns:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Column {oracle_column} not found in table {table_name}"
                )
        return validation_result

    def _build_select_query(
        self,
        table_name: str,
        schema: Dict[str, Any],
        offset: int,
        batch_size: int,
        base_filters: Dict[str, Any],
        runtime_filters: Optional[Dict[str, Any]],
    ) -> str:
        fields = schema["fields"]
        select_columns = []
        for field in fields:
            oracle_column = field["physical_mapping"].get("oracle_column")
            if oracle_column:
                select_columns.append(f"{oracle_column} AS {field['field_id']}")
        select_clause = ", ".join(select_columns) if select_columns else "*"

        where_clauses = []
        if base_filters and base_filters.get("where_clause"):
            where_clauses.append(base_filters["where_clause"])
        if runtime_filters:
            if runtime_filters.get("date_from") and runtime_filters.get("date_column"):
                where_clauses.append(
                    f"{runtime_filters['date_column']} >= "
                    f"TO_DATE('{runtime_filters['date_from']}', 'YYYY-MM-DD')"
                )
            if runtime_filters.get("date_to") and runtime_filters.get("date_column"):
                where_clauses.append(
                    f"{runtime_filters['date_column']} <= "
                    f"TO_DATE('{runtime_filters['date_to']}', 'YYYY-MM-DD')"
                )
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        return f"""
            SELECT {select_clause}
            FROM {table_name}
            {where_clause}
            ORDER BY ROWID
            OFFSET {offset} ROWS
            FETCH NEXT {batch_size} ROWS ONLY
        """

    def _convert_to_canonical(
        self,
        row: Any,
        column_names: List[str],
        row_number: int,
    ) -> CanonicalRow:
        fields: Dict[str, Any] = {}
        for idx, column_name in enumerate(column_names):
            value = row[idx]
            if cx_Oracle is not None and isinstance(value, getattr(cx_Oracle, "LOB", ())):
                value = value.read()
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, date):
                value = value.isoformat()
            fields[column_name] = value

        metadata = {
            "source": "oracle",
            "row_number": row_number,
            "fetched_at": datetime.utcnow().isoformat(),
        }
        return CanonicalRow(fields=fields, metadata=metadata)
