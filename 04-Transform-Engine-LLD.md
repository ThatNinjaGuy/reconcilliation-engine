# Transformation Engine - Detailed Design Document

**Component**: Transformation & Mapping Engine  
**Version**: 1.0  
**Date**: January 30, 2026  
**Dependencies**: Pandas, NumPy

---

## 1. Component Overview

The Transformation Engine applies metadata-defined field mappings to convert source data (Oracle rows) into target-shaped data (MongoDB document structure) before reconciliation. It executes transformation chains, reference lookups, and validations.

**Key Responsibilities**:
- Interpret mapping metadata
- Execute transformation chains (multi-step field derivations)
- Perform reference dataset lookups
- Apply pre/post-transform validations
- Handle errors and logging

---

## 2. Architecture

```
┌─────────────────────────────────────────────┐
│         MappingInterpreter                  │
│  - Loads mapping metadata                   │
│  - Orchestrates transformation per field    │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        │           │           │
┌───────▼──────┐ ┌──▼────────┐ ┌▼────────────┐
│ Transform    │ │Reference  │ │ Validation  │
│ Registry     │ │Data Mgr   │ │ Engine      │
└──────────────┘ └───────────┘ └─────────────┘
```

---

## 3. Core Classes

### 3.1 Mapping Interpreter

