import { Fragment, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";

const TABS = [
  { key: "systems", label: "Systems", endpoint: "/api/v1/systems", idField: "system_id", nameField: "system_name", typeField: "system_type" },
  { key: "schemas", label: "Schemas", endpoint: "/api/v1/schemas", idField: "schema_id", nameField: "schema_name", typeField: null },
  { key: "datasets", label: "Datasets", endpoint: "/api/v1/datasets", idField: "dataset_id", nameField: "dataset_name", typeField: "dataset_type" },
  { key: "mappings", label: "Mappings", endpoint: "/api/v1/mappings", idField: "mapping_id", nameField: "mapping_name", typeField: null },
  { key: "reference_datasets", label: "Reference Datasets", endpoint: "/api/v1/reference-datasets", idField: "reference_dataset_id", nameField: "reference_name", typeField: "source_type" },
  { key: "rule_sets", label: "Rule Sets", endpoint: "/api/v1/rule-sets", idField: "rule_set_id", nameField: "rule_set_name", typeField: "matching_strategy" },
];

function KVTable({ data }) {
  const entries = Object.entries(data || {});
  if (entries.length === 0) return <p className="muted" style={{ margin: 0 }}>—</p>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th style={{ width: 240 }}>Key</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <td className="mono">{k}</td>
              <td className="mono">{typeof v === "object" ? JSON.stringify(v) : String(v)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SchemaFieldsTable({ schema }) {
  const raw = schema?.fields;
  const fields = Array.isArray(raw) ? raw : raw?.fields || [];
  if (!fields.length) return <p className="muted" style={{ margin: 0 }}>No fields.</p>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Field ID</th>
            <th>Name</th>
            <th>Type</th>
            <th>Key</th>
            <th>Nullable</th>
            <th>Physical Mapping</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f) => (
            <tr key={f.field_id}>
              <td className="mono">{f.field_id}</td>
              <td>{f.field_name}</td>
              <td className="mono">
                {f.data_type}
                {f.data_type === "DECIMAL" ? `(${f.precision},${f.scale})` : ""}
              </td>
              <td>{f.is_key ? "Yes" : "No"}</td>
              <td>{f.is_nullable === false ? "No" : "Yes"}</td>
              <td className="mono">{JSON.stringify(f.physical_mapping || {})}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DetailPanel({ tabKey, detail }) {
  if (!detail) return null;

  if (tabKey === "systems") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>System details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>System ID</span><div className="mono">{detail.system_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.system_name}</div></div>
            <div className="field"><span>Type</span><div className="mono">{detail.system_type}</div></div>
            <div className="field"><span>Description</span><div>{detail.description || "—"}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Connection config</span></div>
            <KVTable data={detail.connection_config || {}} />
          </div>
        </div>
      </div>
    );
  }

  if (tabKey === "schemas") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>Schema details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>Schema ID</span><div className="mono">{detail.schema_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.schema_name}</div></div>
            <div className="field"><span>Description</span><div>{detail.description || "—"}</div></div>
            <div className="field"><span>Version</span><div className="mono">{detail.version}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Constraints</span></div>
            <KVTable data={detail.constraints || {}} />
          </div>
        </div>
        <div className="card">
          <h3>Fields</h3>
          <SchemaFieldsTable schema={detail} />
        </div>
      </div>
    );
  }

  if (tabKey === "datasets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>Dataset details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>Dataset ID</span><div className="mono">{detail.dataset_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.dataset_name}</div></div>
            <div className="field"><span>System ID</span><div className="mono">{detail.system_id}</div></div>
            <div className="field"><span>Schema ID</span><div className="mono">{detail.schema_id}</div></div>
            <div className="field"><span>Physical name</span><div className="mono">{detail.physical_name}</div></div>
            <div className="field"><span>Type</span><div className="mono">{detail.dataset_type}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Filter config</span></div>
            <KVTable data={detail.filter_config || {}} />
            <div className="field" style={{ marginTop: 10 }}><span>Metadata</span></div>
            <KVTable data={detail.metadata || {}} />
          </div>
        </div>
      </div>
    );
  }

  if (tabKey === "mappings") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>Mapping details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>Mapping ID</span><div className="mono">{detail.mapping_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.mapping_name}</div></div>
            <div className="field"><span>Source schema</span><div className="mono">{detail.source_schema_id}</div></div>
            <div className="field"><span>Target schema</span><div className="mono">{detail.target_schema_id}</div></div>
            <div className="field"><span>Description</span><div>{detail.description || "—"}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Field mappings</span></div>
            {Array.isArray(detail.field_mappings) && detail.field_mappings.length ? (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>Target field</th><th>Source expression</th><th>Active</th></tr>
                  </thead>
                  <tbody>
                    {detail.field_mappings.map((fm) => (
                      <tr key={fm.field_mapping_id}>
                        <td className="mono">{fm.target_field_id}</td>
                        <td className="mono">{fm.source_expression || "—"}</td>
                        <td>{fm.is_active === false ? "No" : "Yes"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="muted" style={{ margin: 0 }}>No field mappings.</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (tabKey === "reference_datasets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>Reference dataset details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>ID</span><div className="mono">{detail.reference_dataset_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.reference_name}</div></div>
            <div className="field"><span>Source type</span><div className="mono">{detail.source_type}</div></div>
            <div className="field"><span>Description</span><div>{detail.description || "—"}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Source config</span></div>
            <KVTable data={detail.source_config || {}} />
            <div className="field" style={{ marginTop: 10 }}><span>Key fields</span></div>
            <KVTable data={detail.key_fields || {}} />
          </div>
        </div>
      </div>
    );
  }

  if (tabKey === "rule_sets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <h3>Rule set details</h3>
        <div className="grid two">
          <div className="card">
            <div className="field"><span>Rule set ID</span><div className="mono">{detail.rule_set_id}</div></div>
            <div className="field"><span>Name</span><div>{detail.rule_set_name}</div></div>
            <div className="field"><span>Source dataset</span><div className="mono">{detail.source_dataset_id}</div></div>
            <div className="field"><span>Target dataset</span><div className="mono">{detail.target_dataset_id}</div></div>
            <div className="field"><span>Mapping</span><div className="mono">{detail.mapping_id}</div></div>
            <div className="field"><span>Matching strategy</span><div className="mono">{detail.matching_strategy}</div></div>
          </div>
          <div className="card">
            <div className="field"><span>Matching keys</span></div>
            <pre className="codeblock" style={{ maxHeight: 220 }}>
              {JSON.stringify(detail.matching_keys || {}, null, 2)}
            </pre>
          </div>
        </div>
        <div className="card">
          <h3>Comparison rules</h3>
          {Array.isArray(detail.comparison_rules) && detail.comparison_rules.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Target field</th>
                    <th>Comparator</th>
                    <th>Params</th>
                    <th>Ignore</th>
                    <th>Active</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.comparison_rules.map((r) => (
                    <tr key={r.comparison_rule_id}>
                      <td className="mono">{r.target_field_id}</td>
                      <td className="mono">{r.comparator_type}</td>
                      <td className="mono">{JSON.stringify(r.comparator_params || {})}</td>
                      <td>{r.ignore_field ? "Yes" : "No"}</td>
                      <td>{r.is_active === false ? "No" : "Yes"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>No comparison rules.</p>
          )}
        </div>
      </div>
    );
  }

  return null;
}

function EntityTable({ tab, onRunRuleSet }) {
  const { request, loading } = useApi();
  const [items, setItems] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [details, setDetails] = useState({});

  const load = useCallback(async () => {
    const data = await request(tab.endpoint, {}, { toast: false });
    setItems(Array.isArray(data) ? data : []);
  }, [tab.endpoint, request]);

  useEffect(() => {
    load();
  }, [tab.key]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleDelete = async (id) => {
    if (!window.confirm(`Delete ${id}?`)) return;
    await request(`${tab.endpoint}/${id}`, { method: "DELETE" }, { successMessage: `Deleted ${id}` });
    load();
  };

  const loadDetail = async (id) => {
    if (details[id]) return;
    let detail = await request(`${tab.endpoint}/${id}`, {}, { toast: false });
    if (tab.key === "mappings") {
      const fms = await request(`/api/v1/mappings/${id}/field-mappings`, {}, { toast: false });
      detail = { ...detail, field_mappings: Array.isArray(fms) ? fms : [] };
    }
    if (tab.key === "rule_sets") {
      const cr = await request(`/api/v1/rule-sets/${id}/comparison-rules`, {}, { toast: false });
      detail = { ...detail, comparison_rules: Array.isArray(cr) ? cr : [] };
    }
    setDetails((p) => ({ ...p, [id]: detail }));
  };

  if (items === null) {
    return <p className="muted">{loading ? "Loading..." : "No data."}</p>;
  }

  if (items.length === 0) {
    return (
      <div className="empty-state">
        <p className="muted">No {tab.label.toLowerCase()} found.</p>
        <Link className="button" to="/configs/new">Create New</Link>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            {tab.typeField && <th>Type</th>}
            <th>Active</th>
            <th>Created</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const id = item[tab.idField];
            const isExpanded = expanded === id;
            return (
              <Fragment key={id}>
                <tr>
                  <td className="mono">{id}</td>
                  <td>{item[tab.nameField]}</td>
                  {tab.typeField && (
                    <td><span className="badge">{item[tab.typeField]}</span></td>
                  )}
                  <td>
                    {item.is_active !== undefined ? (
                      <span className={item.is_active ? "badge badge-success" : "badge badge-danger"}>
                        {item.is_active ? "Yes" : "No"}
                      </span>
                    ) : "—"}
                  </td>
                  <td className="mono small">{item.created_at || "—"}</td>
                  <td>
                    <div className="actions">
                      {tab.key === "rule_sets" ? (
                        <button
                          type="button"
                          className="button"
                          onClick={() => onRunRuleSet(id)}
                          disabled={loading}
                        >
                          Run
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="button button-secondary"
                        onClick={() => {
                          const next = isExpanded ? null : id;
                          setExpanded(next);
                          if (next) loadDetail(id).catch(() => {});
                        }}
                      >
                        {isExpanded ? "Hide" : "View"}
                      </button>
                      <button type="button" className="button button-secondary danger-text" onClick={() => handleDelete(id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={tab.typeField ? 6 : 5}>
                      <DetailPanel tabKey={tab.key} detail={details[id] || item} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function Configs() {
  const navigate = useNavigate();
  const { request } = useApi();
  const [activeTab, setActiveTab] = useState("systems");
  const tab = TABS.find((t) => t.key === activeTab);
  const [ruleSets, setRuleSets] = useState([]);
  const [selectedRuleSetId, setSelectedRuleSetId] = useState("");
  const [running, setRunning] = useState(false);

  useEffect(() => {
    request("/api/v1/rule-sets", {}, { toast: false })
      .then((rs) => setRuleSets(Array.isArray(rs) ? rs : []))
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runRuleSet = async (ruleSetId) => {
    if (!ruleSetId) return;
    setRunning(true);
    try {
      const job = await request(
        "/api/v1/jobs",
        { method: "POST", body: JSON.stringify({ rule_set_id: ruleSetId, filters: {} }) },
        { successMessage: `Job started for ${ruleSetId}` }
      );
      if (job?.job_id) navigate(`/results/${job.job_id}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Configs</h1>
          <p className="muted">Browse and manage all reconciliation configuration entities.</p>
        </div>
        <div className="actions">
          <Link className="button" to="/configs/new">
            + New Reconciliation
          </Link>
        </div>
      </div>

      <div className="card">
        <h3>Run a Job (existing rule set)</h3>
        <p className="muted" style={{ margin: 0 }}>
          Running a job only requires a Rule Set. Pick one and run it.
        </p>
        <div className="form-grid" style={{ marginTop: 10 }}>
          <label className="field">
            <span>Rule Set</span>
            <select value={selectedRuleSetId} onChange={(e) => setSelectedRuleSetId(e.target.value)}>
              <option value="">— Select a rule set —</option>
              {ruleSets.map((r) => (
                <option key={r.rule_set_id} value={r.rule_set_id}>
                  {r.rule_set_id} — {r.rule_set_name}
                </option>
              ))}
            </select>
          </label>
          <div className="actions" style={{ alignSelf: "end" }}>
            <button type="button" disabled={!selectedRuleSetId || running} onClick={() => runRuleSet(selectedRuleSetId)}>
              {running ? "Running..." : "Run Job"}
            </button>
          </div>
        </div>
      </div>

      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={activeTab === t.key ? "tab active" : "tab"}
            onClick={() => setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="card">
        <EntityTable tab={tab} onRunRuleSet={runRuleSet} />
      </div>
    </div>
  );
}
