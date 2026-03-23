export function DocsSchemas() {
  return (
    <div className="page">
      <div className="card">
        <h3>Schemas</h3>
        <p className="muted">
          Schema is your common vocabulary. It standardizes field meaning across systems.
          This is why reconciliation can compare CSV column `INV_ID` to Oracle column `INVOICE_NO`.
        </p>
        <p className="muted">Allowed `data_type`: STRING, INTEGER, DECIMAL, BOOLEAN, DATE, TIMESTAMP, ARRAY, OBJECT.</p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td className="mono">schema_id</td><td>Yes</td><td>Unique schema key.</td></tr>
              <tr><td className="mono">schema_name</td><td>Yes</td><td>Display name.</td></tr>
              <tr><td className="mono">description</td><td>No</td><td>Business context for future maintainers.</td></tr>
              <tr><td className="mono">fields</td><td>Yes</td><td>Field definitions with `physical_mapping`.</td></tr>
              <tr><td className="mono">constraints</td><td>No</td><td>Optional custom constraints object.</td></tr>
            </tbody>
          </table>
        </div>
        <pre className="codeblock">{`{
  "schema_id": "invoice_schema",
  "schema_name": "Invoice Schema",
  "description": "Canonical invoice fields",
  "fields": {
    "fields": [
      {
        "field_id": "company_id",
        "field_name": "Company ID",
        "data_type": "STRING",
        "is_nullable": false,
        "is_key": true,
        "physical_mapping": { "csv_column": "company_id" }
      },
      {
        "field_id": "amount",
        "field_name": "Amount",
        "data_type": "DECIMAL",
        "precision": 12,
        "scale": 2,
        "physical_mapping": { "csv_column": "amount" }
      }
    ]
  }
}`}</pre>
        <p className="muted">
          `DECIMAL` needs both `precision` and `scale`.
          `physical_mapping` key must match connector style:
          CSV uses `csv_column`, Oracle uses `oracle_column`, Mongo uses `mongo_path`, JSON uses `json_path`.
        </p>
      </div>
    </div>
  );
}

export function DocsDatasets() {
  return (
    <div className="page">
      <div className="card">
        <h3>Datasets</h3>
        <p className="muted">
          A dataset binds a physical object to one system + schema. Allowed `dataset_type`: TABLE, COLLECTION, FILE, VIEW.
        </p>
        <p className="muted">
          In simple words: schema says <em>what</em> fields exist; dataset says <em>where</em> to read those fields from.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Field</th><th>Required</th><th>Allowed Values</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td className="mono">dataset_id</td><td>Yes</td><td>string</td><td>Unique identifier.</td></tr>
              <tr><td className="mono">dataset_name</td><td>Yes</td><td>string</td><td>Display name.</td></tr>
              <tr><td className="mono">system_id</td><td>Yes</td><td>existing system_id</td><td>Connector context.</td></tr>
              <tr><td className="mono">schema_id</td><td>Yes</td><td>existing schema_id</td><td>Canonical mapping target.</td></tr>
              <tr><td className="mono">physical_name</td><td>Yes</td><td>filename/table/collection</td><td>Physical source object name.</td></tr>
              <tr><td className="mono">dataset_type</td><td>Yes</td><td>TABLE | COLLECTION | FILE | VIEW</td><td>Storage object type.</td></tr>
              <tr><td className="mono">filter_config</td><td>No</td><td>object</td><td>Connector-specific filters.</td></tr>
              <tr><td className="mono">metadata</td><td>No</td><td>object</td><td>User metadata (alias accepted as dataset_metadata).</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h3>filter_config by connector</h3>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Connector</th><th>Supported Keys</th><th>Example</th></tr></thead>
            <tbody>
              <tr><td>FILE</td><td className="mono">has_header, delimiter, case_insensitive_lookup</td><td className="mono">{`{"has_header":true,"delimiter":",","case_insensitive_lookup":true}`}</td></tr>
              <tr><td>ORACLE</td><td className="mono">where_clause</td><td className="mono">{`{"where_clause":"status = 'ACTIVE'"}`}</td></tr>
              <tr><td>MONGODB</td><td className="mono">query</td><td className="mono">{`{"query":{"status":"ACTIVE"}}`}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h3>Practical Example: Same Schema, Multiple Datasets</h3>
        <p className="muted">
          You can reuse one schema for daily files:
          <span className="mono"> sales_2026_01.csv </span> and <span className="mono"> sales_2026_02.csv</span>.
          This avoids re-defining fields each time.
        </p>
      </div>
    </div>
  );
}