```python
# src/transformation/mapping_interpreter.py

from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging
from datetime import datetime

from ..connectors.base import CanonicalRow
from .transform_registry import TransformRegistry
from .reference_manager import ReferenceDatasetManager
from .validators import ValidationEngine

logger = logging.getLogger(__name__)

class TransformationContext:
    """
    Context object passed through transformation chain.
    Contains source data, intermediate results, and reference handles.
    """
    
    def __init__(
        self,
        source_row: CanonicalRow,
        reference_manager: ReferenceDatasetManager
    ):
        self.source_row = source_row
        self.reference_manager = reference_manager
        self.derived_fields = {}  # Intermediate computed fields
        self.errors = []
        self.warnings = []
    
    def get_source_field(self, field_id: str, default: Any = None) -> Any:
        """Get value from source row"""
        return self.source_row.get_field(field_id, default)
    
    def set_derived_field(self, field_id: str, value: Any):
        """Store intermediate derived field"""
        self.derived_fields[field_id] = value
    
    def get_derived_field(self, field_id: str, default: Any = None) -> Any:
        """Get previously derived field"""
        return self.derived_fields.get(field_id, default)
    
    def add_error(self, field_id: str, message: str):
        """Record transformation error"""
        self.errors.append({
            "field": field_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_warning(self, field_id: str, message: str):
        """Record transformation warning"""
        self.warnings.append({
            "field": field_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

class MappingInterpreter:
    """
    Interprets mapping metadata and applies transformations to convert
    source rows to target-shaped rows.
    """
    
    def __init__(
        self,
        mapping: Dict[str, Any],
        field_mappings: List[Dict[str, Any]],
        reference_manager: ReferenceDatasetManager,
        transform_registry: TransformRegistry,
        validation_engine: ValidationEngine
    ):
        self.mapping = mapping
        self.field_mappings = field_mappings
        self.reference_manager = reference_manager
        self.transform_registry = transform_registry
        self.validation_engine = validation_engine
    
    def transform_row(self, source_row: CanonicalRow) -> CanonicalRow:
        """
        Transform single source row to target shape.
        
        Args:
            source_row: Source CanonicalRow
        
        Returns:
            Target-shaped CanonicalRow
        """
        context = TransformationContext(source_row, self.reference_manager)
        target_fields = {}
        
        # Process each field mapping
        for field_mapping in self.field_mappings:
            if not field_mapping.get('is_active', True):
                continue
            
            target_field_id = field_mapping['target_field_id']
            
            try:
                # Apply transformation
                value = self._apply_field_mapping(field_mapping, context)
                target_fields[target_field_id] = value
                
            except Exception as e:
                logger.error(f"Transform failed for {target_field_id}: {str(e)}")
                context.add_error(target_field_id, str(e))
                target_fields[target_field_id] = None
        
        # Create target row
        target_row = CanonicalRow(
            fields=target_fields,
            metadata={
                "source_metadata": source_row.metadata,
                "transformation_errors": context.errors,
                "transformation_warnings": context.warnings,
                "transformed_at": datetime.now().isoformat()
            }
        )
        
        return target_row
    
    def _apply_field_mapping(
        self,
        field_mapping: Dict[str, Any],
        context: TransformationContext
    ) -> Any:
        """Apply single field mapping transformation"""
        
        target_field_id = field_mapping['target_field_id']
        
        # Step 1: Pre-transform validations
        if field_mapping.get('pre_validations'):
            self._run_validations(
                field_mapping['pre_validations'],
                context,
                target_field_id,
                phase='pre'
            )
        
        # Step 2: Apply transformation
        value = None
        
        # Simple expression
        if field_mapping.get('source_expression'):
            value = self._evaluate_expression(
                field_mapping['source_expression'],
                context
            )
        
        # Transform chain
        elif field_mapping.get('transform_chain'):
            value = self._apply_transform_chain(
                field_mapping['transform_chain'],
                context
            )
        
        # Step 3: Post-transform validations
        if field_mapping.get('post_validations'):
            self._run_validations(
                field_mapping['post_validations'],
                context,
                target_field_id,
                phase='post',
                value=value
            )
        
        return value
    
    def _evaluate_expression(
        self,
        expression: str,
        context: TransformationContext
    ) -> Any:
        """
        Evaluate simple expression like "FIRST_NAME" or "AMOUNT * 1.1"
        
        For safety, only allow field references and basic math.
        """
        # Simple case: direct field reference
        if expression.isidentifier():
            return context.get_source_field(expression)
        
        # For complex expressions, use safe eval (implement carefully)
        # For now, just support direct field access
        return context.get_source_field(expression)
    
    def _apply_transform_chain(
        self,
        transform_chain: Dict[str, Any],
        context: TransformationContext
    ) -> Any:
        """
        Apply ordered sequence of transformations.
        
        Each step's output becomes input to next step.
        """
        steps = transform_chain.get('steps', [])
        
        # Sort by step_order
        steps = sorted(steps, key=lambda s: s.get('step_order', 0))
        
        value = None
        
        for step in steps:
            transform_type = step['transform_type']
            params = step.get('params', {})
            
            # Execute transform
            value = self.transform_registry.execute(
                transform_type=transform_type,
                params=params,
                context=context,
                previous_value=value
            )
        
        return value
    
    def _run_validations(
        self,
        validations: List[Dict[str, Any]],
        context: TransformationContext,
        field_id: str,
        phase: str,
        value: Any = None
    ):
        """Run validation rules"""
        
        for validation in validations:
            validation_type = validation['validation_type']
            params = validation.get('params', {})
            error_action = validation.get('error_action', 'FAIL')
            
            is_valid, message = self.validation_engine.validate(
                validation_type=validation_type,
                params=params,
                context=context,
                value=value
            )
            
            if not is_valid:
                if error_action == 'FAIL':
                    raise ValueError(f"{phase}-validation failed for {field_id}: {message}")
                elif error_action == 'WARN':
                    context.add_warning(field_id, message)
                # SKIP: do nothing
    
    def transform_batch(
        self,
        source_rows: List[CanonicalRow]
    ) -> List[CanonicalRow]:
        """
        Transform batch of rows.
        
        Can be parallelized in future for performance.
        """
        target_rows = []
        
        for source_row in source_rows:
            target_row = self.transform_row(source_row)
            target_rows.append(target_row)
        
        return target_rows
```

---

## 4. Transform Registry

### 4.1 Built-in Transforms

