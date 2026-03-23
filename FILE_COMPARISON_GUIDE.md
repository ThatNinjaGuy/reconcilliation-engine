# File Comparison Guide (JSON & CSV)

This guide explains how to compare two JSON files or two CSV files using the GenRecon engine.

## Prerequisites

- Backend running: `uvicorn src.api.main:app --reload`
- Frontend running: `cd frontend && npm run dev`
- `RECON_ENCRYPTION_KEY` set (required for creating systems). Generate one:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  export RECON_ENCRYPTION_KEY="<paste-key>"
  ```

## Step 1: Create FILE System

Create a FILE system pointing to the directory containing your files.

**Via UI (Systems → Create System):**

- **System ID:** `file_local`
- **Name:** `Local Files`
- **Type:** `FILE`
- **Connection Config (JSON):** Replace the path with your absolute path to `sample_data`:
  ```json
  {
    "base_path": "/Users/deadshot/Desktop/Code/reconcilliation-engine/sample_data",
    "encoding": "utf-8"
  }
  ```
  On Windows use forward slashes: `"base_path": "C:/path/to/sample_data"`

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/systems \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "system_id": "file_local",
    "system_name": "Local Files",
    "system_type": "FILE",
    "connection_config": {
      "base_path": "/Users/deadshot/Desktop/Code/reconcilliation-engine/sample_data",
      "encoding": "utf-8"
    }
  }'
```

> **Note:** Use the absolute path to `sample_data` (or your folder). On Windows, use forward slashes, e.g. `"C:/data/files"`.

---

## Step 2: Create Schema

Define the logical schema for your records. Use `json_path` for JSON and `csv_column` for CSV.

### Schema for JSON files

**Schema ID:** `records_schema`
**Fields (JSON):**
```json
{
  "fields": [
    {
      "field_id": "id",
      "field_name": "id",
      "data_type": "STRING",
      "is_nullable": false,
      "is_key": true,
      "physical_mapping": {"json_path": "id"}
    },
    {
      "field_id": "name",
      "field_name": "name",
      "data_type": "STRING",
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"json_path": "name"}
    },
    {
      "field_id": "amount",
      "field_name": "amount",
      "data_type": "DECIMAL",
      "precision": 18,
      "scale": 2,
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"json_path": "amount"}
    },
    {
      "field_id": "status",
      "field_name": "status",
      "data_type": "STRING",
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"json_path": "status"}
    }
  ]
}
```

### Schema for CSV files

**Schema ID:** `csv_records_schema`
**Fields (JSON):**
```json
{
  "fields": [
    {
      "field_id": "id",
      "field_name": "id",
      "data_type": "STRING",
      "is_nullable": false,
      "is_key": true,
      "physical_mapping": {"csv_column": "id"}
    },
    {
      "field_id": "name",
      "field_name": "name",
      "data_type": "STRING",
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"csv_column": "name"}
    },
    {
      "field_id": "amount",
      "field_name": "amount",
      "data_type": "DECIMAL",
      "precision": 18,
      "scale": 2,
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"csv_column": "amount"}
    },
    {
      "field_id": "status",
      "field_name": "status",
      "data_type": "STRING",
      "is_nullable": true,
      "is_key": false,
      "physical_mapping": {"csv_column": "status"}
    }
  ]
}
```

---

## Step 3: Create Datasets

Create source and target datasets.

### JSON Datasets

- **Source Dataset ID:** `json_source`  
  - System ID: `file_local`  
  - Schema ID: `records_schema`  
  - Physical Name: `source.json`  
  - Dataset Type: `FILE`  

- **Target Dataset ID:** `json_target`  
  - System ID: `file_local`  
  - Schema ID: `records_schema`  
  - Physical Name: `target.json`  
  - Dataset Type: `FILE`  

### CSV Datasets

- **Source Dataset ID:** `csv_source`  
  - System ID: `file_local`  
  - Schema ID: `csv_records_schema`  
  - Physical Name: `source.csv`  
  - Dataset Type: `FILE`  

- **Target Dataset ID:** `csv_target`  
  - System ID: `file_local`  
  - Schema ID: `csv_records_schema`  
  - Physical Name: `target.csv`  
  - Dataset Type: `FILE`  

---

## Step 4: Create Mapping

Create a mapping from source schema to target schema (1:1 for same structure).