export function DocsMappings() {
  return (
    <div className="page">
      <div className="card">
        <h3>Mappings and Field Mappings</h3>
        <p className="muted">
          Mapping is where you align business meaning.
          If source uses `cust_nm` and target uses `customer_name`, mapping connects them.
        </p>
        <p className="muted">
          A field mapping can be:
          direct (`source_expression`), or transformation-based (`transform_chain`), with optional validations.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td className="mono">mapping_id</td><td>Yes</td><td>Unique mapping identifier.</td></tr>
              <tr><td className="mono">mapping_name</td><td>Yes</td><td>Display name.</td></tr>
              <tr><td className="mono">source_schema_id</td><td>Yes</td><td>Schema of source records.</td></tr>
              <tr><td className="mono">target_schema_id</td><td>Yes</td><td>Schema of target records.</td></tr>
              <tr><td className="mono">description</td><td>No</td><td>Assumptions and transformation notes.</td></tr>
            </tbody>
          </table>
        </div>
        <pre className="codeblock">{`{
  "mapping_id": "invoice_map_v1",
  "mapping_name": "Invoice Mapping",
  "source_schema_id": "invoice_schema",
  "target_schema_id": "invoice_schema",
  "description": "Normalize and map invoice fields"
}`}</pre>
        <pre className="codeblock">{`{
  "mapping_id": "invoice_map_v1",
  "target_field_id": "customer_name",
  "source_expression": "customer",
  "transform_chain": {"steps":[]},
  "pre_validations": {"validations":[]},
  "post_validations": {"validations":[]},
  "is_active": true
}`}</pre>
        <pre className="codeblock">{`{
  "mapping_id": "invoice_map_v1",
  "target_field_id": "country_name",
  "source_expression": null,
  "transform_chain": {
    "steps": [
      {
        "step_order": 1,
        "transform_type": "lookup",
        "params": {
          "reference_dataset": "country_codes",
          "source_field": "country_code",
          "ref_key_field": "code",
          "ref_value_field": "name",
          "default": "UNKNOWN"
        }
      }
    ]
  },
  "is_active": true
}`}</pre>
        <p className="muted">
          This example shows how a reference dataset is connected into the main transformation path.
        </p>
      </div>
    </div>
  );
}

export function DocsRuleSets() {
  return (
    <div className="page">
      <div className="card">
        <h3>Rule Sets</h3>
        <p className="muted">
          Rule set ties datasets + mapping and controls record matching. `matching_strategy` values: `EXACT`, `FUZZY`.
        </p>
        <pre className="codeblock">{`{
  "rule_set_id": "invoice_recon_v1",
  "rule_set_name": "Invoice Reconciliation",
  "source_dataset_id": "invoice_src",
  "target_dataset_id": "invoice_tgt",
  "mapping_id": "invoice_map_v1",
  "matching_strategy": "EXACT",
  "matching_keys": {
    "keys": [
      {"source_field": "company_id", "target_field": "company_id", "is_case_sensitive": false},
      {"source_field": "invoice_id", "target_field": "invoice_id", "is_case_sensitive": false}
    ],
    "key_normalization": {"trim_whitespace": true}
  },
  "scope_config": {},
  "tolerance_config": {}
}`}</pre>
        <p className="muted">
          Composite key matching is recommended for multi-tenant or repeating IDs.
        </p>
        <p className="muted">
          `matching_keys.keys` order matters when key string is constructed; keep order stable across source and target.
        </p>
      </div>
    </div>
  );
}