```python
# src/transformation/transform_registry.py

from typing import Any, Dict, Callable, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import re
import logging

logger = logging.getLogger(__name__)

class TransformRegistry:
    """
    Registry of transformation functions.
    
    Each transform is a function with signature:
    def transform(params: Dict, context: TransformationContext, previous_value: Any) -> Any
    """
    
    def __init__(self):
        self._transforms = {}
        self._register_builtin_transforms()
    
    def register(self, name: str, func: Callable):
        """Register a transform function"""
        self._transforms[name] = func
        logger.info(f"Registered transform: {name}")
    
    def execute(
        self,
        transform_type: str,
        params: Dict[str, Any],
        context: 'TransformationContext',
        previous_value: Any = None
    ) -> Any:
        """Execute a transform"""
        
        if transform_type not in self._transforms:
            raise ValueError(f"Unknown transform type: {transform_type}")
        
        func = self._transforms[transform_type]
        return func(params, context, previous_value)
    
    def _register_builtin_transforms(self):
        """Register all built-in transforms"""
        
        # String operations
        self.register('direct', self._direct)
        self.register('concat', self._concat)
        self.register('substring', self._substring)
        self.register('upper_case', self._upper_case)
        self.register('lower_case', self._lower_case)
        self.register('trim', self._trim)
        self.register('replace', self._replace)
        
        # Math operations
        self.register('add', self._add)
        self.register('subtract', self._subtract)
        self.register('multiply', self._multiply)
        self.register('divide', self._divide)
        self.register('round', self._round)
        
        # Date operations
        self.register('parse_date', self._parse_date)
        self.register('format_date', self._format_date)
        self.register('date_diff', self._date_diff)
        self.register('date_add', self._date_add)
        
        # Reference lookups
        self.register('lookup', self._lookup)
        
        # Conditional
        self.register('conditional', self._conditional)
        
        # Type conversion
        self.register('to_string', self._to_string)
        self.register('to_int', self._to_int)
        self.register('to_decimal', self._to_decimal)
    
    # String Transforms
    
    def _direct(self, params: Dict, context, previous_value) -> Any:
        """Direct field copy"""
        source_field = params['source_field']
        return context.get_source_field(source_field)
    
    def _concat(self, params: Dict, context, previous_value) -> str:
        """
        Concatenate multiple fields.
        
        Params:
            source_fields: List of field IDs
            separator: String separator (default: "")
            trim: Boolean, trim each field before concat
        """
        source_fields = params['source_fields']
        separator = params.get('separator', '')
        trim = params.get('trim', False)
        
        values = []
        for field in source_fields:
            value = context.get_source_field(field)
            if value is not None:
                value_str = str(value)
                if trim:
                    value_str = value_str.strip()
                values.append(value_str)
        
        return separator.join(values)
    
    def _substring(self, params: Dict, context, previous_value) -> str:
        """
        Extract substring.
        
        Params:
            source_field: Field ID (or uses previous_value if not specified)
            start: Start index (0-based)
            length: Length (optional, to end if not specified)
        """
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        if value is None:
            return None
        
        value_str = str(value)
        start = params.get('start', 0)
        length = params.get('length')
        
        if length:
            return value_str[start:start+length]
        else:
            return value_str[start:]
    
    def _upper_case(self, params: Dict, context, previous_value) -> str:
        """Convert to uppercase"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return str(value).upper() if value is not None else None
    
    def _lower_case(self, params: Dict, context, previous_value) -> str:
        """Convert to lowercase"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return str(value).lower() if value is not None else None
    
    def _trim(self, params: Dict, context, previous_value) -> str:
        """Trim whitespace"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return str(value).strip() if value is not None else None
    
    def _replace(self, params: Dict, context, previous_value) -> str:
        """
        Replace text.
        
        Params:
            source_field: Field ID
            pattern: String or regex pattern
            replacement: Replacement string
            is_regex: Boolean (default: False)
        """
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        if value is None:
            return None
        
        value_str = str(value)
        pattern = params['pattern']
        replacement = params['replacement']
        is_regex = params.get('is_regex', False)
        
        if is_regex:
            return re.sub(pattern, replacement, value_str)
        else:
            return value_str.replace(pattern, replacement)
    
    # Math Transforms
    
    def _add(self, params: Dict, context, previous_value) -> Decimal:
        """Add two numbers"""
        left = params.get('left_field')
        right = params.get('right_field')
        
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get('value', 0)))
        
        return left_val + right_val
    
    def _subtract(self, params: Dict, context, previous_value) -> Decimal:
        """Subtract two numbers"""
        left = params.get('left_field')
        right = params.get('right_field')
        
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get('value', 0)))
        
        return left_val - right_val
    
    def _multiply(self, params: Dict, context, previous_value) -> Decimal:
        """Multiply two numbers"""
        left = params.get('left_field')
        right = params.get('right_field')
        
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get('value', 1)))
        
        return left_val * right_val
    
    def _divide(self, params: Dict, context, previous_value) -> Decimal:
        """Divide two numbers"""
        left = params.get('left_field')
        right = params.get('right_field')
        
        left_val = Decimal(str(context.get_source_field(left))) if left else Decimal(str(previous_value))
        right_val = Decimal(str(context.get_source_field(right))) if right else Decimal(str(params.get('value', 1)))
        
        if right_val == 0:
            raise ValueError("Division by zero")
        
        return left_val / right_val
    
    def _round(self, params: Dict, context, previous_value) -> Decimal:
        """Round number"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        decimals = params.get('decimals', 0)
        return round(Decimal(str(value)), decimals)
    
    # Date Transforms
    
    def _parse_date(self, params: Dict, context, previous_value) -> datetime:
        """
        Parse string to datetime.
        
        Params:
            source_field: Field ID
            format: Date format string (e.g., "%Y-%m-%d")
        """
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        if value is None:
            return None
        
        format_str = params.get('format', '%Y-%m-%d')
        
        if isinstance(value, datetime):
            return value
        
        return datetime.strptime(str(value), format_str)
    
    def _format_date(self, params: Dict, context, previous_value) -> str:
        """Format datetime to string"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        if value is None:
            return None
        
        format_str = params.get('format', '%Y-%m-%d')
        
        if isinstance(value, str):
            # Parse first
            value = datetime.fromisoformat(value)
        
        return value.strftime(format_str)
    
    def _date_diff(self, params: Dict, context, previous_value) -> int:
        """
        Calculate difference between two dates in days.
        
        Params:
            date1_field, date2_field: Field IDs
            unit: 'days', 'hours', 'minutes' (default: days)
        """
        date1 = context.get_source_field(params['date1_field'])
        date2 = context.get_source_field(params['date2_field'])
        
        if isinstance(date1, str):
            date1 = datetime.fromisoformat(date1)
        if isinstance(date2, str):
            date2 = datetime.fromisoformat(date2)
        
        diff = date2 - date1
        
        unit = params.get('unit', 'days')
        if unit == 'days':
            return diff.days
        elif unit == 'hours':
            return int(diff.total_seconds() / 3600)
        elif unit == 'minutes':
            return int(diff.total_seconds() / 60)
        else:
            return diff.days
    
    def _date_add(self, params: Dict, context, previous_value) -> datetime:
        """
        Add/subtract time to date.
        
        Params:
            source_field: Field ID
            days, hours, minutes: Amount to add (can be negative)
        """
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        
        delta = timedelta(
            days=params.get('days', 0),
            hours=params.get('hours', 0),
            minutes=params.get('minutes', 0)
        )
        
        return value + delta
    
    # Reference Lookup
    
    def _lookup(self, params: Dict, context, previous_value) -> Any:
        """
        Lookup value from reference dataset.
        
        Params:
            reference_dataset: Reference dataset ID
            source_field: Field ID containing lookup key
            ref_key_field: Key field in reference dataset
            ref_value_field: Value field to return
            default: Default value if not found
        """
        reference_dataset_id = params['reference_dataset']
        source_field = params['source_field']
        ref_key_field = params['ref_key_field']
        ref_value_field = params['ref_value_field']
        default = params.get('default')
        
        # Get lookup key from source
        lookup_key = context.get_source_field(source_field)
        
        if lookup_key is None:
            return default
        
        # Get reference dataset
        ref_data = context.reference_manager.get(reference_dataset_id)
        
        # Perform lookup
        result = ref_data.lookup(
            key_field=ref_key_field,
            key_value=lookup_key,
            value_field=ref_value_field
        )
        
        return result if result is not None else default
    
    # Conditional
    
    def _conditional(self, params: Dict, context, previous_value) -> Any:
        """
        If-then-else logic.
        
        Params:
            condition_field: Field to check
            operator: 'equals', 'not_equals', 'greater_than', 'less_than', 'contains'
            compare_value: Value to compare against
            true_value: Value if condition true
            false_value: Value if condition false
        """
        condition_field = params['condition_field']
        operator = params['operator']
        compare_value = params['compare_value']
        true_value = params['true_value']
        false_value = params['false_value']
        
        field_value = context.get_source_field(condition_field)
        
        condition_met = False
        
        if operator == 'equals':
            condition_met = (field_value == compare_value)
        elif operator == 'not_equals':
            condition_met = (field_value != compare_value)
        elif operator == 'greater_than':
            condition_met = (field_value > compare_value)
        elif operator == 'less_than':
            condition_met = (field_value < compare_value)
        elif operator == 'contains':
            condition_met = (compare_value in str(field_value))
        
        return true_value if condition_met else false_value
    
    # Type Conversion
    
    def _to_string(self, params: Dict, context, previous_value) -> str:
        """Convert to string"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return str(value) if value is not None else None
    
    def _to_int(self, params: Dict, context, previous_value) -> int:
        """Convert to integer"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return int(value) if value is not None else None
    
    def _to_decimal(self, params: Dict, context, previous_value) -> Decimal:
        """Convert to Decimal"""
        if 'source_field' in params:
            value = context.get_source_field(params['source_field'])
        else:
            value = previous_value
        
        return Decimal(str(value)) if value is not None else None
```

