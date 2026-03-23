function ConnectorPage({ title, summary, rows, example, notes }) {
  return (
    <div className="page">
      <div className="card">
        <h3>{title}</h3>
        <p className="muted">{summary}</p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>connection_config key</th><th>Required</th><th>Type / Allowed Values</th><th>Details</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.key}>
                  <td className="mono">{r.key}</td>
                  <td>{r.required}</td>
                  <td>{r.type}</td>
                  <td>{r.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h3>Working Example</h3>
        <pre className="codeblock">{example}</pre>
      </div>
      {notes ? (
        <div className="card">
          <h3>Important Notes</h3>
          <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
            {notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export function DocsConnectorFile() {
  return (
    <ConnectorPage
      title="Connector: FILE"
      summary="Reads `.csv` and `.json` files from a base directory. CSV supports streaming batches."
      rows={[
        { key: "base_path", required: "Yes", type: "absolute directory path", details: "Root directory for dataset `physical_name` files." },
        { key: "encoding", required: "No", type: "string (default: utf-8)", details: "File encoding for reads." },
        { key: "delimiter", required: "No", type: "string (default: ,)", details: "Default CSV delimiter, overridable by dataset filter config." },
        { key: "array_key", required: "No", type: "string", details: "If JSON root is object, selects nested array key." },
      ]}
      example={`{
  "base_path": "/Users/me/recon-data",
  "encoding": "utf-8",
  "delimiter": ",",
  "array_key": "records"
}`}
      notes={[
        "`base_path` must exist and be a directory.",
        "Paths outside base_path are blocked for safety.",
        "JSON files are loaded in-memory; very large datasets should prefer CSV.",
      ]}
    />
  );
}

export function DocsConnectorOracle() {
  return (
    <ConnectorPage
      title="Connector: ORACLE"
      summary="Connects to Oracle via SQLAlchemy + oracledb. Supports table reads and SQL where-clause filtering."
      rows={[
        { key: "host", required: "Yes", type: "string", details: "Oracle server hostname/IP." },
        { key: "port", required: "Yes", type: "integer (e.g. 1521)", details: "Oracle listener port." },
        { key: "service_name", required: "Either service_name or sid", type: "string", details: "Preferred modern Oracle service name." },
        { key: "sid", required: "Either sid or service_name", type: "string", details: "Legacy SID option." },
        { key: "username", required: "Yes", type: "string", details: "Database username." },
        { key: "password", required: "Yes", type: "string", details: "Database password." },
        { key: "pool_size", required: "No", type: "integer (default: 10)", details: "Connection pool base size." },
        { key: "pool_max_overflow", required: "No", type: "integer (default: 20)", details: "Extra connections beyond pool_size." },
      ]}
      example={`{
  "host": "db.example.net",
  "port": 1521,
  "service_name": "ORCLPDB1",
  "username": "recon_user",
  "password": "********",
  "pool_size": 10,
  "pool_max_overflow": 20
}`}
      notes={[
        "If both service_name and sid are set, service_name is used.",
        "Dataset-level where_clause is appended to SELECT statements.",
      ]}
    />
  );
}

export function DocsConnectorMongodb() {
  return (
    <ConnectorPage
      title="Connector: MONGODB"
      summary="Connects via PyMongo and reads collection documents using projection generated from schema mappings."
      rows={[
        { key: "connection_string", required: "Yes", type: "Mongo URI", details: "Example: mongodb://user:pass@host:27017/?authSource=admin" },
        { key: "database", required: "Yes", type: "string", details: "Database name containing target collections." },
        { key: "max_pool_size", required: "No", type: "integer (default: 50)", details: "Mongo client max pool size." },
        { key: "timeout_ms", required: "No", type: "integer (default: 30000)", details: "Server selection timeout in milliseconds." },
      ]}
      example={`{
  "connection_string": "mongodb://localhost:27017",
  "database": "recon_db",
  "max_pool_size": 50,
  "timeout_ms": 30000
}`}
      notes={[
        "Dataset filter_config can include query JSON object.",
        "Pagination uses _id based cursor internally.",
      ]}
    />
  );
}

export function DocsConnectorApi() {
  return (
    <ConnectorPage
      title="Connector: API"
      summary="UI supports entering API connection JSON, but the current backend connector factory does not include an API reader."
      rows={[
        { key: "url", required: "Usually", type: "string URL", details: "Base endpoint for API calls." },
        { key: "headers", required: "Optional", type: "object", details: "Auth and content headers." },
        { key: "auth", required: "Optional", type: "object", details: "Custom auth payload format." },
      ]}
      example={`{
  "url": "https://api.example.com/v1/items",
  "headers": {
    "Authorization": "Bearer <token>"
  }
}`}
      notes={[
        "Treat API config as future-ready in UI.",
        "If you select API system_type and attempt run now, backend may return unsupported system type.",
      ]}
    />
  );
}

