import HelpText from "./HelpText.jsx";

function emptyMapping() {
  return { target_field_id: "", source_expression: "" };
}

export default function MappingBuilder({ mappings, onChange }) {
  const update = (idx, key, val) => {
    const next = [...mappings];
    next[idx] = { ...next[idx], [key]: val };
    onChange(next);
  };

  const add = () => onChange([...mappings, emptyMapping()]);

  const remove = (idx) => onChange(mappings.filter((_, i) => i !== idx));

  return (
    <div className="repeating-builder">
      <HelpText>
        Map each target field to its source expression. For 1:1 mappings, use the same field name
        for both.
      </HelpText>
      <div className="rb-header">
        <span className="rb-cell">Target Field</span>
        <span className="rb-cell">Source Expression</span>
        <span className="rb-remove-placeholder" />
      </div>
      {mappings.map((m, i) => (
        <div key={i} className="rb-row">
          <input
            className="rb-cell"
            value={m.target_field_id}
            onChange={(e) => update(i, "target_field_id", e.target.value)}
            placeholder="e.g. name"
          />
          <input
            className="rb-cell"
            value={m.source_expression}
            onChange={(e) => update(i, "source_expression", e.target.value)}
            placeholder="e.g. name"
          />
          <button type="button" className="fb-remove" onClick={() => remove(i)} title="Remove">
            &times;
          </button>
        </div>
      ))}
      <button type="button" className="button button-secondary" onClick={add}>
        + Add Field Mapping
      </button>
    </div>
  );
}

export { emptyMapping };
