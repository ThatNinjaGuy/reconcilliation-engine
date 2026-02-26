# Reconciliation Engine - Detailed Design Document

**Component**: Reconciliation Engine  
**Version**: 1.0  
**Date**: January 30, 2026  
**Dependencies**: Pandas, NumPy

---

## 1. Component Overview

The Reconciliation Engine compares transformed source data (Oracle mapped to target shape) with actual target data (MongoDB) to identify matches, mismatches, and discrepancies.

**Key Responsibilities**:
- Match source and target records using matching keys
- Compare field values using configured comparison rules
- Detect and categorize discrepancies
- Generate reconciliation statistics and reports

---

## 2. Core Components

### 2.1 Record Matcher

```python
# src/reconciliation/matcher.py

from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
import logging
from datetime import datetime

from ..connectors.base import CanonicalRow

logger = logging.getLogger(__name__)

@dataclass
class MatchedPair:
    """Represents a matched source-target record pair"""
    key: str  # Matching key value
    source_row: CanonicalRow
    target_row: CanonicalRow
    metadata: Dict[str, Any] = None

@dataclass
class MatchResult:
    """Result of matching operation"""
    matched_pairs: List[MatchedPair]
    unmatched_source: List[CanonicalRow]
    unmatched_target: List[CanonicalRow]
    match_stats: Dict[str, Any]

class RecordMatcher:
    """
    Matches source and target records using configured matching keys.
    Supports exact matching and fuzzy matching strategies.
    """
    
    def __init__(self, matching_config: Dict[str, Any]):
        """
        Args:
            matching_config: Contains matching_keys and matching_strategy
        """
        self.matching_config = matching_config
        self.matching_keys = matching_config['matching_keys']
        self.matching_strategy = matching_config.get('matching_strategy', 'EXACT')
    
    def match(
        self,
        source_rows: List[CanonicalRow],
        target_rows: List[CanonicalRow]
    ) -> MatchResult:
        """
        Match source and target rows.
        
        Args:
            source_rows: Transformed source rows (Oracle → target shape)
            target_rows: Actual target rows (MongoDB)
        
        Returns:
            MatchResult containing matched pairs and unmatched records
        """
        start_time = datetime.now()
        
        if self.matching_strategy == 'EXACT':
            result = self._exact_match(source_rows, target_rows)
        elif self.matching_strategy == 'FUZZY':
            result = self._fuzzy_match(source_rows, target_rows)
        else:
            raise ValueError(f"Unknown matching strategy: {self.matching_strategy}")
        
        # Calculate statistics
        result.match_stats = {
            "total_source": len(source_rows),
            "total_target": len(target_rows),
            "matched": len(result.matched_pairs),
            "unmatched_source": len(result.unmatched_source),
            "unmatched_target": len(result.unmatched_target),
            "match_rate": len(result.matched_pairs) / max(len(source_rows), 1) * 100,
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        logger.info(
            f"Matched {result.match_stats['matched']} of "
            f"{result.match_stats['total_source']} source records "
            f"({result.match_stats['match_rate']:.2f}%)"
        )
        
        return result
    
    def _exact_match(
        self,
        source_rows: List[CanonicalRow],
        target_rows: List[CanonicalRow]
    ) -> MatchResult:
        """Exact key-based matching"""
        
        # Build indexes on matching keys
        source_index = self._build_index(source_rows, 'source')
        target_index = self._build_index(target_rows, 'target')
        
        # Find matched, unmatched
        source_keys = set(source_index.keys())
        target_keys = set(target_index.keys())
        
        matched_keys = source_keys & target_keys
        unmatched_source_keys = source_keys - target_keys
        unmatched_target_keys = target_keys - source_keys
        
        # Create matched pairs
        matched_pairs = []
        for key in matched_keys:
            # Handle multiple source/target rows with same key (rare but possible)
            source_list = source_index[key]
            target_list = target_index[key]
            
            # Simple 1:1 pairing (take first of each)
            matched_pairs.append(MatchedPair(
                key=key,
                source_row=source_list[0],
                target_row=target_list[0],
                metadata={
                    "source_count": len(source_list),
                    "target_count": len(target_list)
                }
            ))
            
            if len(source_list) > 1 or len(target_list) > 1:
                logger.warning(f"Duplicate key {key}: {len(source_list)} source, {len(target_list)} target")
        
        # Unmatched records
        unmatched_source = []
        for key in unmatched_source_keys:
            unmatched_source.extend(source_index[key])
        
        unmatched_target = []
        for key in unmatched_target_keys:
            unmatched_target.extend(target_index[key])
        
        return MatchResult(
            matched_pairs=matched_pairs,
            unmatched_source=unmatched_source,
            unmatched_target=unmatched_target,
            match_stats={}
        )
    
    def _build_index(
        self,
        rows: List[CanonicalRow],
        side: str
    ) -> Dict[str, List[CanonicalRow]]:
        """
        Build index on matching keys.
        
        Returns:
            Dict mapping key -> list of rows with that key
        """
        index = {}
        
        for row in rows:
            key = self._extract_matching_key(row, side)
            
            if key not in index:
                index[key] = []
            
            index[key].append(row)
        
        return index
    
    def _extract_matching_key(self, row: CanonicalRow, side: str) -> str:
        """
        Extract matching key from row.
        
        For composite keys, concatenates with delimiter.
        """
        key_parts = []
        
        for key_config in self.matching_keys:
            field_name = key_config[f'{side}_field']
            is_case_sensitive = key_config.get('is_case_sensitive', True)
            
            value = row.get_field(field_name)
            
            if value is None:
                value = ''
            else:
                value = str(value)
                if not is_case_sensitive:
                    value = value.lower()
            
            key_parts.append(value)
        
        # Use pipe delimiter for composite keys
        return '|'.join(key_parts)
    
    def _fuzzy_match(
        self,
        source_rows: List[CanonicalRow],
        target_rows: List[CanonicalRow]
    ) -> MatchResult:
        """
        Fuzzy matching using similarity scores.
        (Placeholder for future implementation)
        """
        # Future: Use fuzzywuzzy, embeddings, or other fuzzy matching techniques
        raise NotImplementedError("Fuzzy matching not yet implemented")
```

