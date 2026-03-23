import HelpText from "./HelpText.jsx";

function FileFilter({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <>
      <label className="field field-inline-check">
        <input
          type="checkbox"
          checked={value.has_header !== false}
          onChange={(e) => set("has_header", e.target.checked)}
        />
        <span>Has Header Row</span>
        <HelpText>Check if the CSV file has a header row with column names.</HelpText>
      </label>
      <label className="field field-inline-check">
        <input
          type="checkbox"
          checked={Boolean(value.case_insensitive_lookup)}
          onChange={(e) => set("case_insensitive_lookup", e.target.checked)}
        />
        <span>Case-Insensitive Column Lookup</span>
        <HelpText>Match column names regardless of upper/lower case (e.g. "ID" matches "id").</HelpText>
      </label>
      <label className="field">
        <span>Delimiter</span>
        <HelpText>Column separator character. Default is comma.</HelpText>
        <input
          value={value.delimiter || ""}
          onChange={(e) => set("delimiter", e.target.value)}
          placeholder=","
          style={{ maxWidth: 100 }}
        />
      </label>
    </>
  );
}

function OracleFilter({ value, onChange }) {
  const set = (k, v) => onChange({ ...value, [k]: v });
  return (
    <label className="field">
      <span>WHERE Clause</span>
      <HelpText>Optional SQL filter condition (without the WHERE keyword).</HelpText>
      <input
        value={value.where_clause || ""}
        onChange={(e) => set("where_clause", e.target.value)}
        placeholder="status = 'ACTIVE'"
      />
    </label>
  );
}

function MongoFilter({ value, onChange }) {
  const raw = typeof value.query === "string" ? value.query : JSON.stringify(value.query || {}, null, 2);
  return (
    <label className="field">
      <span>Query Filter (JSON)</span>
      <HelpText>MongoDB query document to filter records.</HelpText>
      <textarea
        rows={4}
        className="mono-input"
        value={raw}
        onChange={(e) => {
          try {
            onChange({ ...value, query: JSON.parse(e.target.value) });
          } catch {
            onChange({ ...value, query: e.target.value });
          }
        }}
        placeholder='{"status": "ACTIVE"}'
      />
    </label>
  );
}

export default function FilterConfigForm({ systemType, value, onChange }) {
  if (systemType === "FILE") return <FileFilter value={value} onChange={onChange} />;
  if (systemType === "ORACLE") return <OracleFilter value={value} onChange={onChange} />;
  if (systemType === "MONGODB") return <MongoFilter value={value} onChange={onChange} />;
  return null;
}
