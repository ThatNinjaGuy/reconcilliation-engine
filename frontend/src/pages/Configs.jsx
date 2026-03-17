import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import ConnectionConfigForm from "../components/ConnectionConfigForm.jsx";
import FieldBuilder, { emptyField } from "../components/FieldBuilder.jsx";
import FilterConfigForm from "../components/FilterConfigForm.jsx";
import MatchingKeyBuilder from "../components/MatchingKeyBuilder.jsx";
import ComparisonRuleBuilder from "../components/ComparisonRuleBuilder.jsx";
import HelpText from "../components/HelpText.jsx";
import MappingBuilder from "../components/MappingBuilder.jsx";

const TABS = [
  { key: "systems", label: "Systems", endpoint: "/api/v1/systems", idField: "system_id", nameField: "system_name", typeField: "system_type" },
  { key: "schemas", label: "Schemas", endpoint: "/api/v1/schemas", idField: "schema_id", nameField: "schema_name", typeField: null },
  { key: "datasets", label: "Datasets", endpoint: "/api/v1/datasets", idField: "dataset_id", nameField: "dataset_name", typeField: "dataset_type" },
  { key: "mappings", label: "Mappings", endpoint: "/api/v1/mappings", idField: "mapping_id", nameField: "mapping_name", typeField: null },
  { key: "reference_datasets", label: "Reference Datasets", endpoint: "/api/v1/reference-datasets", idField: "reference_dataset_id", nameField: "reference_name", typeField: "source_type" },
  { key: "rule_sets", label: "Rule Sets", endpoint: "/api/v1/rule-sets", idField: "rule_set_id", nameField: "rule_set_name", typeField: "matching_strategy" },
];

function schemaToFieldBuilder(fields) {
  const raw = Array.isArray(fields) ? fields : fields?.fields || [];
  if (!raw.length) return [emptyField()];
  return raw.map((f) => {
    const pm = f.physical_mapping || {};
    const pmKey = Object.keys(pm)[0] || "csv_column";
    return {
      field_id: f.field_id || "",
      field_name: f.field_name || "",
      data_type: f.data_type || "STRING",
      is_nullable: f.is_nullable !== false,
      is_key: Boolean(f.is_key),
      precision: f.precision ?? null,
      scale: f.scale ?? null,
      physical_mapping_type: pmKey,
      physical_mapping_value: pm[pmKey] ?? "",
    };
  });
}

function fieldBuilderToSchemaFields(rows) {
  return {
    fields: (rows || []).map((r) => {
      const out = {
        field_id: r.field_id,
        field_name: r.field_name,
        data_type: r.data_type,
        is_nullable: r.is_nullable,
        is_key: r.is_key,
        physical_mapping: { [r.physical_mapping_type]: r.physical_mapping_value },
      };
      if (r.data_type === "DECIMAL") {
        out.precision = r.precision;
        out.scale = r.scale;
      }
      return out;
    }),
  };
}

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

