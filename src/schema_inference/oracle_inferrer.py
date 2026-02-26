"""Oracle schema inference."""

from __future__ import annotations

from typing import Dict, List, Any
import re

from sqlalchemy import text
from sqlalchemy.engine import Connection


class OracleSchemaInferrer:
    """Infer Oracle table schema and map to generic schema."""

    GENERIC_TYPE_MAP = {
        "NUMBER": "DECIMAL",
        "INTEGER": "INTEGER",
        "VARCHAR2": "STRING",
        "CHAR": "STRING",
        "DATE": "DATE",
        "TIMESTAMP": "TIMESTAMP",
        "CLOB": "STRING",
        "BLOB": "STRING",
    }

    def __init__(self, connection: Connection):
        self.connection = connection

    def infer_table_schema(self, table_name: str) -> Dict[str, Any]:
        fields = self._get_columns(table_name)
        pk_fields = set(self.get_primary_keys(table_name))
        fk_fields = {fk["column_name"]: fk for fk in self.get_foreign_keys(table_name)}

        schema_fields = []
        for col in fields:
            field_id = self._to_field_id(col["column_name"])
            schema_fields.append(
                {
                    "field_id": field_id,
                    "field_name": col["column_name"],
                    "data_type": self.map_to_generic_type(col["data_type"]),
                    "max_length": col.get("data_length"),
                    "precision": col.get("data_precision"),
                    "scale": col.get("data_scale"),
                    "is_nullable": col.get("nullable") == "Y",
                    "is_key": col["column_name"] in pk_fields,
                    "physical_mapping": {"oracle_column": col["column_name"]},
                    "foreign_key": fk_fields.get(col["column_name"]),
                }
            )

        return {
            "schema_id": f"{table_name.lower()}_schema",
            "schema_name": f"{table_name} schema",
            "fields": schema_fields,
        }

    def get_primary_keys(self, table_name: str) -> List[str]:
        query = """
            SELECT cols.column_name
            FROM all_constraints cons
            JOIN all_cons_columns cols
              ON cons.constraint_name = cols.constraint_name
             AND cons.owner = cols.owner
            WHERE cons.constraint_type = 'P'
              AND cons.table_name = UPPER(:table_name)
        """
        result = self.connection.execute(text(query), {"table_name": table_name})
        return [row[0] for row in result.fetchall()]

    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        query = """
            SELECT a.column_name,
                   c_pk.table_name r_table_name,
                   b.column_name r_column_name
            FROM all_cons_columns a
            JOIN all_constraints c
              ON a.owner = c.owner AND a.constraint_name = c.constraint_name
            JOIN all_constraints c_pk
              ON c.r_owner = c_pk.owner AND c.r_constraint_name = c_pk.constraint_name
            JOIN all_cons_columns b
              ON c_pk.owner = b.owner AND c_pk.constraint_name = b.constraint_name
            WHERE c.constraint_type = 'R'
              AND a.table_name = UPPER(:table_name)
        """
        result = self.connection.execute(text(query), {"table_name": table_name})
        return [
            {
                "column_name": row[0],
                "referenced_table": row[1],
                "referenced_field": row[2],
            }
            for row in result.fetchall()
        ]

    def map_to_generic_type(self, oracle_type: str) -> str:
        clean_type = re.split(r"[ (]", oracle_type.upper())[0]
        return self.GENERIC_TYPE_MAP.get(clean_type, "STRING")

    def _get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        query = """
            SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
            FROM USER_TAB_COLUMNS
            WHERE TABLE_NAME = UPPER(:table_name)
        """
        result = self.connection.execute(text(query), {"table_name": table_name})
        columns = []
        for row in result.fetchall():
            columns.append(
                {
                    "column_name": row[0],
                    "data_type": row[1],
                    "data_length": row[2],
                    "data_precision": row[3],
                    "data_scale": row[4],
                    "nullable": row[5],
                }
            )
        return columns

    def _to_field_id(self, column_name: str) -> str:
        parts = column_name.lower().split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])