---

### 2.2 Field Comparator

```python
# src/reconciliation/comparator.py

from typing import Any, Dict, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

class FieldComparator:
    """
    Compares individual field values using configured comparison rules.
    """
    
    def __init__(self):
        self._comparators = {}
        self._register_builtin_comparators()
    
    def register(self, name: str, func):
        """Register custom comparator"""
        self._comparators[name] = func
    
    def compare(
        self,
        source_value: Any,
        target_value: Any,
        comparator_type: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Compare two values.
        
        Args:
            source_value: Value from source
            target_value: Value from target
            comparator_type: Type of comparison
            params: Comparator-specific parameters
        
        Returns:
            (values_match, difference_description)
        """
        if comparator_type not in self._comparators:
            raise ValueError(f"Unknown comparator type: {comparator_type}")
        
        func = self._comparators[comparator_type]
        return func(source_value, target_value, params or {})
    
    def _register_builtin_comparators(self):
        """Register built-in comparators"""
        
        self.register('EXACT', self._exact)
        self.register('NUMERIC_TOLERANCE', self._numeric_tolerance)
        self.register('DATE_WINDOW', self._date_window)
        self.register('CASE_INSENSITIVE', self._case_insensitive)
        self.register('REGEX', self._regex)
        self.register('NULL_EQUALS_EMPTY', self._null_equals_empty)
        self.register('CUSTOM', self._custom)
    
    def _exact(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """Exact equality comparison"""
        
        # Handle None/null
        if source_value is None and target_value is None:
            return True, None
        
        if source_value is None or target_value is None:
            return False, f"One value is null: source={source_value}, target={target_value}"
        
        # Type normalization
        if type(source_value) != type(target_value):
            # Try converting to same type
            try:
                if isinstance(source_value, str) and not isinstance(target_value, str):
                    target_value = str(target_value)
                elif isinstance(target_value, str) and not isinstance(source_value, str):
                    source_value = str(source_value)
            except:
                pass
        
        if source_value == target_value:
            return True, None
        else:
            return False, f"{source_value} != {target_value}"
    
    def _numeric_tolerance(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """
        Numeric comparison with tolerance.
        
        Params:
            tolerance: Absolute or percentage tolerance
            tolerance_type: 'ABSOLUTE' or 'PERCENTAGE'
        """
        if source_value is None and target_value is None:
            return True, None
        
        if source_value is None or target_value is None:
            return False, f"One value is null"
        
        tolerance = Decimal(str(params.get('tolerance', 0)))
        tolerance_type = params.get('tolerance_type', 'ABSOLUTE')
        
        source_decimal = Decimal(str(source_value))
        target_decimal = Decimal(str(target_value))
        
        diff = abs(source_decimal - target_decimal)
        
        if tolerance_type == 'ABSOLUTE':
            within_tolerance = diff <= tolerance
        else:  # PERCENTAGE
            if target_decimal == 0:
                within_tolerance = (diff == 0)
            else:
                percentage_diff = (diff / abs(target_decimal)) * 100
                within_tolerance = percentage_diff <= tolerance
        
        if within_tolerance:
            return True, None
        else:
            return False, f"Difference {diff} exceeds tolerance {tolerance}"
    
    def _date_window(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """
        Date/time comparison with window tolerance.
        
        Params:
            window_seconds: Allowed difference in seconds
        """
        if source_value is None and target_value is None:
            return True, None
        
        if source_value is None or target_value is None:
            return False, f"One value is null"
        
        window_seconds = params.get('window_seconds', 0)
        
        # Convert to datetime
        if isinstance(source_value, str):
            source_dt = datetime.fromisoformat(source_value)
        else:
            source_dt = source_value
        
        if isinstance(target_value, str):
            target_dt = datetime.fromisoformat(target_value)
        else:
            target_dt = target_value
        
        diff = abs((source_dt - target_dt).total_seconds())
        
        if diff <= window_seconds:
            return True, None
        else:
            return False, f"Time difference {diff}s exceeds window {window_seconds}s"
    
    def _case_insensitive(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """Case-insensitive string comparison"""
        
        if source_value is None and target_value is None:
            return True, None
        
        if source_value is None or target_value is None:
            return False, f"One value is null"
        
        source_str = str(source_value).lower()
        target_str = str(target_value).lower()
        
        if source_str == target_str:
            return True, None
        else:
            return False, f"{source_value} != {target_value} (case-insensitive)"
    
    def _regex(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """
        Regex pattern matching.
        
        Params:
            pattern: Regex pattern both values must match
        """
        pattern = params['pattern']
        
        if source_value is None and target_value is None:
            return True, None
        
        if source_value is None or target_value is None:
            return False, f"One value is null"
        
        source_str = str(source_value)
        target_str = str(target_value)
        
        source_match = re.match(pattern, source_str) is not None
        target_match = re.match(pattern, target_str) is not None
        
        if source_match and target_match:
            return True, None
        else:
            return False, f"Values don't both match pattern {pattern}"
    
    def _null_equals_empty(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """Treat null and empty string as equal"""
        
        # Normalize
        source_norm = source_value if source_value not in [None, ''] else None
        target_norm = target_value if target_value not in [None, ''] else None
        
        if source_norm == target_norm:
            return True, None
        else:
            return False, f"{source_value} != {target_value}"
    
    def _custom(self, source_value: Any, target_value: Any, params: Dict) -> Tuple[bool, Optional[str]]:
        """
        Custom comparison function.
        
        Params:
            function: Python function name or lambda
        """
        # Future: support custom comparison functions
        raise NotImplementedError("Custom comparators not yet implemented")
```

