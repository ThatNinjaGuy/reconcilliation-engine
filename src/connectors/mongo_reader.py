"""MongoDB dataset reader implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId

from .base import BatchResult, CanonicalRow, DatasetReader
from .exceptions import ConnectionError

logger = logging.getLogger(__name__)


class MongoDatasetReader(DatasetReader):
    """MongoDB connector using PyMongo."""

    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        super().__init__(system_config, schema)
        self.client = None
        self.database = None

    def connect(self) -> bool:
        try:
            connection_string = self.system_config["connection_string"]
            database_name = self.system_config["database"]
            max_pool_size = self.system_config.get("max_pool_size", 50)
            timeout_ms = self.system_config.get("timeout_ms", 30000)

            self.client = MongoClient(
                connection_string,
                maxPoolSize=max_pool_size,
                serverSelectionTimeoutMS=timeout_ms,
            )
            self.client.admin.command("ping")
            self.database = self.client[database_name]
            logger.info("MongoDB connection established")
            return True
        except ConnectionFailure as exc:
            raise ConnectionError(str(exc)) from exc

    def disconnect(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        start_time = datetime.utcnow()
        collection_name = dataset["physical_name"]
        filter_config = dataset.get("filter_config", {})
        collection = self.database[collection_name]

        query = self._build_query(
            base_filters=filter_config,
            runtime_filters=filters,
            cursor=cursor,
        )
        projection = self._build_projection(self.schema)
        documents = list(collection.find(query, projection).limit(batch_size))

        canonical_rows = []
        for idx, doc in enumerate(documents):
            canonical_rows.append(self._convert_to_canonical(doc, idx))

        has_more = len(documents) == batch_size
        next_cursor = None
        if has_more and documents:
            next_cursor = {"last_id": documents[-1].get("_id")}

        batch_metadata = {
            "source": "mongodb",
            "collection": collection_name,
            "rows_fetched": len(documents),
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
        collection_name = dataset["physical_name"]
        filter_config = dataset.get("filter_config", {})
        collection = self.database[collection_name]
        query = self._build_query(
            base_filters=filter_config,
            runtime_filters=filters,
            cursor=None,
        )
        return collection.count_documents(query)

    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        collection_name = dataset["physical_name"]
        schema_fields = self.schema["fields"]
        validation_result = {"valid": True, "errors": [], "warnings": []}
        collection = self.database[collection_name]
        sample_docs = list(collection.find().limit(100))
        if not sample_docs:
            validation_result["warnings"].append(
                f"Collection {collection_name} is empty, cannot validate schema"
            )
            return validation_result

        for field in schema_fields:
            mongo_path = field["physical_mapping"].get("mongo_path")
            if not mongo_path:
                continue
            found = 0
            for doc in sample_docs:
                value = self._extract_nested_value(doc, mongo_path)
                if value is not None:
                    found += 1
            if found == 0:
                validation_result["valid"] = False
                validation_result["errors"].append(
                    f"Path {mongo_path} not found in any sample documents"
                )
        return validation_result

    def _build_query(
        self,
        base_filters: Dict[str, Any],
        runtime_filters: Optional[Dict[str, Any]],
        cursor: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        query: Dict[str, Any] = {}
        if base_filters and base_filters.get("query"):
            query.update(base_filters["query"])
        if cursor and "last_id" in cursor:
            query["_id"] = {"$gt": cursor["last_id"]}
        if runtime_filters:
            if runtime_filters.get("date_from") and runtime_filters.get("date_field"):
                date_field = runtime_filters["date_field"]
                query.setdefault(date_field, {})
                query[date_field]["$gte"] = datetime.fromisoformat(runtime_filters["date_from"])
            if runtime_filters.get("date_to") and runtime_filters.get("date_field"):
                date_field = runtime_filters["date_field"]
                query.setdefault(date_field, {})
                query[date_field]["$lte"] = datetime.fromisoformat(runtime_filters["date_to"])
        return query

    def _build_projection(self, schema: Dict[str, Any]) -> Dict[str, int]:
        projection: Dict[str, int] = {}
        for field in schema["fields"]:
            mongo_path = field["physical_mapping"].get("mongo_path")
            if mongo_path:
                projection[mongo_path] = 1
        projection["_id"] = 1
        return projection

    def _convert_to_canonical(self, document: Dict[str, Any], row_number: int) -> CanonicalRow:
        fields: Dict[str, Any] = {}
        for field in self.schema["fields"]:
            mongo_path = field["physical_mapping"].get("mongo_path")
            if mongo_path:
                value = self._extract_nested_value(document, mongo_path)
                fields[field["field_id"]] = self._convert_value(value, field["data_type"])

        metadata = {
            "source": "mongodb",
            "_id": str(document.get("_id")),
            "row_number": row_number,
            "fetched_at": datetime.utcnow().isoformat(),
        }
        return CanonicalRow(fields=fields, metadata=metadata)

    def _extract_nested_value(self, document: Dict[str, Any], path: str) -> Any:
        keys = path.split(".")
        value: Any = document
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif isinstance(value, list) and key.isdigit():
                idx = int(key)
                value = value[idx] if idx < len(value) else None
            else:
                value = None
            if value is None:
                break
        return value

    def _convert_value(self, value: Any, target_type: str) -> Any:
        if value is None:
            return None
        if target_type == "STRING":
            return str(value) if not isinstance(value, ObjectId) else str(value)
        if target_type == "INTEGER":
            return int(value)
        if target_type == "DECIMAL":
            return float(value)
        if target_type == "TIMESTAMP":
            return value.isoformat() if isinstance(value, datetime) else value
        if target_type == "BOOLEAN":
            return bool(value)
        return value