function DetailPanel({
  tabKey,
  detail,
  mode,
  draft,
  setDraft,
  onSave,
  onCancel,
}) {
  if (!detail) return null;
  const isEdit = mode === "edit";

  if (isEdit && !draft) return null;

  const header = (
    <div className="actions" style={{ justifyContent: "flex-end" }}>
      <button type="button" className="button button-secondary" onClick={onCancel}>
        Cancel
      </button>
      <button type="button" onClick={onSave}>
        Save
      </button>
    </div>
  );

  if (tabKey === "systems") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>System {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>System ID</span>
                <input value={draft.system_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input value={draft.system_name} onChange={(e) => setDraft((p) => ({ ...p, system_name: e.target.value }))} />
              </label>
              <label className="field">
                <span>Type</span>
                <select value={draft.system_type} onChange={(e) => setDraft((p) => ({ ...p, system_type: e.target.value }))}>
                  <option value="FILE">FILE</option>
                  <option value="ORACLE">ORACLE</option>
                  <option value="MONGODB">MONGODB</option>
                  <option value="API">API</option>
                </select>
              </label>
              <label className="field">
                <span>Description</span>
                <input value={draft.description || ""} onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value }))} />
              </label>
            </div>
            <div className="card">
              <h3>Connection config</h3>
              <ConnectionConfigForm
                systemType={draft.system_type}
                value={draft.connection_config || {}}
                onChange={(cfg) => setDraft((p) => ({ ...p, connection_config: cfg }))}
              />
            </div>
          </>
        ) : (
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
              <HelpText>Note: sensitive fields may appear masked.</HelpText>
            </div>
          </div>
        )}
      </div>
    );
  }

  if (tabKey === "schemas") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Schema {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>Schema ID</span>
                <input value={draft.schema_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input value={draft.schema_name} onChange={(e) => setDraft((p) => ({ ...p, schema_name: e.target.value }))} />
              </label>
            </div>
            <FieldBuilder fields={draft._fieldBuilderRows} onChange={(rows) => setDraft((p) => ({ ...p, _fieldBuilderRows: rows }))} />
          </>
        ) : (
          <>
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
          </>
        )}
      </div>
    );
  }

  if (tabKey === "datasets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Dataset {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>Dataset ID</span>
                <input value={draft.dataset_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input
                  value={draft.dataset_name}
                  onChange={(e) => setDraft((p) => ({ ...p, dataset_name: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>System ID</span>
                <input value={draft.system_id} disabled />
              </label>
              <label className="field">
                <span>Schema ID</span>
                <input value={draft.schema_id} disabled />
              </label>
              <label className="field">
                <span>Physical name</span>
                <input
                  value={draft.physical_name}
                  onChange={(e) => setDraft((p) => ({ ...p, physical_name: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>Type</span>
                <input value={draft.dataset_type} disabled />
              </label>
            </div>
            <div className="card">
              <h3>Filter config</h3>
              <FilterConfigForm
                systemType="FILE"
                value={draft.filter_config || {}}
                onChange={(cfg) => setDraft((p) => ({ ...p, filter_config: cfg }))}
              />
            </div>
          </>
        ) : (
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
        )}
      </div>
    );
  }

  if (tabKey === "mappings") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Mapping {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>Mapping ID</span>
                <input value={draft.mapping_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input
                  value={draft.mapping_name}
                  onChange={(e) => setDraft((p) => ({ ...p, mapping_name: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>Description</span>
                <input
                  value={draft.description || ""}
                  onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value }))}
                />
              </label>
            </div>
            <div className="card">
              <h3>Field mappings</h3>
              <MappingBuilder
                mappings={draft._fieldMappings || []}
                onChange={(m) => setDraft((p) => ({ ...p, _fieldMappings: m }))}
              />
            </div>
          </>
        ) : (
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
        )}
      </div>
    );
  }

  if (tabKey === "reference_datasets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Reference dataset {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>ID</span>
                <input value={draft.reference_dataset_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input
                  value={draft.reference_name}
                  onChange={(e) => setDraft((p) => ({ ...p, reference_name: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>Source type</span>
                <input value={draft.source_type} disabled />
              </label>
              <label className="field">
                <span>Description</span>
                <input
                  value={draft.description || ""}
                  onChange={(e) => setDraft((p) => ({ ...p, description: e.target.value }))}
                />
              </label>
            </div>
            <div className="grid two" style={{ marginTop: 10 }}>
              <label className="field">
                <span>Source config (JSON)</span>
                <textarea
                  rows={6}
                  className="mono-input"
                  value={JSON.stringify(draft.source_config || {}, null, 2)}
                  onChange={(e) => {
                    try {
                      setDraft((p) => ({ ...p, source_config: JSON.parse(e.target.value) }));
                    } catch {
                      //
                    }
                  }}
                />
              </label>
              <label className="field">
                <span>Key fields (JSON)</span>
                <textarea
                  rows={6}
                  className="mono-input"
                  value={JSON.stringify(draft.key_fields || {}, null, 2)}
                  onChange={(e) => {
                    try {
                      setDraft((p) => ({ ...p, key_fields: JSON.parse(e.target.value) }));
                    } catch {
                      //
                    }
                  }}
                />
              </label>
            </div>
          </>
        ) : (
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
        )}
      </div>
    );
  }

  if (tabKey === "rule_sets") {
    return (
      <div className="card" style={{ marginTop: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
          <h3 style={{ margin: 0 }}>Rule set {isEdit ? "edit" : "details"}</h3>
          {isEdit ? header : null}
        </div>
        {isEdit ? (
          <>
            <div className="form-grid">
              <label className="field">
                <span>Rule set ID</span>
                <input value={draft.rule_set_id} disabled />
              </label>
              <label className="field">
                <span>Name</span>
                <input
                  value={draft.rule_set_name}
                  onChange={(e) => setDraft((p) => ({ ...p, rule_set_name: e.target.value }))}
                />
              </label>
              <label className="field">
                <span>Matching strategy</span>
                <select
                  value={draft.matching_strategy}
                  onChange={(e) => setDraft((p) => ({ ...p, matching_strategy: e.target.value }))}
                >
                  <option value="EXACT">EXACT</option>
                  <option value="FUZZY">FUZZY</option>
                </select>
              </label>
            </div>
            <div className="card">
              <h3>Matching keys</h3>
              <MatchingKeyBuilder
                keys={draft._matchingKeys || []}
                trimWhitespace={draft._trimWhitespace || false}
                onChange={(keys) => setDraft((p) => ({ ...p, _matchingKeys: keys }))}
                onTrimChange={(tw) => setDraft((p) => ({ ...p, _trimWhitespace: tw }))}
              />
            </div>
            <div className="card">
              <h3>Comparison rules</h3>
              <ComparisonRuleBuilder
                rules={draft._comparisonRules || []}
                onChange={(rules) => setDraft((p) => ({ ...p, _comparisonRules: rules }))}
              />
              <HelpText>
                Saving will append new comparison rules; deleting existing rules is not yet supported from the UI.
              </HelpText>
            </div>
          </>
        ) : (
          <>
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
          </>
        )}
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
  const [editId, setEditId] = useState(null);
  const [draft, setDraft] = useState(null);

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

  const startEdit = async (id) => {
    await loadDetail(id);
    const detail = details[id] || (await request(`${tab.endpoint}/${id}`, {}, { toast: false }));
    if (tab.key === "schemas") {
      setDraft({
        ...detail,
        _fieldBuilderRows: schemaToFieldBuilder(detail.fields),
      });
    } else if (tab.key === "mappings") {
      setDraft({
        ...detail,
        _fieldMappings: (detail.field_mappings || []).map((fm) => ({
          target_field_id: fm.target_field_id || "",
          source_expression: fm.source_expression || "",
        })),
      });
    } else if (tab.key === "rule_sets") {
      const mk = detail.matching_keys;
      let keys = [];
      let trimWhitespace = false;
      if (Array.isArray(mk)) {
        keys = mk;
      } else if (mk && typeof mk === "object") {
        keys = Array.isArray(mk.keys) ? mk.keys : [];
        trimWhitespace = Boolean(mk.key_normalization?.trim_whitespace);
      }
      setDraft({
        ...detail,
        _matchingKeys: keys,
        _trimWhitespace: trimWhitespace,
        _comparisonRules: [],
      });
    } else {
      setDraft({ ...detail });
    }
    setEditId(id);
  };

  const cancelEdit = () => {
    setEditId(null);
    setDraft(null);
  };

  const saveEdit = async () => {
    if (!editId || !draft) return;
    if (tab.key === "systems") {
      const payload = {
        system_name: draft.system_name,
        system_type: draft.system_type,
        description: draft.description,
        connection_config: draft.connection_config || {},
        is_active: draft.is_active,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
    }
    if (tab.key === "schemas") {
      const payload = {
        schema_name: draft.schema_name,
        fields: fieldBuilderToSchemaFields(draft._fieldBuilderRows),
        constraints: draft.constraints || {},
        is_active: draft.is_active,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
    }
    if (tab.key === "datasets") {
      const payload = {
        dataset_name: draft.dataset_name,
        physical_name: draft.physical_name,
        filter_config: draft.filter_config || {},
        metadata: draft.metadata || {},
        is_active: draft.is_active,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
    }
    if (tab.key === "reference_datasets") {
      const payload = {
        reference_name: draft.reference_name,
        description: draft.description,
        source_config: draft.source_config,
        key_fields: draft.key_fields,
        value_fields: draft.value_fields,
        cache_config: draft.cache_config,
        refresh_schedule: draft.refresh_schedule,
        is_active: draft.is_active,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
    }
    if (tab.key === "mappings") {
      const payload = {
        mapping_name: draft.mapping_name,
        description: draft.description,
        is_active: draft.is_active,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
      // replace field mappings via delete + add
      if (Array.isArray(draft._fieldMappings)) {
        const existing = await request(`/api/v1/mappings/${editId}/field-mappings`, {}, { toast: false });
        for (const fm of existing || []) {
          await request(`/api/v1/mappings/${editId}/field-mappings/${fm.field_mapping_id}`, { method: "DELETE" }, { toast: false });
        }
        for (const fm of draft._fieldMappings) {
          if (!fm.target_field_id) continue;
          await request(`/api/v1/mappings/${editId}/field-mappings`, {
            method: "POST",
            body: JSON.stringify({
              mapping_id: editId,
              target_field_id: fm.target_field_id,
              source_expression: fm.source_expression,
              transform_chain: { steps: [] },
              pre_validations: { validations: [] },
              post_validations: { validations: [] },
              is_active: true,
            }),
          }, { toast: false });
        }
      }
    }
    if (tab.key === "rule_sets") {
      const mk = {
        keys: draft._matchingKeys || [],
        key_normalization: { trim_whitespace: draft._trimWhitespace || false },
      };
      const payload = {
        rule_set_name: draft.rule_set_name,
        matching_strategy: draft.matching_strategy,
        matching_keys: mk,
      };
      const updated = await request(`${tab.endpoint}/${editId}`, { method: "PUT", body: JSON.stringify(payload) }, { successMessage: `Updated ${editId}` });
      setDetails((p) => ({ ...p, [editId]: updated }));
      // append new comparison rules
      if (Array.isArray(draft._comparisonRules)) {
        for (const r of draft._comparisonRules) {
          if (!r.target_field_id) continue;
          await request(`/api/v1/rule-sets/${editId}/comparison-rules`, {
            method: "POST",
            body: JSON.stringify({
              rule_set_id: editId,
              target_field_id: r.target_field_id,
              comparator_type: r.comparator_type,
              comparator_params: r.comparator_params || {},
              ignore_field: Boolean(r.ignore_field),
            }),
          }, { toast: false });
        }
      }
    }
    cancelEdit();
    load();
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
                      {expanded === id ? (
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => (editId === id ? cancelEdit() : startEdit(id).catch(() => {}))}
                        >
                          {editId === id ? "Stop edit" : "Edit"}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="button button-secondary"
                        onClick={() => {
                          const next = isExpanded ? null : id;
                          setExpanded(next);
                          if (next) loadDetail(id).catch(() => {});
                          if (!next) cancelEdit();
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
                      <DetailPanel
                        tabKey={tab.key}
                        detail={details[id] || item}
                        mode={editId === id ? "edit" : "view"}
                        draft={editId === id ? draft : null}
                        setDraft={setDraft}
                        onSave={saveEdit}
                        onCancel={cancelEdit}
                      />
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
  const [systems, setSystems] = useState([]);
  const [schemas, setSchemas] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [selectedRuleSetId, setSelectedRuleSetId] = useState("");
  const [running, setRunning] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createDraft, setCreateDraft] = useState(null);

  useEffect(() => {
    Promise.all([
      request("/api/v1/rule-sets", {}, { toast: false }),
      request("/api/v1/systems", {}, { toast: false }),
      request("/api/v1/schemas", {}, { toast: false }),
      request("/api/v1/datasets", {}, { toast: false }),
      request("/api/v1/mappings", {}, { toast: false }),
    ])
      .then(([rs, sys, sch, ds, mp]) => {
        setRuleSets(Array.isArray(rs) ? rs : []);
        setSystems(Array.isArray(sys) ? sys : []);
        setSchemas(Array.isArray(sch) ? sch : []);
        setDatasets(Array.isArray(ds) ? ds : []);
        setMappings(Array.isArray(mp) ? mp : []);
      })
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

  const singular = useMemo(() => {
    const map = {
      systems: "System",
      schemas: "Schema",
      datasets: "Dataset",
      mappings: "Mapping",
      reference_datasets: "Reference Dataset",
      rule_sets: "Rule Set",
    };
    return map[tab.key] || "Item";
  }, [tab.key]);

  const openCreate = () => {
    setCreateOpen(true);
    if (tab.key === "systems") {
      setCreateDraft({
        system_id: "",
        system_name: "",
        system_type: "FILE",
        description: "",
        connection_config: { base_path: "" },
      });
    } else if (tab.key === "schemas") {
      setCreateDraft({
        schema_id: "",
        schema_name: "",
        _fieldBuilderRows: [emptyField()],
      });
    } else if (tab.key === "datasets") {
      setCreateDraft({
        dataset_id: "",
        dataset_name: "",
        system_id: systems[0]?.system_id || "",
        schema_id: schemas[0]?.schema_id || "",
        physical_name: "",
        dataset_type: "FILE",
        filter_config: { has_header: true },
        metadata: {},
      });
    } else if (tab.key === "mappings") {
      setCreateDraft({
        mapping_id: "",
        mapping_name: "",
        source_schema_id: schemas[0]?.schema_id || "",
        target_schema_id: schemas[0]?.schema_id || "",
        description: "",
        _fieldMappings: [{ target_field_id: "", source_expression: "" }],
      });
    } else if (tab.key === "reference_datasets") {
      setCreateDraft({
        reference_dataset_id: "",
        reference_name: "",
        description: "",
        source_type: "file",
        source_config: {},
        key_fields: {},
        value_fields: null,
        cache_config: null,
        refresh_schedule: "",
      });
    } else if (tab.key === "rule_sets") {
      setCreateDraft({
        rule_set_id: "",
        rule_set_name: "",
        source_dataset_id: datasets[0]?.dataset_id || "",
        target_dataset_id: datasets[0]?.dataset_id || "",
        mapping_id: mappings[0]?.mapping_id || "",
        matching_strategy: "EXACT",
        _matchingKeys: [{ source_field: "id", target_field: "id", is_case_sensitive: false }],
        _trimWhitespace: true,
        _comparisonRules: [],
      });
    } else {
      setCreateDraft({});
    }
  };

  const closeCreate = () => {
    setCreateOpen(false);
    setCreateDraft(null);
  };

  const saveCreate = async () => {
    if (!createDraft) return;
    if (tab.key === "systems") {
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(createDraft) }, { successMessage: "System created" });
    }
    if (tab.key === "schemas") {
      const payload = {
        schema_id: createDraft.schema_id,
        schema_name: createDraft.schema_name,
        fields: fieldBuilderToSchemaFields(createDraft._fieldBuilderRows),
        constraints: {},
      };
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(payload) }, { successMessage: "Schema created" });
    }
    if (tab.key === "datasets") {
      const payload = {
        dataset_id: createDraft.dataset_id,
        dataset_name: createDraft.dataset_name,
        system_id: createDraft.system_id,
        schema_id: createDraft.schema_id,
        physical_name: createDraft.physical_name,
        dataset_type: createDraft.dataset_type,
        filter_config: createDraft.filter_config || {},
        metadata: createDraft.metadata || {},
      };
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(payload) }, { successMessage: "Dataset created" });
    }
    if (tab.key === "mappings") {
      const payload = {
        mapping_id: createDraft.mapping_id,
        mapping_name: createDraft.mapping_name,
        source_schema_id: createDraft.source_schema_id,
        target_schema_id: createDraft.target_schema_id,
        description: createDraft.description,
      };
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(payload) }, { successMessage: "Mapping created" });
      for (const fm of createDraft._fieldMappings || []) {
        if (!fm.target_field_id) continue;
        await request(`/api/v1/mappings/${createDraft.mapping_id}/field-mappings`, {
          method: "POST",
          body: JSON.stringify({
            mapping_id: createDraft.mapping_id,
            target_field_id: fm.target_field_id,
            source_expression: fm.source_expression,
            transform_chain: { steps: [] },
            pre_validations: { validations: [] },
            post_validations: { validations: [] },
            is_active: true,
          }),
        }, { toast: false });
      }
    }
    if (tab.key === "reference_datasets") {
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(createDraft) }, { successMessage: "Reference dataset created" });
    }
    if (tab.key === "rule_sets") {
      const mk = {
        keys: createDraft._matchingKeys || [],
        key_normalization: { trim_whitespace: createDraft._trimWhitespace || false },
      };
      const payload = {
        rule_set_id: createDraft.rule_set_id,
        rule_set_name: createDraft.rule_set_name,
        source_dataset_id: createDraft.source_dataset_id,
        target_dataset_id: createDraft.target_dataset_id,
        mapping_id: createDraft.mapping_id,
        matching_strategy: createDraft.matching_strategy,
        matching_keys: mk,
        scope_config: {},
        tolerance_config: {},
      };
      await request(tab.endpoint, { method: "POST", body: JSON.stringify(payload) }, { successMessage: "Rule set created" });
      for (const r of createDraft._comparisonRules || []) {
        if (!r.target_field_id) continue;
        await request(`/api/v1/rule-sets/${createDraft.rule_set_id}/comparison-rules`, {
          method: "POST",
          body: JSON.stringify({
            rule_set_id: createDraft.rule_set_id,
            target_field_id: r.target_field_id,
            comparator_type: r.comparator_type,
            comparator_params: r.comparator_params || {},
            ignore_field: Boolean(r.ignore_field),
          }),
        }, { toast: false });
      }
    }

    // Refresh lists and close
    closeCreate();
    // soft refresh of cached lists
    request(tab.endpoint, {}, { toast: false }).catch(() => {});
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
        <div className="page-head" style={{ marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: 0 }}>{tab.label}</h3>
            <p className="muted" style={{ margin: 0 }}>
              Manage {tab.label.toLowerCase()} (view, edit, delete).
            </p>
          </div>
          <div className="actions">
            <button
              type="button"
              className="button"
              onClick={() => (createOpen ? closeCreate() : openCreate())}
            >
              {createOpen ? "Close" : `+ Add ${singular}`}
            </button>
          </div>
        </div>

        {createOpen && createDraft ? (
          <div className="card" style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12 }}>
              <h3 style={{ margin: 0 }}>Add {singular}</h3>
              <div className="actions">
                <button type="button" className="button button-secondary" onClick={closeCreate}>Cancel</button>
                <button type="button" onClick={saveCreate}>Create</button>
              </div>
            </div>

            {tab.key === "systems" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>System ID *</span><input value={createDraft.system_id} onChange={(e)=>setCreateDraft(p=>({...p,system_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.system_name} onChange={(e)=>setCreateDraft(p=>({...p,system_name:e.target.value}))} /></label>
                  <label className="field"><span>Type *</span>
                    <select value={createDraft.system_type} onChange={(e)=>setCreateDraft(p=>({...p,system_type:e.target.value}))}>
                      <option value="FILE">FILE</option><option value="ORACLE">ORACLE</option><option value="MONGODB">MONGODB</option><option value="API">API</option>
                    </select>
                  </label>
                  <label className="field"><span>Description</span><input value={createDraft.description} onChange={(e)=>setCreateDraft(p=>({...p,description:e.target.value}))} /></label>
                </div>
                <ConnectionConfigForm
                  systemType={createDraft.system_type}
                  value={createDraft.connection_config || {}}
                  onChange={(cfg)=>setCreateDraft(p=>({...p,connection_config:cfg}))}
                />
              </>
            ) : null}

            {tab.key === "schemas" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>Schema ID *</span><input value={createDraft.schema_id} onChange={(e)=>setCreateDraft(p=>({...p,schema_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.schema_name} onChange={(e)=>setCreateDraft(p=>({...p,schema_name:e.target.value}))} /></label>
                </div>
                <FieldBuilder fields={createDraft._fieldBuilderRows} onChange={(rows)=>setCreateDraft(p=>({...p,_fieldBuilderRows:rows}))} />
              </>
            ) : null}

            {tab.key === "datasets" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>Dataset ID *</span><input value={createDraft.dataset_id} onChange={(e)=>setCreateDraft(p=>({...p,dataset_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.dataset_name} onChange={(e)=>setCreateDraft(p=>({...p,dataset_name:e.target.value}))} /></label>
                  <label className="field"><span>System *</span>
                    <select value={createDraft.system_id} onChange={(e)=>setCreateDraft(p=>({...p,system_id:e.target.value}))}>
                      {systems.map((s)=>(<option key={s.system_id} value={s.system_id}>{s.system_id} — {s.system_name}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Schema *</span>
                    <select value={createDraft.schema_id} onChange={(e)=>setCreateDraft(p=>({...p,schema_id:e.target.value}))}>
                      {schemas.map((s)=>(<option key={s.schema_id} value={s.schema_id}>{s.schema_id} — {s.schema_name}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Physical name *</span><input value={createDraft.physical_name} onChange={(e)=>setCreateDraft(p=>({...p,physical_name:e.target.value}))} placeholder="source.csv" /></label>
                  <label className="field"><span>Dataset type</span>
                    <select value={createDraft.dataset_type} onChange={(e)=>setCreateDraft(p=>({...p,dataset_type:e.target.value}))}>
                      <option value="FILE">FILE</option><option value="TABLE">TABLE</option><option value="COLLECTION">COLLECTION</option><option value="VIEW">VIEW</option>
                    </select>
                  </label>
                </div>
                <div className="card">
                  <h3>Filter config</h3>
                  <FilterConfigForm
                    systemType={(systems.find((s)=>s.system_id===createDraft.system_id)?.system_type) || "FILE"}
                    value={createDraft.filter_config || {}}
                    onChange={(cfg)=>setCreateDraft(p=>({...p,filter_config:cfg}))}
                  />
                </div>
              </>
            ) : null}

            {tab.key === "mappings" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>Mapping ID *</span><input value={createDraft.mapping_id} onChange={(e)=>setCreateDraft(p=>({...p,mapping_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.mapping_name} onChange={(e)=>setCreateDraft(p=>({...p,mapping_name:e.target.value}))} /></label>
                  <label className="field"><span>Source schema *</span>
                    <select value={createDraft.source_schema_id} onChange={(e)=>setCreateDraft(p=>({...p,source_schema_id:e.target.value}))}>
                      {schemas.map((s)=>(<option key={s.schema_id} value={s.schema_id}>{s.schema_id}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Target schema *</span>
                    <select value={createDraft.target_schema_id} onChange={(e)=>setCreateDraft(p=>({...p,target_schema_id:e.target.value}))}>
                      {schemas.map((s)=>(<option key={s.schema_id} value={s.schema_id}>{s.schema_id}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Description</span><input value={createDraft.description} onChange={(e)=>setCreateDraft(p=>({...p,description:e.target.value}))} /></label>
                </div>
                <div className="card">
                  <h3>Field mappings</h3>
                  <MappingBuilder mappings={createDraft._fieldMappings || []} onChange={(m)=>setCreateDraft(p=>({...p,_fieldMappings:m}))} />
                </div>
              </>
            ) : null}

            {tab.key === "reference_datasets" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>ID *</span><input value={createDraft.reference_dataset_id} onChange={(e)=>setCreateDraft(p=>({...p,reference_dataset_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.reference_name} onChange={(e)=>setCreateDraft(p=>({...p,reference_name:e.target.value}))} /></label>
                  <label className="field"><span>Source type *</span><input value={createDraft.source_type} onChange={(e)=>setCreateDraft(p=>({...p,source_type:e.target.value}))} placeholder="file|oracle|mongodb|inline" /></label>
                  <label className="field"><span>Description</span><input value={createDraft.description} onChange={(e)=>setCreateDraft(p=>({...p,description:e.target.value}))} /></label>
                </div>
                <div className="grid two">
                  <label className="field"><span>Source config (JSON)</span>
                    <textarea rows={6} className="mono-input" value={JSON.stringify(createDraft.source_config||{},null,2)} onChange={(e)=>{try{setCreateDraft(p=>({...p,source_config:JSON.parse(e.target.value)}))}catch{}}} />
                  </label>
                  <label className="field"><span>Key fields (JSON)</span>
                    <textarea rows={6} className="mono-input" value={JSON.stringify(createDraft.key_fields||{},null,2)} onChange={(e)=>{try{setCreateDraft(p=>({...p,key_fields:JSON.parse(e.target.value)}))}catch{}}} />
                  </label>
                </div>
              </>
            ) : null}

            {tab.key === "rule_sets" ? (
              <>
                <div className="form-grid">
                  <label className="field"><span>Rule set ID *</span><input value={createDraft.rule_set_id} onChange={(e)=>setCreateDraft(p=>({...p,rule_set_id:e.target.value}))} /></label>
                  <label className="field"><span>Name *</span><input value={createDraft.rule_set_name} onChange={(e)=>setCreateDraft(p=>({...p,rule_set_name:e.target.value}))} /></label>
                  <label className="field"><span>Source dataset *</span>
                    <select value={createDraft.source_dataset_id} onChange={(e)=>setCreateDraft(p=>({...p,source_dataset_id:e.target.value}))}>
                      {datasets.map((d)=>(<option key={d.dataset_id} value={d.dataset_id}>{d.dataset_id} — {d.dataset_name}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Target dataset *</span>
                    <select value={createDraft.target_dataset_id} onChange={(e)=>setCreateDraft(p=>({...p,target_dataset_id:e.target.value}))}>
                      {datasets.map((d)=>(<option key={d.dataset_id} value={d.dataset_id}>{d.dataset_id} — {d.dataset_name}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Mapping *</span>
                    <select value={createDraft.mapping_id} onChange={(e)=>setCreateDraft(p=>({...p,mapping_id:e.target.value}))}>
                      {mappings.map((m)=>(<option key={m.mapping_id} value={m.mapping_id}>{m.mapping_id} — {m.mapping_name}</option>))}
                    </select>
                  </label>
                  <label className="field"><span>Matching strategy</span>
                    <select value={createDraft.matching_strategy} onChange={(e)=>setCreateDraft(p=>({...p,matching_strategy:e.target.value}))}>
                      <option value="EXACT">EXACT</option><option value="FUZZY">FUZZY</option>
                    </select>
                  </label>
                </div>
                <div className="card">
                  <h3>Matching keys</h3>
                  <MatchingKeyBuilder
                    keys={createDraft._matchingKeys || []}
                    trimWhitespace={createDraft._trimWhitespace || false}
                    onChange={(keys)=>setCreateDraft(p=>({...p,_matchingKeys:keys}))}
                    onTrimChange={(tw)=>setCreateDraft(p=>({...p,_trimWhitespace:tw}))}
                  />
                </div>
                <div className="card">
                  <h3>Comparison rules (optional)</h3>
                  <ComparisonRuleBuilder rules={createDraft._comparisonRules || []} onChange={(rules)=>setCreateDraft(p=>({...p,_comparisonRules:rules}))} />
                </div>
              </>
            ) : null}
          </div>
        ) : null}

        <EntityTable tab={tab} onRunRuleSet={runRuleSet} />
      </div>
    </div>
  );
}
