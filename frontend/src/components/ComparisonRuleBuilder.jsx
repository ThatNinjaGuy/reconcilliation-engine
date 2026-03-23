import HelpText from "./HelpText.jsx";

const COMPARATOR_TYPES = [
  { value: "EXACT", label: "Exact Match", desc: "Values must match exactly." },
  { value: "NUMERIC_TOLERANCE", label: "Numeric Tolerance", desc: "Allow numeric differences within a tolerance." },
  { value: "DATE_WINDOW", label: "Date Window", desc: "Allow date/time differences within a time window." },
  { value: "CASE_INSENSITIVE", label: "Case Insensitive", desc: "Compare strings ignoring case." },
  { value: "REGEX", label: "Regex", desc: "Both values must match a regex pattern." },
  { value: "NULL_EQUALS_EMPTY", label: "Null = Empty", desc: "Treat null and empty string as equal." },
];

function emptyRule() {
  return { target_field_id: "", comparator_type: "EXACT", comparator_params: {}, ignore_field: false };
}

function Params({ comparatorType, params, onChange }) {
  const set = (k, v) => onChange({ ...params, [k]: v });

  if (comparatorType === "NUMERIC_TOLERANCE") {
    return (
      <div className="rb-params">
        <label className="field">
          <span>Tolerance</span>
          <input
            type="number"
            step="any"
            value={params.tolerance ?? ""}
            onChange={(e) => set("tolerance", e.target.value ? Number(e.target.value) : "")}
            placeholder="0.01"
          />
        </label>
        <label className="field">
          <span>Type</span>
          <select value={params.tolerance_type || "ABSOLUTE"} onChange={(e) => set("tolerance_type", e.target.value)}>
            <option value="ABSOLUTE">Absolute</option>
            <option value="PERCENT">Percent</option>
          </select>
        </label>
      </div>
    );
  }

  if (comparatorType === "DATE_WINDOW") {
    return (
      <div className="rb-params">
        <label className="field">
          <span>Window (seconds)</span>
          <input
            type="number"
            value={params.window_seconds ?? ""}
            onChange={(e) => set("window_seconds", e.target.value ? Number(e.target.value) : "")}
            placeholder="60"
          />
        </label>
      </div>
    );
  }

  if (comparatorType === "REGEX") {
    return (
      <div className="rb-params">
        <label className="field">
          <span>Pattern</span>
          <input
            value={params.pattern || ""}
            onChange={(e) => set("pattern", e.target.value)}
            placeholder="^[A-Z]+$"
          />
        </label>
      </div>
    );
  }

  return null;
}

export default function ComparisonRuleBuilder({ rules, onChange }) {
  const update = (idx, updated) => {
    const next = [...rules];
    next[idx] = { ...next[idx], ...updated };
    onChange(next);
  };

  const add = () => onChange([...rules, emptyRule()]);
  const remove = (idx) => onChange(rules.filter((_, i) => i !== idx));

  return (
    <div className="repeating-builder">
      <HelpText>
        Define how each field should be compared between source and target records.
        Choose a comparator type and configure any required parameters.
      </HelpText>
      {rules.map((r, i) => {
        const ct = COMPARATOR_TYPES.find((c) => c.value === r.comparator_type);
        return (
          <div key={i} className="cr-row">
            <div className="cr-main">
              <input
                className="rb-cell"
                value={r.target_field_id}
                onChange={(e) => update(i, { target_field_id: e.target.value })}
                placeholder="target field"
              />
              <select
                className="rb-cell"
                value={r.comparator_type}
                onChange={(e) => update(i, { comparator_type: e.target.value, comparator_params: {} })}
              >
                {COMPARATOR_TYPES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
              <label className="rb-check" title="Skip this field during comparison">
                <input
                  type="checkbox"
                  checked={Boolean(r.ignore_field)}
                  onChange={(e) => update(i, { ignore_field: e.target.checked })}
                />
                Ignore
              </label>
              <button type="button" className="fb-remove" onClick={() => remove(i)} title="Remove">
                &times;
              </button>
            </div>
            {ct && <div className="cr-desc">{ct.desc}</div>}
            <Params
              comparatorType={r.comparator_type}
              params={r.comparator_params || {}}
              onChange={(p) => update(i, { comparator_params: p })}
            />
          </div>
        );
      })}
      <button type="button" className="button button-secondary" onClick={add}>
        + Add Comparison Rule
      </button>
    </div>
  );
}

export { emptyRule };
