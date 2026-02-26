"""MongoDB data extraction with batching."""

from __future__ import annotations

from typing import Dict, Generator, Optional, Any


class MongoDBDataExtractor:
    """Extract data from MongoDB with cursor batching."""

    def __init__(self, database):
        self.database = database

    def extract_data(
        self,
        collection_name: str,
        query: Optional[Dict[str, Any]] = None,
        batch_size: int = 1000,
        flatten: bool = True,
    ) -> Generator[Dict[str, Any], None, None]:
        collection = self.database[collection_name]
        cursor = collection.find(query or {}).batch_size(batch_size)
        for doc in cursor:
            if flatten:
                yield self._flatten(doc)
            else:
                yield doc

    def _flatten(self, document: Dict[str, Any]) -> Dict[str, Any]:
        flattened: Dict[str, Any] = {}

        def _flatten_obj(obj: Any, prefix: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    path = f"{prefix}.{key}" if prefix else key
                    _flatten_obj(value, path)
            elif isinstance(obj, list):
                flattened[prefix] = obj
            else:
                flattened[prefix] = obj

        _flatten_obj(document)
        return flattened