---

### 2.3 Discrepancy Detector

```python
# src/reconciliation/discrepancy_detector.py

from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from .matcher import MatchedPair
from .comparator import FieldComparator

logger = logging.getLogger(__name__)

@dataclass
class FieldDiscrepancy:
    """Represents a field-level discrepancy"""
    key: str  # Matching key
    field_id: str
    source_value: Any
    target_value: Any
    difference: str
    comparator_type: str
    severity: str = "ERROR"  # ERROR, WARNING

@dataclass
class RecordDiscrepancy:
    """Represents all discrepancies for a matched record"""
    key: str
    field_discrepancies: List[FieldDiscrepancy]
    source_metadata: Dict[str, Any]
    target_metadata: Dict[str, Any]

class DiscrepancyDetector:
    """
    Detects field-level discrepancies in matched record pairs.
    """
    
    def __init__(
        self,
        target_schema: Dict[str, Any],
        comparison_rules: List[Dict[str, Any]],
        comparator: FieldComparator
    ):
        """
        Args:
            target_schema: Target schema definition
            comparison_rules: Field-level comparison rules
            comparator: FieldComparator instance
        """
        self.target_schema = target_schema
        self.comparison_rules = comparison_rules
        self.comparator = comparator
        
        # Build lookup for comparison rules by field
        self.rules_by_field = {
            rule['target_field_id']: rule
            for rule in comparison_rules
            if rule.get('is_active', True)
        }
    
    def detect(
        self,
        matched_pairs: List[MatchedPair]
    ) -> List[RecordDiscrepancy]:
        """
        Detect discrepancies in matched pairs.
        
        Args:
            matched_pairs: List of matched source-target pairs
        
        Returns:
            List of RecordDiscrepancy (only for records with discrepancies)
        """
        record_discrepancies = []
        
        for pair in matched_pairs:
            field_discrepancies = self._compare_record_pair(pair)
            
            if field_discrepancies:
                record_discrepancies.append(RecordDiscrepancy(
                    key=pair.key,
                    field_discrepancies=field_discrepancies,
                    source_metadata=pair.source_row.metadata,
                    target_metadata=pair.target_row.metadata
                ))
        
        logger.info(
            f"Found discrepancies in {len(record_discrepancies)} of "
            f"{len(matched_pairs)} matched records"
        )
        
        return record_discrepancies
    
    def _compare_record_pair(self, pair: MatchedPair) -> List[FieldDiscrepancy]:
        """Compare all fields in a matched pair"""
        
        field_discrepancies = []
        
        # Get all target fields
        target_fields = self.target_schema['fields']
        
        for field_def in target_fields:
            field_id = field_def['field_id']
            
            # Check if field should be ignored
            rule = self.rules_by_field.get(field_id)
            if rule and rule.get('ignore_field', False):
                continue
            
            # Get comparison rule or use default
            comparator_type = 'EXACT'
            comparator_params = {}
            
            if rule:
                comparator_type = rule.get('comparator_type', 'EXACT')
                comparator_params = rule.get('comparator_params', {})
            
            # Get values
            source_value = pair.source_row.get_field(field_id)
            target_value = pair.target_row.get_field(field_id)
            
            # Compare
            try:
                values_match, difference = self.comparator.compare(
                    source_value=source_value,
                    target_value=target_value,
                    comparator_type=comparator_type,
                    params=comparator_params
                )
                
                if not values_match:
                    field_discrepancies.append(FieldDiscrepancy(
                        key=pair.key,
                        field_id=field_id,
                        source_value=source_value,
                        target_value=target_value,
                        difference=difference,
                        comparator_type=comparator_type,
                        severity="ERROR"
                    ))
            
            except Exception as e:
                logger.error(f"Comparison failed for field {field_id}: {str(e)}")
                field_discrepancies.append(FieldDiscrepancy(
                    key=pair.key,
                    field_id=field_id,
                    source_value=source_value,
                    target_value=target_value,
                    difference=f"Comparison error: {str(e)}",
                    comparator_type=comparator_type,
                    severity="WARNING"
                ))
        
        return field_discrepancies
```

