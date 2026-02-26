"""Base connector interfaces and types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CanonicalRow:
    """Unified internal representation of a data row."""

    fields: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_field(self, field_id: str, default: Any = None) -> Any:
        return self.fields.get(field_id, default)

    def set_field(self, field_id: str, value: Any) -> None:
        self.fields[field_id] = value

    def to_dict(self) -> Dict[str, Any]:
        return {"fields": self.fields, "metadata": self.metadata}


@dataclass
class BatchResult:
    rows: List[CanonicalRow]
    cursor: Optional[Any]
    has_more: bool
    batch_metadata: Dict[str, Any]


class DatasetReader(ABC):
    """Abstract base class for dataset readers."""

    def __init__(self, system_config: Dict[str, Any], schema: Dict[str, Any]):
        self.system_config = system_config
        self.schema = schema
        self.connection = None

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def fetch_batch(
        self,
        dataset: Dict[str, Any],
        cursor: Optional[Any] = None,
        batch_size: int = 10000,
        filters: Optional[Dict[str, Any]] = None,
    ) -> BatchResult:
        pass

    @abstractmethod
    def get_row_count(
        self,
        dataset: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        pass

    @abstractmethod
    def validate_schema(self, dataset: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