---

## 5. Reference Dataset Manager

```python
# src/transformation/reference_manager.py

from typing import Dict, Any, Optional
import pandas as pd
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReferenceHandle:
    """
    Handle to a loaded reference dataset.
    Provides lookup operations.
    """
    
    def __init__(self, data: pd.DataFrame, reference_id: str):
        self.data = data
        self.reference_id = reference_id
        self._index_cache = {}
    
    def lookup(
        self,
        key_field: str,
        key_value: Any,
        value_field: str
    ) -> Optional[Any]:
        """
        Lookup value by key.
        
        Args:
            key_field: Column name for lookup key
            key_value: Value to search for
            value_field: Column name to return
        
        Returns:
            Matched value or None
        """
        # Create index if not cached
        cache_key = key_field
        if cache_key not in self._index_cache:
            self._index_cache[cache_key] = self.data.set_index(key_field)[value_field].to_dict()
        
        return self._index_cache[cache_key].get(key_value)
    
    def lookup_multiple(
        self,
        key_field: str,
        key_values: list,
        value_field: str
    ) -> Dict[Any, Any]:
        """Batch lookup for multiple keys"""
        results = {}
        for key in key_values:
            results[key] = self.lookup(key_field, key, value_field)
        return results

class ReferenceDatasetManager:
    """
    Manages loading and caching of reference datasets.
    """
    
    def __init__(self):
        self._cache = {}
        self._metadata = {}
    
    def load(
        self,
        reference_dataset_id: str,
        reference_config: Dict[str, Any]
    ) -> ReferenceHandle:
        """
        Load reference dataset.
        Caches in memory for reuse within job run.
        
        Args:
            reference_dataset_id: Reference dataset ID
            reference_config: Configuration from metadata
        
        Returns:
            ReferenceHandle for lookups
        """
        # Check cache
        if reference_dataset_id in self._cache:
            logger.debug(f"Using cached reference dataset: {reference_dataset_id}")
            return self._cache[reference_dataset_id]
        
        # Load based on source type
        source_type = reference_config['source_type']
        source_config = reference_config['source_config']
        
        logger.info(f"Loading reference dataset: {reference_dataset_id} from {source_type}")
        
        if source_type == 'CSV':
            data = self._load_from_csv(source_config)
        elif source_type == 'ORACLE':
            data = self._load_from_oracle(source_config)
        elif source_type == 'MONGODB':
            data = self._load_from_mongodb(source_config)
        elif source_type == 'INLINE':
            data = self._load_from_inline(source_config)
        else:
            raise ValueError(f"Unsupported reference source type: {source_type}")
        
        # Create handle
        handle = ReferenceHandle(data, reference_dataset_id)
        
        # Cache
        self._cache[reference_dataset_id] = handle
        self._metadata[reference_dataset_id] = {
            "loaded_at": datetime.now().isoformat(),
            "row_count": len(data)
        }
        
        logger.info(f"Loaded {len(data)} rows for {reference_dataset_id}")
        
        return handle
    
    def _load_from_csv(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load from CSV file"""
        file_path = config['file_path']
        delimiter = config.get('delimiter', ',')
        has_header = config.get('has_header', True)
        encoding = config.get('encoding', 'UTF-8')
        
        header = 0 if has_header else None
        
        data = pd.read_csv(
            file_path,
            delimiter=delimiter,
            header=header,
            encoding=encoding
        )
        
        return data
    
    def _load_from_oracle(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load from Oracle query"""
        # Use connector to execute query
        from ..connectors.factory import ConnectorFactory
        from ..metadata.repositories import SystemRepository
        
        system_id = config['system_id']
        query = config['query']
        
        # Get system config (would normally inject dependencies)
        # For now, simplified
        
        # Execute query and return as DataFrame
        # Implementation depends on your connector setup
        pass
    
    def _load_from_mongodb(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load from MongoDB query"""
        # Similar to Oracle
        pass
    
    def _load_from_inline(self, config: Dict[str, Any]) -> pd.DataFrame:
        """Load from inline JSON data"""
        data = config['data']
        return pd.DataFrame(data)
    
    def get(self, reference_dataset_id: str) -> ReferenceHandle:
        """Get cached reference dataset"""
        if reference_dataset_id not in self._cache:
            raise ValueError(f"Reference dataset not loaded: {reference_dataset_id}")
        
        return self._cache[reference_dataset_id]
    
    def clear_cache(self):
        """Clear all cached reference datasets"""
        self._cache.clear()
        self._metadata.clear()
        logger.info("Cleared reference dataset cache")
```

