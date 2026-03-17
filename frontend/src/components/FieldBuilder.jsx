import HelpText from "./HelpText.jsx";

const DATA_TYPES = [
  { value: "STRING", label: "STRING" },
  { value: "INTEGER", label: "INTEGER" },
  { value: "DECIMAL", label: "DECIMAL (needs precision & scale)" },
  { value: "BOOLEAN", label: "BOOLEAN" },
  { value: "DATE", label: "DATE" },
  { value: "TIMESTAMP", label: "TIMESTAMP" },
  { value: "ARRAY", label: "ARRAY" },
  { value: "OBJECT", label: "OBJECT" },
];

const MAPPING_TYPES = [
  { value: "json_path", label: "JSON Path" },
  { value: "csv_column", label: "CSV Column" },
  { value: "oracle_column", label: "Oracle Column" },
  { value: "mongo_path", label: "Mongo Path" },
];

function emptyField() {
  return {
    field_id: "",
    field_name: "",
    data_type: "STRING",
    is_nullable: true,
    is_key: false,
    precision: null,
    scale: null,
    physical_mapping_type: "csv_column",
    physical_mapping_value: "",
  };
}

function FieldRow({ field, index, onChange, onRemove }) {
  const set = (k, v) => onChange(index, { ...field, [k]: v });
  const isDecimal = field.data_type === "DECIMAL";

  return (
    <div className="field-builder-row">
      <input
        className="fb-cell"
        value={field.field_id}
        onChange={(e) => set("field_id", e.target.value)}
        placeholder="field_id"
      />
      <input
        className="fb-cell"
        value={field.field_name}
        onChange={(e) => set("field_name", e.target.value)}
        placeholder="field_name"
      />
      <select className="fb-cell" value={field.data_type} onChange={(e) => set("data_type", e.target.value)}>
        {DATA_TYPES.map((dt) => (
          <option key={dt.value} value={dt.value}>{dt.label}</option>
        ))}
      </select>
      {isDecimal ? (
        <>
          <input
            className="fb-cell fb-small"
            type="number"
            value={field.precision ?? ""}
            onChange={(e) => set("precision", e.target.value ? Number(e.target.value) : null)}
            placeholder="precision"
          />
          <input
            className="fb-cell fb-small"
            type="number"
            value={field.scale ?? ""}
            onChange={(e) => set("scale", e.target.value ? Number(e.target.value) : null)}
            placeholder="scale"
          />
        </>
      ) : (
        <>
          <span className="fb-cell fb-small" />
          <span className="fb-cell fb-small" />
        </>
      )}
      <label className="fb-check">
        <input type="checkbox" checked={!field.is_nullable} onChange={(e) => set("is_nullable", !e.target.checked)} />
        Required
      </label>
      <label className="fb-check">
        <input type="checkbox" checked={field.is_key} onChange={(e) => set("is_key", e.target.checked)} />
        Key
      </label>
      <select className="fb-cell" value={field.physical_mapping_type} onChange={(e) => set("physical_mapping_type", e.target.value)}>
        {MAPPING_TYPES.map((mt) => (
          <option key={mt.value} value={mt.value}>{mt.label}</option>
        ))}
      </select>
      <input
        className="fb-cell"
        value={field.physical_mapping_value}
        onChange={(e) => set("physical_mapping_value", e.target.value)}
        placeholder="column / path"
      />
      <button type="button" className="fb-remove" onClick={() => onRemove(index)} title="Remove field">
        &times;
      </button>
    </div>
  );
}

export default function FieldBuilder({ fields, onChange }) {
  const updateField = (idx, updated) => {
    const next = [...fields];
    next[idx] = updated;
    onChange(next);
  };

  const addField = () => onChange([...fields, emptyField()]);

  const removeField = (idx) => onChange(fields.filter((_, i) => i !== idx));

  return (
    <div className="field-builder">
      <HelpText>
        Define the fields for this schema. At least one field must be marked as Key.
        DECIMAL type requires precision and scale.
      </HelpText>
      <div className="field-builder-header">
        <span className="fb-cell">ID</span>
        <span className="fb-cell">Name</span>
        <span className="fb-cell">Data Type</span>
        <span className="fb-cell fb-small">Prec.</span>
        <span className="fb-cell fb-small">Scale</span>
        <span className="fb-check">Req.</span>
        <span className="fb-check">Key</span>
        <span className="fb-cell">Mapping Type</span>
        <span className="fb-cell">Mapping Value</span>
        <span className="fb-remove-placeholder" />
      </div>
      {fields.map((f, i) => (
        <FieldRow key={i} field={f} index={i} onChange={updateField} onRemove={removeField} />
      ))}
      <button type="button" className="button button-secondary" onClick={addField}>
        + Add Field
      </button>
    </div>
  );
}

export { emptyField };
