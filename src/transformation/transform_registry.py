"""Transformation function registry."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, Dict
import re
import logging

logger = logging.getLogger(__name__)


class TransformRegistry:
    """Registry for transformation functions."""

    def __init__(self) -> None:
        self._transforms: Dict[str, Callable] = {}
        self._register_builtin_transforms()

    def register(self, name: str, func: Callable) -> None:
        self._transforms[name] = func
        logger.info("Registered transform: %s", name)

    def execute(
        self,
        transform_type: str,
        params: Dict[str, Any],
        context: "TransformationContext",
        previous_value: Any = None,
    ) -> Any:
        if transform_type not in self._transforms:
            raise ValueError(f"Unknown transform type: {transform_type}")
        return self._transforms[transform_type](params, context, previous_value)

    def _register_builtin_transforms(self) -> None:
        self.register("direct", self._direct)
        self.register("concat", self._concat)
        self.register("substring", self._substring)
        self.register("upper_case", self._upper_case)
        self.register("lower_case", self._lower_case)
        self.register("trim", self._trim)
        self.register("replace", self._replace)

        self.register("add", self._add)
        self.register("subtract", self._subtract)
        self.register("multiply", self._multiply)
        self.register("divide", self._divide)
        self.register("round", self._round)

        self.register("parse_date", self._parse_date)
        self.register("format_date", self._format_date)
        self.register("date_diff", self._date_diff)
        self.register("date_add", self._date_add)

        self.register("lookup", self._lookup)
        self.register("conditional", self._conditional)

        self.register("to_string", self._to_string)
        self.register("to_int", self._to_int)
        self.register("to_decimal", self._to_decimal)

    def _direct(self, params: Dict, context, previous_value) -> Any:
        source_field = params["source_field"]
        return context.get_source_field(source_field)

    def _concat(self, params: Dict, context, previous_value) -> str:
        source_fields = params["source_fields"]
        separator = params.get("separator", "")
        trim = params.get("trim", False)
        values = []
        for field in source_fields:
            value = context.get_source_field(field)
            if value is not None:
                value_str = str(value)
                values.append(value_str.strip() if trim else value_str)
        return separator.join(values)

    def _substring(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        if value is None:
            return None
        value_str = str(value)
        start = params.get("start", 0)
        length = params.get("length")
        return value_str[start:start + length] if length else value_str[start:]

    def _upper_case(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return str(value).upper() if value is not None else None

    def _lower_case(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return str(value).lower() if value is not None else None

    def _trim(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return str(value).strip() if value is not None else None

    def _replace(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        if value is None:
            return None
        value_str = str(value)
        pattern = params["pattern"]
        replacement = params["replacement"]
        if params.get("is_regex", False):
            return re.sub(pattern, replacement, value_str)
        return value_str.replace(pattern, replacement)

    def _add(self, params: Dict, context, previous_value) -> Decimal:
        left = params.get("left_field")
        right = params.get("right_field")
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get("value", 0)))
        return left_val + right_val

    def _subtract(self, params: Dict, context, previous_value) -> Decimal:
        left = params.get("left_field")
        right = params.get("right_field")
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get("value", 0)))
        return left_val - right_val

    def _multiply(self, params: Dict, context, previous_value) -> Decimal:
        left = params.get("left_field")
        right = params.get("right_field")
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get("value", 1)))
        return left_val * right_val

    def _divide(self, params: Dict, context, previous_value) -> Decimal:
        left = params.get("left_field")
        right = params.get("right_field")
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get("value", 1)))
        if right_val == 0:
            raise ValueError("Division by zero")
        return left_val / right_val

    def _round(self, params: Dict, context, previous_value) -> Decimal:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        decimals = params.get("decimals", 0)
        return round(Decimal(str(value)), decimals)

    def _parse_date(self, params: Dict, context, previous_value) -> datetime:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        if value is None:
            return None
        format_str = params.get("format", "%Y-%m-%d")
        if isinstance(value, datetime):
            return value
        return datetime.strptime(str(value), format_str)

    def _format_date(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        if value is None:
            return None
        format_str = params.get("format", "%Y-%m-%d")
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        return value.strftime(format_str)

    def _date_diff(self, params: Dict, context, previous_value) -> int:
        date1 = context.get_source_field(params["date1_field"])
        date2 = context.get_source_field(params["date2_field"])
        if isinstance(date1, str):
            date1 = datetime.fromisoformat(date1)
        if isinstance(date2, str):
            date2 = datetime.fromisoformat(date2)
        diff = date2 - date1
        unit = params.get("unit", "days")
        if unit == "hours":
            return int(diff.total_seconds() / 3600)
        if unit == "minutes":
            return int(diff.total_seconds() / 60)
        return diff.days

    def _date_add(self, params: Dict, context, previous_value) -> datetime:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        delta = timedelta(
            days=params.get("days", 0),
            hours=params.get("hours", 0),
            minutes=params.get("minutes", 0),
        )
        return value + delta

    def _lookup(self, params: Dict, context, previous_value) -> Any:
        reference_dataset_id = params["reference_dataset"]
        source_field = params["source_field"]
        ref_key_field = params["ref_key_field"]
        ref_value_field = params["ref_value_field"]
        default = params.get("default")

        lookup_key = context.get_source_field(source_field)
        if lookup_key is None:
            return default
        ref_data = context.reference_manager.get(reference_dataset_id)
        result = ref_data.lookup(ref_key_field, lookup_key, ref_value_field)
        return result if result is not None else default

    def _conditional(self, params: Dict, context, previous_value) -> Any:
        condition_field = params["condition_field"]
        operator = params["operator"]
        compare_value = params["compare_value"]
        true_value = params["true_value"]
        false_value = params["false_value"]

        field_value = context.get_source_field(condition_field)
        condition_met = False

        if operator == "equals":
            condition_met = field_value == compare_value
        elif operator == "not_equals":
            condition_met = field_value != compare_value
        elif operator == "greater_than":
            condition_met = field_value > compare_value
        elif operator == "less_than":
            condition_met = field_value < compare_value
        elif operator == "contains":
            condition_met = compare_value in str(field_value)

        return true_value if condition_met else false_value

    def _to_string(self, params: Dict, context, previous_value) -> str:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return str(value) if value is not None else None

    def _to_int(self, params: Dict, context, previous_value) -> int:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return int(value) if value is not None else None

    def _to_decimal(self, params: Dict, context, previous_value) -> Decimal:
        value = context.get_source_field(params["source_field"]) if "source_field" in params else previous_value
        return Decimal(str(value)) if value is not None else None
