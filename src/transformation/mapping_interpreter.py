"""Mapping interpreter for transformation chains."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List
import logging

from ..connectors.base import CanonicalRow
from .transform_registry import TransformRegistry
from .reference_manager import ReferenceDatasetManager
from .validators import ValidationEngine

logger = logging.getLogger(__name__)


class TransformationContext:
    """Context passed through transformation chain."""

    def __init__(self, source_row: CanonicalRow, reference_manager: ReferenceDatasetManager):
        self.source_row = source_row
        self.reference_manager = reference_manager
        self.derived_fields: Dict[str, Any] = {}
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def get_source_field(self, field_id: str, default: Any = None) -> Any:
        return self.source_row.get_field(field_id, default)

    def set_derived_field(self, field_id: str, value: Any) -> None:
        self.derived_fields[field_id] = value

    def get_derived_field(self, field_id: str, default: Any = None) -> Any:
        return self.derived_fields.get(field_id, default)

    def add_error(self, field_id: str, message: str) -> None:
        self.errors.append(
            {"field": field_id, "message": message, "timestamp": datetime.utcnow().isoformat()}
        )

    def add_warning(self, field_id: str, message: str) -> None:
        self.warnings.append(
            {"field": field_id, "message": message, "timestamp": datetime.utcnow().isoformat()}
        )


class MappingInterpreter:
    """Interprets mapping metadata and transforms rows."""

    def __init__(
        self,
        mapping: Dict[str, Any],
        field_mappings: List[Dict[str, Any]],
        reference_manager: ReferenceDatasetManager,
        transform_registry: TransformRegistry,
        validation_engine: ValidationEngine,
    ):
        self.mapping = mapping
        self.field_mappings = field_mappings
        self.reference_manager = reference_manager
        self.transform_registry = transform_registry
        self.validation_engine = validation_engine

    def transform_row(self, source_row: CanonicalRow) -> CanonicalRow:
        context = TransformationContext(source_row, self.reference_manager)
        target_fields: Dict[str, Any] = {}

        for field_mapping in self.field_mappings:
            if not field_mapping.get("is_active", True):
                continue

            target_field_id = field_mapping["target_field_id"]
            try:
                value = self._apply_field_mapping(field_mapping, context)
                target_fields[target_field_id] = value
            except Exception as exc:
                logger.error("Transform failed for %s: %s", target_field_id, exc)
                context.add_error(target_field_id, str(exc))
                target_fields[target_field_id] = None

        return CanonicalRow(
            fields=target_fields,
            metadata={
                "source_metadata": source_row.metadata,
                "transformation_errors": context.errors,
                "transformation_warnings": context.warnings,
                "transformed_at": datetime.utcnow().isoformat(),
            },
        )

    def transform_batch(self, source_rows: List[CanonicalRow]) -> List[CanonicalRow]:
        return [self.transform_row(row) for row in source_rows]

    def _apply_field_mapping(self, field_mapping: Dict[str, Any], context: TransformationContext) -> Any:
        target_field_id = field_mapping["target_field_id"]

        if field_mapping.get("pre_validations"):
            self._run_validations(
                field_mapping["pre_validations"], context, target_field_id, phase="pre"
            )

        if field_mapping.get("source_expression"):
            value = self._evaluate_expression(field_mapping["source_expression"], context)
        elif field_mapping.get("transform_chain"):
            value = self._apply_transform_chain(field_mapping["transform_chain"], context)
        else:
            value = None

        if field_mapping.get("post_validations"):
            self._run_validations(
                field_mapping["post_validations"],
                context,
                target_field_id,
                phase="post",
                value=value,
            )

        return value

    def _evaluate_expression(self, expression: str, context: TransformationContext) -> Any:
        if expression.isidentifier():
            return context.get_source_field(expression)
        return context.get_source_field(expression)

    def _apply_transform_chain(self, transform_chain: Dict[str, Any], context: TransformationContext) -> Any:
        if isinstance(transform_chain, list):
            steps = transform_chain
        else:
            steps = transform_chain.get("steps", [])
        steps = sorted(steps, key=lambda s: s.get("step_order", 0))
        value = None
        for step in steps:
            value = self.transform_registry.execute(
                transform_type=step["transform_type"],
                params=step.get("params", {}),
                context=context,
                previous_value=value,
            )
        return value

    def _run_validations(
        self,
        validations: List[Dict[str, Any]],
        context: TransformationContext,
        field_id: str,
        phase: str,
        value: Any = None,
    ) -> None:
        if isinstance(validations, dict):
            validations = validations.get("validations", [])
        for validation in validations:
            validation_type = validation["validation_type"]
            params = validation.get("params", {})
            error_action = validation.get("error_action", "FAIL")
            is_valid, message = self.validation_engine.validate(
                validation_type=validation_type,
                params=params,
                context=context,
                value=value,
            )
            if not is_valid:
                if error_action == "FAIL":
                    raise ValueError(f"{phase}-validation failed for {field_id}: {message}")
                if error_action == "WARN":
                    context.add_warning(field_id, message)
