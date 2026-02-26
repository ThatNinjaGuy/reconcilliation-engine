"""Field-level comparison logic."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)


class FieldComparator:
    """Compares field values with configured rules."""

    def __init__(self) -> None:
        self._comparators: Dict[str, Any] = {}
        self._register_builtin_comparators()

    def register(self, name: str, func) -> None:
        self._comparators[name] = func

    def compare(
        self,
        source_value: Any,
        target_value: Any,
        comparator_type: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        if comparator_type not in self._comparators:
            raise ValueError(f"Unknown comparator type: {comparator_type}")
        func = self._comparators[comparator_type]
        return func(source_value, target_value, params or {})

    def _register_builtin_comparators(self) -> None:
        self.register("EXACT", self._exact)
        self.register("NUMERIC_TOLERANCE", self._numeric_tolerance)
        self.register("DATE_WINDOW", self._date_window)
        self.register("CASE_INSENSITIVE", self._case_insensitive)
        self.register("REGEX", self._regex)
        self.register("NULL_EQUALS_EMPTY", self._null_equals_empty)
        self.register("CUSTOM", self._custom)

    def _exact(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        if source_value is None and target_value is None:
            return True, None
        if source_value is None or target_value is None:
            return False, f"One value is null: source={source_value}, target={target_value}"

        if type(source_value) != type(target_value):
            if isinstance(source_value, str) and not isinstance(target_value, str):
                target_value = str(target_value)
            elif isinstance(target_value, str) and not isinstance(source_value, str):
                source_value = str(source_value)

        if source_value == target_value:
            return True, None
        return False, f"{source_value} != {target_value}"

    def _numeric_tolerance(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        if source_value is None and target_value is None:
            return True, None
        if source_value is None or target_value is None:
            return False, "One value is null"

        tolerance = Decimal(str(params.get("tolerance", 0)))
        tolerance_type = params.get("tolerance_type", "ABSOLUTE")

        source_decimal = Decimal(str(source_value))
        target_decimal = Decimal(str(target_value))
        diff = abs(source_decimal - target_decimal)

        if tolerance_type == "ABSOLUTE":
            within = diff <= tolerance
        else:
            if target_decimal == 0:
                within = diff == 0
            else:
                within = (diff / abs(target_decimal)) * 100 <= tolerance

        if within:
            return True, None
        return False, f"Difference {diff} exceeds tolerance {tolerance}"

    def _date_window(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        if source_value is None and target_value is None:
            return True, None
        if source_value is None or target_value is None:
            return False, "One value is null"

        window_seconds = params.get("window_seconds", 0)
        if isinstance(source_value, str):
            source_value = datetime.fromisoformat(source_value)
        if isinstance(target_value, str):
            target_value = datetime.fromisoformat(target_value)
        diff = abs((source_value - target_value).total_seconds())
        if diff <= window_seconds:
            return True, None
        return False, f"Time difference {diff}s exceeds window {window_seconds}s"

    def _case_insensitive(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        if source_value is None and target_value is None:
            return True, None
        if source_value is None or target_value is None:
            return False, "One value is null"
        if str(source_value).lower() == str(target_value).lower():
            return True, None
        return False, f"{source_value} != {target_value} (case-insensitive)"

    def _regex(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        pattern = params["pattern"]
        if source_value is None and target_value is None:
            return True, None
        if source_value is None or target_value is None:
            return False, "One value is null"
        source_match = re.match(pattern, str(source_value)) is not None
        target_match = re.match(pattern, str(target_value)) is not None
        if source_match and target_match:
            return True, None
        return False, f"Values don't both match pattern {pattern}"

    def _null_equals_empty(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        source_norm = source_value if source_value not in [None, ""] else None
        target_norm = target_value if target_value not in [None, ""] else None
        if source_norm == target_norm:
            return True, None
        return False, f"{source_value} != {target_value}"

    def _custom(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        raise NotImplementedError("Custom comparators not yet implemented")
