import HelpText from "./HelpText.jsx";

function emptyKey() {
  return { source_field: "", target_field: "", is_case_sensitive: true };
}

export default function MatchingKeyBuilder({ keys, trimWhitespace, onChange, onTrimChange }) {
  const update = (idx, key, val) => {
    const next = [...keys];
    next[idx] = { ...next[idx], [key]: val };
    onChange(next);
  };

  const add = () => onChange([...keys, emptyKey()]);
  const remove = (idx) => onChange(keys.filter((_, i) => i !== idx));

  return (
    <div className="repeating-builder">
      <HelpText>
        Define which fields to use for matching source records to target records.
        Records with the same composite key are considered a match.
      </HelpText>
      <div className="rb-header">
        <span className="rb-cell">Source Field</span>
        <span className="rb-cell">Target Field</span>
        <span className="rb-check-head">Case Sensitive</span>
        <span className="rb-remove-placeholder" />
      </div>
      {keys.map((k, i) => (
        <div key={i} className="rb-row">
          <input
            className="rb-cell"
            value={k.source_field}
            onChange={(e) => update(i, "source_field", e.target.value)}
            placeholder="e.g. id"
          />
          <input
            className="rb-cell"
            value={k.target_field}
            onChange={(e) => update(i, "target_field", e.target.value)}
            placeholder="e.g. id"
          />
          <label className="rb-check">
            <input
              type="checkbox"
              checked={k.is_case_sensitive !== false}
              onChange={(e) => update(i, "is_case_sensitive", e.target.checked)}
            />
          </label>
          <button type="button" className="fb-remove" onClick={() => remove(i)} title="Remove">
            &times;
          </button>
        </div>
      ))}
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" className="button button-secondary" onClick={add}>
          + Add Key
        </button>
        <label className="field field-inline-check" style={{ margin: 0 }}>
          <input
            type="checkbox"
            checked={Boolean(trimWhitespace)}
            onChange={(e) => onTrimChange(e.target.checked)}
          />
          <span>Trim whitespace from keys</span>
        </label>
      </div>
    </div>
  );
}

export { emptyKey };
