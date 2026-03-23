export default function DocsPage() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Documentation</h1>
          <p className="muted">
            Complete setup guide for systems, datasets, mappings, rule sets, comparison rules, and reference datasets.
          </p>
        </div>
      </div>

      <div className="card">
        <h3>End-to-end Flow</h3>
        <ol className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>Create source and target systems.</li>
          <li>Create schemas with physical mappings for each field.</li>
          <li>Create datasets linked to system + schema.</li>
          <li>Create mapping from source schema to target schema.</li>
          <li>Create rule set (matching keys + optional comparison rules).</li>
          <li>Run jobs from Configs or Dashboard using rule set ID.</li>
        </ol>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Systems</h3>
          <p className="muted">`system_type`: FILE, ORACLE, MONGODB, API</p>
          <p className="muted">Use `description` to document usage, owner, and expected payload shape.</p>
          <p className="muted">Connection config varies by type (paths, connection string, db/table, endpoint, auth).</p>
        </div>
        <div className="card">
          <h3>Schemas</h3>
          <p className="muted">Each field needs: `field_id`, `field_name`, `data_type`, nullability, key flag.</p>
          <p className="muted">`physical_mapping` links canonical field to source representation.</p>
          <p className="muted">`DECIMAL` requires both precision and scale.</p>
        </div>
      </div>

      <div className="grid two">
        <div className="card">
          <h3>Datasets</h3>
          <p className="muted">A dataset binds `system_id` + `schema_id` + `physical_name`.</p>
          <p className="muted">`dataset_type`: FILE, TABLE, COLLECTION, VIEW.</p>
          <p className="muted">`filter_config` controls parser behavior (headers, delimiter, sheet, query filters).</p>
        </div>
        <div className="card">
          <h3>Mappings</h3>
          <p className="muted">Map target field IDs to source expressions.</p>
          <p className="muted">Use mapping description to explain transformation assumptions.</p>
          <p className="muted">Field mappings can be edited in Configs inline.</p>
        </div>
      </div>

      <div className="card">
        <h3>Rule Sets and Matching</h3>
        <p className="muted">`matching_strategy`: EXACT or FUZZY.</p>
        <p className="muted">Matching keys can be composite (2+ columns) and support per-key case sensitivity.</p>
        <p className="muted">`key_normalization.trim_whitespace` helps normalize spacing differences.</p>
      </div>

      <div className="card">
        <h3>Comparison Rules (Optional)</h3>
        <p className="muted">Create per-field comparators to override default exact checks.</p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Comparator Type</th>
                <th>Typical Params</th>
                <th>Use Case</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="mono">EXACT</td>
                <td className="mono">{`{}`}</td>
                <td>Strict equality.</td>
              </tr>
              <tr>
                <td className="mono">NUMERIC_TOLERANCE</td>
                <td className="mono">{`{"tolerance": 0.01}`}</td>
                <td>Amounts with minor drift.</td>
              </tr>
              <tr>
                <td className="mono">ABSOLUTE_DIFFERENCE</td>
                <td className="mono">{`{"max_diff": 5}`}</td>
                <td>Integer thresholds.</td>
              </tr>
              <tr>
                <td className="mono">RELATIVE_PERCENT</td>
                <td className="mono">{`{"max_percent": 1.5}`}</td>
                <td>Percentage-based tolerance.</td>
              </tr>
              <tr>
                <td className="mono">CASE_INSENSITIVE</td>
                <td className="mono">{`{}`}</td>
                <td>Text values with casing differences.</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="muted">Use `ignore_field: true` to skip a target field from discrepancy checks.</p>
      </div>

      <div className="card">
        <h3>Reference Datasets</h3>
        <p className="muted">Use for lookup/enrichment and normalization scenarios.</p>
        <p className="muted">Define source config, key fields, and optional cache/refresh behavior.</p>
        <p className="muted">Can be combined with transformations and validation workflows.</p>
      </div>

      <div className="card">
        <h3>Best Practices</h3>
        <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>Use composite keys whenever one field is not globally unique.</li>
          <li>Start with EXACT matching, then add targeted comparison rules.</li>
          <li>Add descriptions on systems, schemas, mappings, and reference datasets.</li>
          <li>Keep schema physical mappings aligned with real source column names/paths.</li>
        </ul>
      </div>
    </div>
  );
}
