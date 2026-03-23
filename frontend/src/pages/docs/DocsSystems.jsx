export default function DocsSystems() {
  return (
    <div className="page">
      <div className="card">
        <h3>System Configuration</h3>
        <p className="muted">
          A system defines connection details for one source/target technology.
          Allowed `system_type` values are: `FILE`, `ORACLE`, `MONGODB`, `API`.
        </p>
        <p className="muted">
          Create one system per environment/technology boundary.
          Example: `oracle_prod_finance` and `oracle_stage_finance` should usually be separate systems.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Field</th><th>Required</th><th>Allowed Values</th><th>Description</th></tr>
            </thead>
            <tbody>
              <tr><td className="mono">system_id</td><td>Yes</td><td>string</td><td>Unique identifier (immutable key you reference later).</td></tr>
              <tr><td className="mono">system_name</td><td>Yes</td><td>string</td><td>Human-friendly name displayed in UI.</td></tr>
              <tr><td className="mono">system_type</td><td>Yes</td><td>FILE | ORACLE | MONGODB | API</td><td>Selects connector behavior and required config keys.</td></tr>
              <tr><td className="mono">description</td><td>No</td><td>string</td><td>Document owner, purpose, environment and usage notes.</td></tr>
              <tr><td className="mono">connection_config</td><td>Yes</td><td>object</td><td>Connector-specific settings.</td></tr>
              <tr><td className="mono">is_active</td><td>No</td><td>true | false</td><td>Whether this config is active.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Example: FILE System</h3>
        <pre className="codeblock">{`{
  "system_id": "file_local",
  "system_name": "Local Files",
  "system_type": "FILE",
  "description": "Reads CSV and JSON from sample_data",
  "connection_config": {
    "base_path": "/Users/me/data",
    "encoding": "utf-8",
    "delimiter": ",",
    "array_key": "records"
  },
  "is_active": true
}`}</pre>
        <p className="muted">Use one system per environment/source cluster (e.g. local, stage, prod).</p>
      </div>

      <div className="card">
        <h3>When Users Get Confused</h3>
        <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>System is not data. It is only the connection profile.</li>
          <li>You do not select columns in system. Column logic belongs to schema.</li>
          <li>You do not select file/table in system. Concrete object belongs to dataset (`physical_name`).</li>
        </ul>
      </div>
    </div>
  );
}