---

### 2.4 Reconciliation Orchestrator

```python
# src/reconciliation/engine.py

from typing import Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
import logging

from ..connectors.base import CanonicalRow
from .matcher import RecordMatcher, MatchResult
from .comparator import FieldComparator
from .discrepancy_detector import DiscrepancyDetector, RecordDiscrepancy

logger = logging.getLogger(__name__)

@dataclass
class ReconciliationResult:
    """Complete reconciliation result"""
    rule_set_id: str
    match_result: MatchResult
    record_discrepancies: List[RecordDiscrepancy]
    summary_stats: Dict[str, Any]
    run_metadata: Dict[str, Any]

class ReconciliationEngine:
    """
    Main reconciliation engine that orchestrates matching and comparison.
    """
    
    def __init__(
        self,
        rule_set: Dict[str, Any],
        target_schema: Dict[str, Any],
        comparison_rules: List[Dict[str, Any]]
    ):
        """
        Args:
            rule_set: ReconciliationRuleSet metadata
            target_schema: Target schema definition
            comparison_rules: Field-level comparison rules
        """
        self.rule_set = rule_set
        self.target_schema = target_schema
        self.comparison_rules = comparison_rules
        
        # Initialize components
        self.matcher = RecordMatcher(rule_set)
        self.comparator = FieldComparator()
        self.detector = DiscrepancyDetector(
            target_schema=target_schema,
            comparison_rules=comparison_rules,
            comparator=self.comparator
        )
    
    def reconcile(
        self,
        source_rows: List[CanonicalRow],
        target_rows: List[CanonicalRow]
    ) -> ReconciliationResult:
        """
        Execute complete reconciliation.
        
        Args:
            source_rows: Transformed source rows (already mapped to target shape)
            target_rows: Actual target rows
        
        Returns:
            ReconciliationResult with complete findings
        """
        start_time = datetime.now()
        
        logger.info(
            f"Starting reconciliation: {len(source_rows)} source, "
            f"{len(target_rows)} target rows"
        )
        
        # Step 1: Match records
        match_result = self.matcher.match(source_rows, target_rows)
        
        # Step 2: Detect discrepancies in matched records
        record_discrepancies = self.detector.detect(match_result.matched_pairs)
        
        # Step 3: Calculate summary statistics
        summary_stats = self._calculate_summary_stats(
            match_result=match_result,
            record_discrepancies=record_discrepancies
        )
        
        # Run metadata
        run_metadata = {
            "rule_set_id": self.rule_set['rule_set_id'],
            "started_at": start_time.isoformat(),
            "completed_at": datetime.now().isoformat(),
            "duration_ms": (datetime.now() - start_time).total_seconds() * 1000
        }
        
        result = ReconciliationResult(
            rule_set_id=self.rule_set['rule_set_id'],
            match_result=match_result,
            record_discrepancies=record_discrepancies,
            summary_stats=summary_stats,
            run_metadata=run_metadata
        )
        
        logger.info(
            f"Reconciliation complete: {summary_stats['matched_with_no_discrepancy']} "
            f"perfect matches, {summary_stats['matched_with_discrepancy']} with discrepancies"
        )
        
        return result
    
    def _calculate_summary_stats(
        self,
        match_result: MatchResult,
        record_discrepancies: List[RecordDiscrepancy]
    ) -> Dict[str, Any]:
        """Calculate summary statistics"""
        
        total_matched = len(match_result.matched_pairs)
        matched_with_discrepancy = len(record_discrepancies)
        matched_with_no_discrepancy = total_matched - matched_with_discrepancy
        
        # Field-level discrepancy breakdown
        field_discrepancy_counts = {}
        total_field_discrepancies = 0
        
        for record_disc in record_discrepancies:
            for field_disc in record_disc.field_discrepancies:
                field_id = field_disc.field_id
                field_discrepancy_counts[field_id] = field_discrepancy_counts.get(field_id, 0) + 1
                total_field_discrepancies += 1
        
        stats = {
            "total_source_records": match_result.match_stats['total_source'],
            "total_target_records": match_result.match_stats['total_target'],
            "matched_records": total_matched,
            "matched_with_no_discrepancy": matched_with_no_discrepancy,
            "matched_with_discrepancy": matched_with_discrepancy,
            "unmatched_source_records": len(match_result.unmatched_source),
            "unmatched_target_records": len(match_result.unmatched_target),
            "total_field_discrepancies": total_field_discrepancies,
            "field_discrepancy_counts": field_discrepancy_counts,
            "match_rate_percent": match_result.match_stats['match_rate'],
            "accuracy_rate_percent": (matched_with_no_discrepancy / max(total_matched, 1)) * 100
        }
        
        return stats
```

