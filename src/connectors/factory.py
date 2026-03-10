"""Factory for connector implementations."""

from __future__ import annotations

from typing import Any, Dict, Type

from .base import DatasetReader
from .file_reader import FileDatasetReader
from .mongo_reader import MongoDatasetReader
from .oracle_reader import OracleDatasetReader


class ConnectorFactory:
    """Create dataset readers by system type."""

    _readers: Dict[str, Type[DatasetReader]] = {
        "ORACLE": OracleDatasetReader,
        "MONGODB": MongoDatasetReader,
        "FILE": FileDatasetReader,
    }

    @classmethod
    def create_reader(
        cls,
        system_type: str,
        system_config: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> DatasetReader:
        reader_class = cls._readers.get(system_type)
        if not reader_class:
            raise ValueError(f"Unsupported system type: {system_type}")
        return reader_class(system_config, schema)

    @classmethod
    def register_reader(cls, system_type: str, reader_class: Type[DatasetReader]) -> None:
        cls._readers[system_type] = reader_class
