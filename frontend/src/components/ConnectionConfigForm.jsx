import HelpText from "./HelpText.jsx";

const SYSTEM_DESCRIPTIONS = {
  FILE: "Connect to local CSV or JSON files on the server filesystem.",
  ORACLE: "Connect to an Oracle database via host/port/service.",
  MONGODB: "Connect to a MongoDB instance via connection string.",
  API: "Connect to a REST API endpoint.",
};

function FileFields({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <>
      <label className="field">
        <span>Base Path *</span>
        <HelpText>Absolute path to the directory containing your data files.</HelpText>
        <input value={value.base_path || ""} onChange={(e) => set("base_path", e.target.value)} placeholder="/path/to/data/directory" />
      </label>
      <label className="field">
        <span>Encoding</span>
        <HelpText>Character encoding for reading files.</HelpText>
        <input value={value.encoding || ""} onChange={(e) => set("encoding", e.target.value)} placeholder="utf-8" />
      </label>
      <label className="field">
        <span>Delimiter</span>
        <HelpText>Column delimiter for CSV files. Default is comma.</HelpText>
        <input value={value.delimiter || ""} onChange={(e) => set("delimiter", e.target.value)} placeholder="," />
      </label>
      <label className="field">
        <span>Array Key</span>
        <HelpText>For JSON where the root is an object, specify the key holding the records array.</HelpText>
        <input value={value.array_key || ""} onChange={(e) => set("array_key", e.target.value)} placeholder='e.g. "records"' />
      </label>
    </>
  );
}

function OracleFields({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <>
      <label className="field">
        <span>Host *</span>
        <input value={value.host || ""} onChange={(e) => set("host", e.target.value)} placeholder="localhost" />
      </label>
      <label className="field">
        <span>Port *</span>
        <input type="number" value={value.port ?? ""} onChange={(e) => set("port", Number(e.target.value))} placeholder="1521" />
      </label>
      <label className="field">
        <span>Service Name</span>
        <HelpText>Use either Service Name or SID, not both.</HelpText>
        <input value={value.service_name || ""} onChange={(e) => set("service_name", e.target.value)} placeholder="ORCL" />
      </label>
      <label className="field">
        <span>SID</span>
        <input value={value.sid || ""} onChange={(e) => set("sid", e.target.value)} placeholder="ORCL" />
      </label>
      <label className="field">
        <span>Username *</span>
        <input value={value.username || ""} onChange={(e) => set("username", e.target.value)} placeholder="db_user" />
      </label>
      <label className="field">
        <span>Password *</span>
        <input type="password" value={value.password || ""} onChange={(e) => set("password", e.target.value)} placeholder="••••••" />
      </label>
      <label className="field">
        <span>Pool Size</span>
        <input type="number" value={value.pool_size ?? ""} onChange={(e) => set("pool_size", Number(e.target.value))} placeholder="10" />
      </label>
      <label className="field">
        <span>Pool Max Overflow</span>
        <input type="number" value={value.pool_max_overflow ?? ""} onChange={(e) => set("pool_max_overflow", Number(e.target.value))} placeholder="20" />
      </label>
    </>
  );
}

function MongoFields({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <>
      <label className="field">
        <span>Connection String *</span>
        <HelpText>Full MongoDB URI.</HelpText>
        <input value={value.connection_string || ""} onChange={(e) => set("connection_string", e.target.value)} placeholder="mongodb://localhost:27017" />
      </label>
      <label className="field">
        <span>Database *</span>
        <input value={value.database || ""} onChange={(e) => set("database", e.target.value)} placeholder="mydb" />
      </label>
      <label className="field">
        <span>Max Pool Size</span>
        <input type="number" value={value.max_pool_size ?? ""} onChange={(e) => set("max_pool_size", Number(e.target.value))} placeholder="50" />
      </label>
      <label className="field">
        <span>Timeout (ms)</span>
        <input type="number" value={value.timeout_ms ?? ""} onChange={(e) => set("timeout_ms", Number(e.target.value))} placeholder="30000" />
      </label>
    </>
  );
}

function ApiFields({ value, onChange }) {
  return (
    <label className="field">
      <span>Config (JSON)</span>
      <HelpText>Free-form JSON for API connection parameters (url, headers, auth, etc.).</HelpText>
      <textarea
        rows={6}
        className="mono-input"
        value={typeof value === "string" ? value : JSON.stringify(value, null, 2)}
        onChange={(e) => {
          try { onChange(JSON.parse(e.target.value)); } catch { /* let user keep typing */ }
        }}
        placeholder='{\n  "url": "https://api.example.com",\n  "headers": {}\n}'
      />
    </label>
  );
}

export default function ConnectionConfigForm({ systemType, value, onChange }) {
  const desc = SYSTEM_DESCRIPTIONS[systemType];
  return (
    <div className="connection-config-form">
      {desc && <p className="help-text" style={{ marginBottom: 12 }}>{desc}</p>}
      <div className="form-grid">
        {systemType === "FILE" && <FileFields value={value} onChange={onChange} />}
        {systemType === "ORACLE" && <OracleFields value={value} onChange={onChange} />}
        {systemType === "MONGODB" && <MongoFields value={value} onChange={onChange} />}
        {systemType === "API" && <ApiFields value={value} onChange={onChange} />}
      </div>
    </div>
  );
}