---

## 3. Result Persistence

```python
# src/reconciliation/result_repository.py

from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime
import json

from .engine import ReconciliationResult

class ResultRepository:
    """
    Persists reconciliation results to database.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_result(self, result: ReconciliationResult) -> str:
        """
        Save reconciliation result.
        
        Returns:
            run_id
        """
        run_id = self._generate_run_id()
        
        # Insert run summary
        self._insert_run_summary(run_id, result)
        
        # Insert matched records
        self._insert_matched_records(run_id, result.match_result.matched_pairs)
        
        # Insert unmatched records
        self._insert_unmatched_records(run_id, result.match_result)
        
        # Insert discrepancies
        self._insert_discrepancies(run_id, result.record_discrepancies)
        
        self.db.commit()
        
        return run_id
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        return f"RUN_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    
    def _insert_run_summary(self, run_id: str, result: ReconciliationResult):
        """Insert into reconciliation_runs table"""
        
        query = """
        INSERT INTO reconciliation_runs (
            run_id, rule_set_id, status, started_at, completed_at,
            total_source_records, total_target_records,
            matched_records, matched_with_discrepancy,
            unmatched_source_records, unmatched_target_records,
            summary_stats, run_metadata
        ) VALUES (
            :run_id, :rule_set_id, :status, :started_at, :completed_at,
            :total_source, :total_target,
            :matched, :matched_with_disc,
            :unmatched_source, :unmatched_target,
            :summary_stats, :run_metadata
        )
        """
        
        self.db.execute(text(query), {
            "run_id": run_id,
            "rule_set_id": result.rule_set_id,
            "status": "COMPLETED",
            "started_at": result.run_metadata['started_at'],
            "completed_at": result.run_metadata['completed_at'],
            "total_source": result.summary_stats['total_source_records'],
            "total_target": result.summary_stats['total_target_records'],
            "matched": result.summary_stats['matched_records'],
            "matched_with_disc": result.summary_stats['matched_with_discrepancy'],
            "unmatched_source": result.summary_stats['unmatched_source_records'],
            "unmatched_target": result.summary_stats['unmatched_target_records'],
            "summary_stats": json.dumps(result.summary_stats),
            "run_metadata": json.dumps(result.run_metadata)
        })
    
    def _insert_discrepancies(self, run_id: str, discrepancies: List):
        """Insert into discrepancies table"""
        
        for record_disc in discrepancies:
            for field_disc in record_disc.field_discrepancies:
                query = """
                INSERT INTO discrepancies (
                    run_id, record_key, field_id,
                    source_value, target_value, difference,
                    comparator_type, severity, detected_at
                ) VALUES (
                    :run_id, :record_key, :field_id,
                    :source_value, :target_value, :difference,
                    :comparator_type, :severity, :detected_at
                )
                """
                
                self.db.execute(text(query), {
                    "run_id": run_id,
                    "record_key": field_disc.key,
                    "field_id": field_disc.field_id,
                    "source_value": str(field_disc.source_value),
                    "target_value": str(field_disc.target_value),
                    "difference": field_disc.difference,
                    "comparator_type": field_disc.comparator_type,
                    "severity": field_disc.severity,
                    "detected_at": datetime.now()
                })
```

---

**Document End**

*Next Document*: API Layer and Complete Test Plan

Let me know if you want me to continue with the API endpoints specification and comprehensive test plan!
