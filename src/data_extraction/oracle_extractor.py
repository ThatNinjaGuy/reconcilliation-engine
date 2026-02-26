"""Oracle data extraction with batching."""

from __future__ import annotations

from typing import Dict, Generator, Optional, Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


class OracleDataExtractor:
    """Extract data from Oracle with batch processing."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def extract_data(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: int = 1000,
        transformations: Optional[Dict[str, Any]] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        offset = 0
        while True:
            query = self._build_query(table_name, filters, offset, batch_size)
            result = self.connection.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            if not rows:
                break
            for row in rows:
                record = dict(zip(columns, row))
                if transformations:
                    record = self._apply_transformations(record, transformations)
                yield record
            if len(rows) < batch_size:
                break
            offset += batch_size

    def _build_query(
        self,
        table_name: str,
        filters: Optional[Dict[str, Any]],
        offset: int,
        batch_size: int,
    ) -> str:
        where_clause = ""
        if filters:
            conditions = [f"{key} = '{value}'" for key, value in filters.items()]
            where_clause = "WHERE " + " AND ".join(conditions)
        return f"""
            SELECT * FROM {table_name}
            {where_clause}
            ORDER BY ROWID
            OFFSET {offset} ROWS FETCH NEXT {batch_size} ROWS ONLY
        """

    def _apply_transformations(self, record: Dict[str, Any], transformations: Dict[str, Any]) -> Dict[str, Any]:
        transformed = dict(record)
        for field, func in transformations.items():
            transformed[field] = func(transformed.get(field))
        return transformed