- **Mapping ID:** `file_mapping`
- **Name:** `File to File Mapping`
- **Source Schema ID:** `records_schema` (or `csv_records_schema`)
- **Target Schema ID:** `records_schema` (or `csv_records_schema`)

---

## Step 5: Add Field Mappings

Add field mappings (direct copy). For each target field:

| Target Field ID | Source Expression |
|-----------------|-------------------|
| id              | id                |
| name            | name              |
| amount          | amount            |
| status          | status            |

Use "Add Field Mapping" for each, with `source_expression` set to the same field id.

---

## Step 6: Create Rule Set

- **Rule Set ID:** `json_recon` (or `csv_recon`)
- **Name:** `JSON File Reconciliation` (or `CSV File Reconciliation`)
- **Source Dataset ID:** `json_source` (or `csv_source`)
- **Target Dataset ID:** `json_target` (or `csv_target`)
- **Mapping ID:** `file_mapping`
- **Matching Keys (JSON):**
  ```json
  {
    "keys": [
      {
        "source_field": "id",
        "target_field": "id",
        "is_case_sensitive": true
      }
    ]
  }
  ```

---

## Step 7: Add Comparison Rules (Optional)

To allow tolerance for numeric fields (e.g. `amount`):

- **Rule Set ID:** `json_recon`
- **Target Field ID:** `amount`
- **Comparator Type:** `NUMERIC_TOLERANCE`
- **Comparator Params (JSON):**
  ```json
  {"tolerance": 0.01, "tolerance_type": "ABSOLUTE"}
  ```

---

## Step 8: Run Reconciliation Job

- **Rule Set ID:** `json_recon` or `csv_recon`
- Click **Create Job**

Poll job status, then fetch results.

---

## Expected Results for Sample Data

With the provided `sample_data` files:

- **Matched:** id 1 (identical), id 2 (amount diff), id 3 (name diff)
- **Unmatched source:** id 4 (Dave)
- **Unmatched target:** id 5 (Eve)
- **Discrepancies:** id 2 (amount), id 3 (name)

---

## Composite Key Scenario (2+ Columns as Unique Key)

This section shows how to test matching when the unique key is a **combination of columns**.

### Sample files

Use these files in `sample_data/`:

- `composite_source.csv`
- `composite_target.csv`

Both files use:

- `company_id`
- `invoice_id`

as the composite key.

### 1) Create System

- **System ID:** `file_local_composite`
- **Name:** `Local Files Composite`
- **Type:** `FILE`
- **Connection Config:**
  ```json
  {
    "base_path": "/Users/deadshot/Desktop/Code/reconcilliation-engine/sample_data",
    "encoding": "utf-8"
  }
  ```

### 2) Create Schema

- **Schema ID:** `composite_csv_schema`
- **Schema Name:** `Composite CSV Schema`
- **Fields:** (`company_id` and `invoice_id` must be `is_key: true`)
  ```json
  {
    "fields": [
      {
        "field_id": "company_id",
        "field_name": "company_id",
        "data_type": "STRING",
        "is_nullable": false,
        "is_key": true,
        "physical_mapping": {"csv_column": "company_id"}
      },
      {
        "field_id": "invoice_id",
        "field_name": "invoice_id",
        "data_type": "STRING",
        "is_nullable": false,
        "is_key": true,
        "physical_mapping": {"csv_column": "invoice_id"}
      },
      {
        "field_id": "customer",
        "field_name": "customer",
        "data_type": "STRING",
        "is_nullable": true,
        "is_key": false,
        "physical_mapping": {"csv_column": "customer"}
      },
      {
        "field_id": "amount",
        "field_name": "amount",
        "data_type": "DECIMAL",
        "precision": 18,
        "scale": 2,
        "is_nullable": true,
        "is_key": false,
        "physical_mapping": {"csv_column": "amount"}
      },
      {
        "field_id": "status",
        "field_name": "status",
        "data_type": "STRING",
        "is_nullable": true,
        "is_key": false,
        "physical_mapping": {"csv_column": "status"}
      }
    ]
  }
  ```

### 3) Create Datasets

- **Source Dataset**
  - Dataset ID: `composite_source_ds`
  - System ID: `file_local_composite`
  - Schema ID: `composite_csv_schema`
  - Physical Name: `composite_source.csv`
  - Dataset Type: `FILE`

- **Target Dataset**
  - Dataset ID: `composite_target_ds`
  - System ID: `file_local_composite`
  - Schema ID: `composite_csv_schema`
  - Physical Name: `composite_target.csv`
  - Dataset Type: `FILE`

