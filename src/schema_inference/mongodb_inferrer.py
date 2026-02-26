"""MongoDB schema inference."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List


class MongoDBSchemaInferrer:
    """Infer schema from MongoDB collection samples."""

    def __init__(self, database):
        self.database = database

    def infer_collection_schema(self, collection_name: str, sample_size: int = 100) -> Dict[str, Any]:
        collection = self.database[collection_name]
        documents = list(collection.find().limit(sample_size))
        fields = self.infer_from_samples(documents)
        return {
            "schema_id": f"{collection_name}_schema",
            "schema_name": f"{collection_name} schema",
            "fields": fields,
        }

    def infer_from_samples(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        field_types: Dict[str, set] = defaultdict(set)
        for doc in documents:
            for path, value in self.flatten_nested_paths(doc).items():
                field_types[path].add(self._infer_type(value))

        schema_fields = []
        for field_path, types in field_types.items():
            schema_fields.append(
                {
                    "field_id": field_path,
                    "field_name": field_path.split(".")[-1],
                    "data_type": self._resolve_type(types),
                    "is_nullable": False,
                    "is_key": field_path in {"_id", "id"},
                    "physical_mapping": {"mongo_path": field_path},
                }
            )
        return schema_fields

    def flatten_nested_paths(self, document: Dict[str, Any]) -> Dict[str, Any]:
        flattened: Dict[str, Any] = {}

        def _flatten(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    path = f"{prefix}.{key}" if prefix else key
                    _flatten(value, path)
            elif isinstance(obj, list):
                flattened[prefix] = obj
            else:
                flattened[prefix] = obj

        _flatten(document)
        return flattened

    def _infer_type(self, value: Any) -> str:
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "BOOLEAN"
        if isinstance(value, int):
            return "INTEGER"
        if isinstance(value, float):
            return "DECIMAL"
        if isinstance(value, list):
            return "ARRAY"
        if isinstance(value, dict):
            return "OBJECT"
        return "STRING"

    def _resolve_type(self, types: set) -> str:
        types = {t for t in types if t != "NULL"}
        if not types:
            return "STRING"
        if "OBJECT" in types:
            return "OBJECT"
        if "ARRAY" in types:
            return "ARRAY"
        if "DECIMAL" in types and "INTEGER" in types:
            return "DECIMAL"
        if len(types) == 1:
            return next(iter(types))
        return "STRING"
