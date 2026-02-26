"""Reference dataset manager."""

from __future__ import annotations

from typing import Any, Dict, Optional, Callable
import logging
from datetime import datetime

import pandas as pd

from ..connectors.factory import ConnectorFactory

logger = logging.getLogger(__name__)


class ReferenceHandle:
    """Handle to loaded reference dataset."""

    def __init__(self, data: pd.DataFrame, reference_id: str):
        self.data = data
        self.reference_id = reference_id
        self._index_cache: Dict[str, Dict[Any, Any]] = {}

    def lookup(self, key_field: str, key_value: Any, value_field: str) -> Optional[Any]:
        if key_field not in self._index_cache:
            self._index_cache[key_field] = (
                self.data.set_index(key_field)[value_field].to_dict()
            )
        return self._index_cache[key_field].get(key_value)

    def lookup_multiple(self, key_field: str, key_values: list, value_field: str) -> Dict[Any, Any]:
        return {key: self.lookup(key_field, key, value_field) for key in key_values}


class ReferenceDatasetManager:
    """Load and cache reference datasets."""

    def __init__(
        self,
        system_resolver: Optional[Callable[[str], Dict[str, Any]]] = None,
        schema_resolver: Optional[Callable[[str], Dict[str, Any]]] = None,
    ):
        self._cache: Dict[str, ReferenceHandle] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self.system_resolver = system_resolver
        self.schema_resolver = schema_resolver

    def load(self, reference_dataset_id: str, reference_config: Dict[str, Any]) -> ReferenceHandle:
        if reference_dataset_id in self._cache:
            logger.debug("Using cached reference dataset: %s", reference_dataset_id)
            return self._cache[reference_dataset_id]

        source_type = reference_config["source_type"]
        source_config = reference_config["source_config"]
        logger.info("Loading reference dataset: %s from %s", reference_dataset_id, source_type)

        if source_type == "CSV":
            data = self._load_from_csv(source_config)
        elif source_type == "ORACLE":
            data = self._load_from_oracle(source_config)
        elif source_type == "MONGODB":
            data = self._load_from_mongodb(source_config)
        elif source_type == "INLINE":
            data = self._load_from_inline(source_config)
        else:
            raise ValueError(f"Unsupported reference source type: {source_type}")

        handle = ReferenceHandle(data, reference_dataset_id)
        self._cache[reference_dataset_id] = handle
        self._metadata[reference_dataset_id] = {
            "loaded_at": datetime.utcnow().isoformat(),
            "row_count": len(data),
        }
        return handle

    def _load_from_csv(self, config: Dict[str, Any]) -> pd.DataFrame:
        file_path = config["file_path"]
        delimiter = config.get("delimiter", ",")
        has_header = config.get("has_header", True)
        encoding = config.get("encoding", "UTF-8")
        header = 0 if has_header else None
        return pd.read_csv(file_path, delimiter=delimiter, header=header, encoding=encoding)

    def _load_from_oracle(self, config: Dict[str, Any]) -> pd.DataFrame:
        system_id = config.get("system_id")
        query = config.get("query")
        if system_id and self.system_resolver:
            system = self.system_resolver(system_id)
            schema = config.get("schema", {"fields": []})
            reader = ConnectorFactory.create_reader(system["system_type"], system["connection_config"], schema)
            dataset = {"physical_name": config.get("table_name", "DUAL"), "filter_config": {}}
            with reader:
                batch = reader.fetch_batch(dataset, batch_size=config.get("batch_size", 10000))
            return pd.DataFrame([row.fields for row in batch.rows])
        if config.get("connection_config") and query:
            system = {
                "system_type": "ORACLE",
                "connection_config": config["connection_config"],
            }
            schema = config.get("schema", {"fields": []})
            reader = ConnectorFactory.create_reader(system["system_type"], system["connection_config"], schema)
            dataset = {"physical_name": config["table_name"], "filter_config": {"where_clause": query}}
            with reader:
                batch = reader.fetch_batch(dataset, batch_size=config.get("batch_size", 10000))
            return pd.DataFrame([row.fields for row in batch.rows])
        raise ValueError("Invalid Oracle reference dataset config")

    def _load_from_mongodb(self, config: Dict[str, Any]) -> pd.DataFrame:
        system_id = config.get("system_id")
        if system_id and self.system_resolver:
            system = self.system_resolver(system_id)
            schema = config.get("schema", {"fields": []})
            reader = ConnectorFactory.create_reader(system["system_type"], system["connection_config"], schema)
            dataset = {"physical_name": config["collection_name"], "filter_config": {"query": config.get("query")}}
            with reader:
                batch = reader.fetch_batch(dataset, batch_size=config.get("batch_size", 10000))
            return pd.DataFrame([row.fields for row in batch.rows])
        if config.get("connection_config"):
            system = {
                "system_type": "MONGODB",
                "connection_config": config["connection_config"],
            }
            schema = config.get("schema", {"fields": []})
            reader = ConnectorFactory.create_reader(system["system_type"], system["connection_config"], schema)
            dataset = {"physical_name": config["collection_name"], "filter_config": {"query": config.get("query")}}
            with reader:
                batch = reader.fetch_batch(dataset, batch_size=config.get("batch_size", 10000))
            return pd.DataFrame([row.fields for row in batch.rows])
        raise ValueError("Invalid MongoDB reference dataset config")

    def _load_from_inline(self, config: Dict[str, Any]) -> pd.DataFrame:
        data = config["data"]
        return pd.DataFrame(data)

    def get(self, reference_dataset_id: str) -> ReferenceHandle:
        if reference_dataset_id not in self._cache:
            raise ValueError(f"Reference dataset not loaded: {reference_dataset_id}")
        return self._cache[reference_dataset_id]

    def clear_cache(self) -> None:
        self._cache.clear()
        self._metadata.clear()
        logger.info("Cleared reference dataset cache")