### 4) Create Mapping

- **Mapping ID:** `composite_mapping`
- **Name:** `Composite Mapping`
- **Source Schema ID:** `composite_csv_schema`
- **Target Schema ID:** `composite_csv_schema`

Field mappings (1:1):

| Target Field ID | Source Expression |
|-----------------|-------------------|
| company_id      | company_id        |
| invoice_id      | invoice_id        |
| customer        | customer          |
| amount          | amount            |
| status          | status            |

### 5) Create Rule Set (Composite Keys)

- **Rule Set ID:** `composite_recon`
- **Name:** `Composite Key Reconciliation`
- **Source Dataset ID:** `composite_source_ds`
- **Target Dataset ID:** `composite_target_ds`
- **Mapping ID:** `composite_mapping`
- **Matching Keys:**
  ```json
  {
    "keys": [
      {
        "source_field": "company_id",
        "target_field": "company_id",
        "is_case_sensitive": true
      },
      {
        "source_field": "invoice_id",
        "target_field": "invoice_id",
        "is_case_sensitive": true
      }
    ],
    "key_normalization": {
      "trim_whitespace": true
    }
  }
  ```

### 6) Optional Comparison Rules

Add `EXACT` comparison rules for:

- `customer`
- `amount`
- `status`

### Expected Output (Composite Test)

For the supplied composite files, expected highlights:

- **Matched with discrepancies:** `C01|INV-1002`, `C02|INV-1002`, `C04|INV-1001`
- **Unmatched source:** `C04|INV-1002`
- **Unmatched target:** `C05|INV-1001`

This validates that matching is done on the **combined key** (`company_id + invoice_id`), not on either column alone.

---

## Quick Test via API

```bash
# 1. Create system (after setting RECON_ENCRYPTION_KEY)
# 2. Create schema
# 3. Create datasets
# 4. Create mapping + field mappings
# 5. Create rule set
# 6. Create job

curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"rule_set_id": "json_recon"}'

# Get job ID from response, then:
curl http://localhost:8000/api/v1/jobs/JOB_xxx
curl http://localhost:8000/api/v1/results/JOB_xxx/summary
curl "http://localhost:8000/api/v1/results/JOB_xxx/discrepancies?limit=50"
```

---

## Order-Independence and Case Handling

The reconciliation engine is **order-independent** across all connectors (FILE, Oracle, MongoDB, API):

| Aspect | Behavior | Notes |
|--------|----------|-------|
| **Row order** | Records are matched by key values, not position. | CSV rows, JSON array elements, Oracle/MongoDB result rows can appear in any order. |
| **Column order (CSV)** | Columns are looked up by header name. | Column order in source vs target does not matter. |
| **JSON key order** | JSON keys are accessed by name. | Key order in objects is irrelevant. |
| **Composite matching keys** | Keys are combined into a deterministic composite string. | Field order in schema only affects reporting, not matching. |

### Case-Insensitive Lookup (FILE connector)

When source and target files use different casing (e.g. `ID` vs `id`, `Customer_Name` vs `customer_name`), enable case-insensitive lookup in the dataset **filter_config**:

```json
{
  "filter_config": {
    "case_insensitive_lookup": true
  }
}
```

This applies to both JSON keys (via `json_path`) and CSV column headers (via `csv_column`).

### Key Normalization (Rule Set)

To treat matching keys as equal despite whitespace or casing differences:

- Set `is_case_sensitive: false` on a matching key to compare keys case-insensitively.
- Set `key_normalization.trim_whitespace: true` in the rule set's matching config to trim leading/trailing whitespace when building matching keys:

```json
{
  "matching_keys": [
    {"source_field": "id", "target_field": "id", "is_case_sensitive": false}
  ],
  "key_normalization": {"trim_whitespace": true}
}
```

---

## Physical Mapping Reference

| File Type | physical_mapping    | Example                          |
|-----------|---------------------|----------------------------------|
| JSON      | `json_path`         | `{"json_path": "nested.field"}`  |
| CSV       | `csv_column`        | `{"csv_column": "Column Name"}`  |

For JSON arrays of objects, each object is a row. For a JSON object with an array under a key, set `array_key` in connection_config, e.g. `{"base_path": "...", "array_key": "records"}`.

**filter_config** (per-dataset): `delimiter`, `has_header` (CSV), `case_insensitive_lookup` (CSV/JSON).