---

## 6. Validation Engine

```python
# src/transformation/validators.py

from typing import Dict, Any, Tuple
import re
from datetime import datetime

class ValidationEngine:
    """
    Executes validation rules on field values.
    """
    
    def __init__(self):
        self._validators = {}
        self._register_builtin_validators()
    
    def register(self, name: str, func):
        """Register custom validator"""
        self._validators[name] = func
    
    def validate(
        self,
        validation_type: str,
        params: Dict[str, Any],
        context: 'TransformationContext',
        value: Any = None
    ) -> Tuple[bool, str]:
        """
        Execute validation.
        
        Returns:
            (is_valid, message)
        """
        if validation_type not in self._validators:
            raise ValueError(f"Unknown validation type: {validation_type}")
        
        func = self._validators[validation_type]
        return func(params, context, value)
    
    def _register_builtin_validators(self):
        """Register built-in validators"""
        
        self.register('not_null', self._not_null)
        self.register('max_length', self._max_length)
        self.register('min_length', self._min_length)
        self.register('regex', self._regex)
        self.register('range', self._range)
        self.register('in_list', self._in_list)
    
    def _not_null(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate fields are not null"""
        fields = params.get('fields', [])
        
        for field in fields:
            field_value = context.get_source_field(field)
            if field_value is None:
                return False, f"Field {field} is null"
        
        return True, "OK"
    
    def _max_length(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate string max length"""
        max_len = params['length']
        
        if value is None:
            return True, "OK"
        
        if len(str(value)) > max_len:
            return False, f"Length {len(str(value))} exceeds max {max_len}"
        
        return True, "OK"
    
    def _min_length(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate string min length"""
        min_len = params['length']
        
        if value is None:
            return True, "OK"
        
        if len(str(value)) < min_len:
            return False, f"Length {len(str(value))} below min {min_len}"
        
        return True, "OK"
    
    def _regex(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate against regex pattern"""
        pattern = params['pattern']
        
        if value is None:
            return True, "OK"
        
        if not re.match(pattern, str(value)):
            return False, f"Value does not match pattern {pattern}"
        
        return True, "OK"
    
    def _range(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate numeric range"""
        min_val = params.get('min')
        max_val = params.get('max')
        
        if value is None:
            return True, "OK"
        
        numeric_value = float(value)
        
        if min_val is not None and numeric_value < min_val:
            return False, f"Value {numeric_value} below min {min_val}"
        
        if max_val is not None and numeric_value > max_val:
            return False, f"Value {numeric_value} above max {max_val}"
        
        return True, "OK"
    
    def _in_list(self, params: Dict, context, value) -> Tuple[bool, str]:
        """Validate value in allowed list"""
        allowed_values = params['values']
        
        if value is None:
            return True, "OK"
        
        if value not in allowed_values:
            return False, f"Value {value} not in allowed list"
        
        return True, "OK"
```

---

**Document End**

*Next Component*: Reconciliation Engine Design

Let me know if you'd like me to continue with the remaining components (Reconciliation Engine, Orchestration Layer, API Layer, and Test Plan)!