export function DocsComparisonRules() {
  return (
    <div className="page">
      <div className="card">
        <h3>Comparison Rules</h3>
        <p className="muted">Allowed `comparator_type` values: EXACT, NUMERIC_TOLERANCE, DATE_WINDOW, CASE_INSENSITIVE, REGEX, CUSTOM, NULL_EQUALS_EMPTY.</p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Comparator</th><th>Supported Params</th><th>Notes</th></tr></thead>
            <tbody>
              <tr><td className="mono">EXACT</td><td className="mono">{`{}`}</td><td>Strict equality.</td></tr>
              <tr><td className="mono">NUMERIC_TOLERANCE</td><td className="mono">{`{"tolerance": 0.01, "tolerance_type":"ABSOLUTE|PERCENT"}`}</td><td>Tolerance can be absolute or percent.</td></tr>
              <tr><td className="mono">DATE_WINDOW</td><td className="mono">{`{"window_seconds": 60}`}</td><td>ISO datetime values are accepted.</td></tr>
              <tr><td className="mono">CASE_INSENSITIVE</td><td className="mono">{`{}`}</td><td>Compares lowercased text.</td></tr>
              <tr><td className="mono">REGEX</td><td className="mono">{`{"pattern":"^[A-Z0-9]+$"}`}</td><td>Both values must match pattern.</td></tr>
              <tr><td className="mono">NULL_EQUALS_EMPTY</td><td className="mono">{`{}`}</td><td>Treats null and empty string as equal.</td></tr>
              <tr><td className="mono">CUSTOM</td><td className="mono">{`{...}`}</td><td>Declared in schema but currently not implemented in comparator engine.</td></tr>
            </tbody>
          </table>
        </div>
        <pre className="codeblock">{`{
  "rule_set_id": "invoice_recon_v1",
  "target_field_id": "amount",
  "comparator_type": "NUMERIC_TOLERANCE",
  "comparator_params": {"tolerance": 0.5, "tolerance_type": "ABSOLUTE"},
  "ignore_field": false,
  "is_active": true
}`}</pre>
        <p className="muted">
          If no comparison rule exists for a field, default comparator behaves like exact value comparison.
        </p>
      </div>
    </div>
  );
}

export function DocsReferenceDatasets() {
  return (
    <div className="page">
      <div className="card">
        <h3>Reference Datasets</h3>
        <p className="muted">
          Reference dataset is a side table used by transforms (usually `lookup`) to enrich or normalize source values.
          It is loaded and cached by the reference manager during execution.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
            <tbody>
              <tr><td className="mono">reference_dataset_id</td><td>Yes</td><td>Unique key for the reference set.</td></tr>
              <tr><td className="mono">reference_name</td><td>Yes</td><td>Display name.</td></tr>
              <tr><td className="mono">source_type</td><td>Yes</td><td>String (project-specific convention, e.g. file/oracle/mongodb/inline).</td></tr>
              <tr><td className="mono">source_config</td><td>Yes</td><td>Source definition object.</td></tr>
              <tr><td className="mono">key_fields</td><td>Yes</td><td>Key definition for lookups.</td></tr>
              <tr><td className="mono">value_fields</td><td>No</td><td>Fields returned from lookup.</td></tr>
              <tr><td className="mono">cache_config</td><td>No</td><td>Cache strategy parameters.</td></tr>
              <tr><td className="mono">refresh_schedule</td><td>No</td><td>Cron-like or custom schedule string.</td></tr>
              <tr><td className="mono">description</td><td>No</td><td>Purpose and maintenance notes.</td></tr>
            </tbody>
          </table>
        </div>
        <pre className="codeblock">{`{
  "reference_dataset_id": "country_codes",
  "reference_name": "Country Codes",
  "description": "ISO country lookup",
  "source_type": "file",
  "source_config": {"path": "reference/country_codes.csv"},
  "key_fields": {"code": "country_code"},
  "value_fields": {"name": "country_name"},
  "cache_config": {"ttl_seconds": 3600},
  "refresh_schedule": "0 * * * *",
  "is_active": true
}`}</pre>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Use Case</th><th>Lookup Key</th><th>Output Value</th></tr></thead>
            <tbody>
              <tr><td>Country code normalization</td><td className="mono">country_code</td><td className="mono">country_name</td></tr>
              <tr><td>Status code expansion</td><td className="mono">status_cd</td><td className="mono">status_description</td></tr>
              <tr><td>Category remapping</td><td className="mono">legacy_category</td><td className="mono">std_category</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
