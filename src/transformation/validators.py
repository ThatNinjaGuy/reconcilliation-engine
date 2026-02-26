"""Validation engine for transformations."""

from __future__ import annotations

from typing import Any, Dict, Tuple
import re


class ValidationEngine:
    """Executes validation rules on field values."""

    def __init__(self) -> None:
        self._validators: Dict[str, Any] = {}
        self._register_builtin_validators()

    def register(self, name: str, func) -> None:
        self._validators[name] = func

    def validate(
        self,
        validation_type: str,
        params: Dict[str, Any],
        context: "TransformationContext",
        value: Any = None,
    ) -> Tuple[bool, str]:
        if validation_type not in self._validators:
            raise ValueError(f"Unknown validation type: {validation_type}")
        func = self._validators[validation_type]
        return func(params, context, value)

    def _register_builtin_validators(self) -> None:
        self.register("not_null", self._not_null)
        self.register("max_length", self._max_length)
        self.register("min_length", self._min_length)
        self.register("regex", self._regex)
        self.register("range", self._range)
        self.register("in_list", self._in_list)

    def _not_null(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        fields = params.get("fields", [])
        for field in fields:
            field_value = context.get_source_field(field)
            if field_value is None:
                return False, f"Field {field} is null"
        return True, "OK"

    def _max_length(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        max_len = params["length"]
        if value is None:
            return True, "OK"
        if len(str(value)) > max_len:
            return False, f"Length {len(str(value))} exceeds max {max_len}"
        return True, "OK"

    def _min_length(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        min_len = params["length"]
        if value is None:
            return True, "OK"
        if len(str(value)) < min_len:
            return False, f"Length {len(str(value))} below min {min_len}"
        return True, "OK"

    def _regex(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        pattern = params["pattern"]
        if value is None:
            return True, "OK"
        if not re.match(pattern, str(value)):
            return False, f"Value does not match pattern {pattern}"
        return True, "OK"

    def _range(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        min_val = params.get("min")
        max_val = params.get("max")
        if value is None:
            return True, "OK"
        numeric_value = float(value)
        if min_val is not None and numeric_value < min_val:
            return False, f"Value {numeric_value} below min {min_val}"
        if max_val is not None and numeric_value > max_val:
            return False, f"Value {numeric_value} above max {max_val}"
        return True, "OK"

    def _in_list(self, params: Dict[str, Any], context, value) -> Tuple[bool, str]:
        allowed_values = params["values"]
        if value is None:
            return True, "OK"
        if value not in allowed_values:
            return False, f"Value {value} not in allowed list"
        return True, "OK"
