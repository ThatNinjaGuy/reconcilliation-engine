import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Collapsible from "../components/Collapsible.jsx";
import ConnectionConfigForm from "../components/ConnectionConfigForm.jsx";
import FieldBuilder, { emptyField } from "../components/FieldBuilder.jsx";
import FilterConfigForm from "../components/FilterConfigForm.jsx";
import MappingBuilder from "../components/MappingBuilder.jsx";
import MatchingKeyBuilder from "../components/MatchingKeyBuilder.jsx";
import ComparisonRuleBuilder from "../components/ComparisonRuleBuilder.jsx";
import HelpText from "../components/HelpText.jsx";
import { useApi } from "../hooks/useApi.js";

const StepBadge = ({ idx, title, done }) => (
  <div className={done ? "step step-done" : "step"}>
    <div className="step-num">{idx}</div>
    <div className="step-title">
      {title} {done ? <span className="step-check">&#10003;</span> : null}
    </div>
  </div>
);

function ExistingPicker({ label, items, value, onChange, getId, getName, getMeta }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="">— Select —</option>
        {(items || []).map((it) => {
          const id = getId(it);
          const name = getName(it);
          const meta = getMeta ? getMeta(it) : "";
          return (
            <option key={id} value={id}>
              {id} {name ? `— ${name}` : ""}{meta ? ` (${meta})` : ""}
            </option>
          );
        })}
      </select>
    </label>
  );
}

export default function ConfigWizard() {
  const { request, loading } = useApi();
  const navigate = useNavigate();

  const [systemId, setSystemId] = useState("");
  const [schemaId, setSchemaId] = useState("");
  const [sourceDatasetId, setSourceDatasetId] = useState("");
  const [targetDatasetId, setTargetDatasetId] = useState("");
  const [mappingId, setMappingId] = useState("");
  const [ruleSetId, setRuleSetId] = useState("");
  const [lastJobId, setLastJobId] = useState("");

  // Existing entities lists
  const [systems, setSystems] = useState([]);
  const [schemas, setSchemas] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [mappings, setMappings] = useState([]);
  const [ruleSets, setRuleSets] = useState([]);

  // “Use existing” selection state
  const [useExistingSystem, setUseExistingSystem] = useState(false);
  const [useExistingSchema, setUseExistingSchema] = useState(false);
  const [useExistingDatasets, setUseExistingDatasets] = useState(false);
  const [useExistingMapping, setUseExistingMapping] = useState(false);
  const [useExistingRuleSet, setUseExistingRuleSet] = useState(false);

  const [selectedSystemId, setSelectedSystemId] = useState("");
  const [selectedSchemaId, setSelectedSchemaId] = useState("");
  const [selectedSourceDatasetId, setSelectedSourceDatasetId] = useState("");
  const [selectedTargetDatasetId, setSelectedTargetDatasetId] = useState("");
  const [selectedMappingId, setSelectedMappingId] = useState("");
  const [selectedRuleSetId, setSelectedRuleSetId] = useState("");

  // --- System ---
  const [systemForm, setSystemForm] = useState({
    system_id: "",
    system_name: "",
    system_type: "FILE",
    description: "",
  });
  const [connectionConfig, setConnectionConfig] = useState({ base_path: "" });

  // --- Schema ---
  const [schemaForm, setSchemaForm] = useState({ schema_id: "", schema_name: "" });
  const [schemaFields, setSchemaFields] = useState([emptyField()]);

  // --- Datasets ---
  const [datasetForm, setDatasetForm] = useState({
    source_dataset_id: "",
    source_dataset_name: "",
    target_dataset_id: "",
    target_dataset_name: "",
    physical_source: "source.csv",
    physical_target: "target.csv",
    dataset_type: "FILE",
  });
  const [filterConfig, setFilterConfig] = useState({ has_header: true });

  // --- Mapping ---
  const [mappingForm, setMappingForm] = useState({ mapping_id: "", mapping_name: "" });
  const [fieldMappings, setFieldMappings] = useState([
    { target_field_id: "", source_expression: "" },
  ]);

  // --- Rule Set ---
  const [ruleSetForm, setRuleSetForm] = useState({
    rule_set_id: "",
    rule_set_name: "",
    matching_strategy: "EXACT",
  });
  const [matchingKeys, setMatchingKeys] = useState([
    { source_field: "id", target_field: "id", is_case_sensitive: false },
  ]);
  const [trimWhitespace, setTrimWhitespace] = useState(true);
  const [comparisonRules, setComparisonRules] = useState([
    { target_field_id: "", comparator_type: "EXACT", comparator_params: {}, ignore_field: false },
  ]);

  useEffect(() => {
    // Load existing configs once for reuse pickers
    const loadAll = async () => {
      const [sys, sch, ds, mp, rs] = await Promise.all([
        request("/api/v1/systems", {}, { toast: false }),
        request("/api/v1/schemas", {}, { toast: false }),
        request("/api/v1/datasets", {}, { toast: false }),
        request("/api/v1/mappings", {}, { toast: false }),
        request("/api/v1/rule-sets", {}, { toast: false }),
      ]);
      setSystems(Array.isArray(sys) ? sys : []);
      setSchemas(Array.isArray(sch) ? sch : []);
      setDatasets(Array.isArray(ds) ? ds : []);
      setMappings(Array.isArray(mp) ? mp : []);
      setRuleSets(Array.isArray(rs) ? rs : []);
    };
    loadAll().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const done = useMemo(
    () => ({
      system: Boolean(systemId),
      schema: Boolean(schemaId),
      datasets: Boolean(sourceDatasetId && targetDatasetId),
      mapping: Boolean(mappingId),
      ruleSet: Boolean(ruleSetId),
      job: Boolean(lastJobId),
    }),
    [systemId, schemaId, sourceDatasetId, targetDatasetId, mappingId, ruleSetId, lastJobId]
  );

  // --- Handlers ---

  const applyExistingSystem = async () => {
    if (!selectedSystemId) return;
    const sys = await request(`/api/v1/systems/${selectedSystemId}`, {}, { toast: false });
    setSystemId(sys.system_id);
    setSystemForm({
      system_id: sys.system_id || "",
      system_name: sys.system_name || "",
      system_type: sys.system_type || "FILE",
      description: sys.description || "",
    });
    setConnectionConfig(sys.connection_config || {});
  };

  const applyExistingSchema = async () => {
    if (!selectedSchemaId) return;
    const sch = await request(`/api/v1/schemas/${selectedSchemaId}`, {}, { toast: false });
    setSchemaId(sch.schema_id);
    setSchemaForm({ schema_id: sch.schema_id || "", schema_name: sch.schema_name || "" });
    const rawFields = Array.isArray(sch.fields) ? sch.fields : sch.fields?.fields || [];
    const fb = (rawFields || []).map((f) => {
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
    setSchemaFields(fb.length ? fb : [emptyField()]);
  };

  const applyExistingDatasets = async () => {
    if (!selectedSourceDatasetId || !selectedTargetDatasetId) return;
    const [src, tgt] = await Promise.all([
      request(`/api/v1/datasets/${selectedSourceDatasetId}`, {}, { toast: false }),
      request(`/api/v1/datasets/${selectedTargetDatasetId}`, {}, { toast: false }),
    ]);
    setSourceDatasetId(src.dataset_id);
    setTargetDatasetId(tgt.dataset_id);
    // Auto-fill upstream IDs if blank (common case when reusing)
    if (!systemId && src.system_id) setSystemId(src.system_id);
    if (!schemaId && src.schema_id) setSchemaId(src.schema_id);
    setDatasetForm((p) => ({
      ...p,
      source_dataset_id: src.dataset_id || "",
      source_dataset_name: src.dataset_name || "",
      target_dataset_id: tgt.dataset_id || "",
      target_dataset_name: tgt.dataset_name || "",
      physical_source: src.physical_name || p.physical_source,
      physical_target: tgt.physical_name || p.physical_target,
      dataset_type: src.dataset_type || p.dataset_type,
    }));
    setFilterConfig(src.filter_config || { has_header: true });
  };

  const applyExistingMapping = async () => {
    if (!selectedMappingId) return;
    const mp = await request(`/api/v1/mappings/${selectedMappingId}`, {}, { toast: false });
    setMappingId(mp.mapping_id);
    setMappingForm({ mapping_id: mp.mapping_id || "", mapping_name: mp.mapping_name || "" });
    // load field mappings for this mapping
    const fms = await request(`/api/v1/mappings/${selectedMappingId}/field-mappings`, {}, { toast: false });
    const list = (Array.isArray(fms) ? fms : []).map((fm) => ({
      target_field_id: fm.target_field_id || "",
      source_expression: fm.source_expression || "",
    }));
    setFieldMappings(list.length ? list : [{ target_field_id: "", source_expression: "" }]);
    // Auto-fill schema if blank
    if (!schemaId && mp.source_schema_id) setSchemaId(mp.source_schema_id);
  };

  const applyExistingRuleSet = async () => {
    if (!selectedRuleSetId) return;
    const rs = await request(`/api/v1/rule-sets/${selectedRuleSetId}`, {}, { toast: false });
    setRuleSetId(rs.rule_set_id);
    setRuleSetForm({
      rule_set_id: rs.rule_set_id || "",
      rule_set_name: rs.rule_set_name || "",
      matching_strategy: rs.matching_strategy || "EXACT",
    });
    // Auto-fill dependent IDs so the rest of the wizard can be skipped
    if (rs.source_dataset_id) setSourceDatasetId(rs.source_dataset_id);
    if (rs.target_dataset_id) setTargetDatasetId(rs.target_dataset_id);
    if (rs.mapping_id) setMappingId(rs.mapping_id);

    const mk = rs.matching_keys;
    if (Array.isArray(mk)) {
      setMatchingKeys(mk);
      setTrimWhitespace(false);
    } else if (mk && typeof mk === "object") {
      setMatchingKeys(Array.isArray(mk.keys) ? mk.keys : []);
      setTrimWhitespace(Boolean(mk.key_normalization?.trim_whitespace));
    }

    const rules = await request(`/api/v1/rule-sets/${selectedRuleSetId}/comparison-rules`, {}, { toast: false });
    const cr = (Array.isArray(rules) ? rules : []).map((r) => ({
      target_field_id: r.target_field_id || "",
      comparator_type: r.comparator_type || "EXACT",
      comparator_params: r.comparator_params || {},
      ignore_field: Boolean(r.ignore_field),
    }));
    setComparisonRules(cr.length ? cr : [{ target_field_id: "", comparator_type: "EXACT", comparator_params: {}, ignore_field: false }]);
  };

  const createSystem = async () => {
    const cleaned = { ...connectionConfig };
    Object.keys(cleaned).forEach((k) => {
      if (cleaned[k] === "" || cleaned[k] === null || cleaned[k] === undefined) delete cleaned[k];
    });
    const payload = {
      ...systemForm,
      connection_config: cleaned,
    };
    const res = await request("/api/v1/systems", {
      method: "POST",
      body: JSON.stringify(payload),
    }, { successMessage: "System created" });
    if (res?.system_id) setSystemId(res.system_id);
  };

  const createSchema = async () => {
    const fields = schemaFields.map((f) => {
      const out = {
        field_id: f.field_id,
        field_name: f.field_name,
        data_type: f.data_type,
        is_nullable: f.is_nullable,
        is_key: f.is_key,
        physical_mapping: { [f.physical_mapping_type]: f.physical_mapping_value },
      };
      if (f.data_type === "DECIMAL") {
        out.precision = f.precision;
        out.scale = f.scale;
      }
      return out;
    });
    const payload = {
      schema_id: schemaForm.schema_id,
      schema_name: schemaForm.schema_name,
      fields: { fields },
      constraints: {},
    };
    const res = await request("/api/v1/schemas", {
      method: "POST",
      body: JSON.stringify(payload),
    }, { successMessage: "Schema created" });
    if (res?.schema_id) setSchemaId(res.schema_id);
  };

  const createDatasets = async () => {
    const src = await request("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: datasetForm.source_dataset_id,
        dataset_name: datasetForm.source_dataset_name,
        system_id: systemId,
        schema_id: schemaId,
        physical_name: datasetForm.physical_source,
        dataset_type: datasetForm.dataset_type,
        filter_config: filterConfig,
        metadata: {},
      }),
    }, { successMessage: "Source dataset created" });

    const tgt = await request("/api/v1/datasets", {
      method: "POST",
      body: JSON.stringify({
        dataset_id: datasetForm.target_dataset_id,
        dataset_name: datasetForm.target_dataset_name,
        system_id: systemId,
        schema_id: schemaId,
        physical_name: datasetForm.physical_target,
        dataset_type: datasetForm.dataset_type,
        filter_config: filterConfig,
        metadata: {},
      }),
    }, { successMessage: "Target dataset created" });

    if (src?.dataset_id) setSourceDatasetId(src.dataset_id);
    if (tgt?.dataset_id) setTargetDatasetId(tgt.dataset_id);
  };

  const createMappingAndFields = async () => {
    const res = await request("/api/v1/mappings", {
      method: "POST",
      body: JSON.stringify({
        ...mappingForm,
        source_schema_id: schemaId,
        target_schema_id: schemaId,
      }),
    }, { successMessage: "Mapping created" });
    if (res?.mapping_id) setMappingId(res.mapping_id);

    for (const fm of fieldMappings) {
      if (!fm.target_field_id) continue;
      await request(`/api/v1/mappings/${res.mapping_id}/field-mappings`, {
        method: "POST",
        body: JSON.stringify({
          mapping_id: res.mapping_id,
          target_field_id: fm.target_field_id,
          source_expression: fm.source_expression,
          transform_chain: { steps: [] },
          pre_validations: { validations: [] },
          post_validations: { validations: [] },
          is_active: true,
        }),
      }, { successMessage: `Field mapping: ${fm.target_field_id}` });
    }
  };

  const createRuleSetAndRules = async () => {
    const rs = await request("/api/v1/rule-sets", {
      method: "POST",
      body: JSON.stringify({
        rule_set_id: ruleSetForm.rule_set_id,
        rule_set_name: ruleSetForm.rule_set_name,
        source_dataset_id: sourceDatasetId,
        target_dataset_id: targetDatasetId,
        mapping_id: mappingId,
        matching_strategy: ruleSetForm.matching_strategy,
        matching_keys: {
          keys: matchingKeys,
          key_normalization: { trim_whitespace: trimWhitespace },
        },
        scope_config: {},
        tolerance_config: {},
      }),
    }, { successMessage: "Rule set created" });
    if (rs?.rule_set_id) setRuleSetId(rs.rule_set_id);

    for (const r of comparisonRules) {
      if (!r.target_field_id) continue;
      await request(`/api/v1/rule-sets/${rs.rule_set_id}/comparison-rules`, {
        method: "POST",
        body: JSON.stringify({
          rule_set_id: rs.rule_set_id,
          target_field_id: r.target_field_id,
          comparator_type: r.comparator_type,
          comparator_params: r.comparator_params || {},
          ignore_field: Boolean(r.ignore_field),
          is_active: true,
        }),
      }, { successMessage: `Rule: ${r.target_field_id}` });
    }
  };

  const runJob = async () => {
    const job = await request("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify({ rule_set_id: ruleSetId, filters: {} }),
    }, { successMessage: "Job started" });
    if (job?.job_id) setLastJobId(job.job_id);
  };

  const sysField = (key) => (e) => setSystemForm((p) => ({ ...p, [key]: e.target.value }));
  const schField = (key) => (e) => setSchemaForm((p) => ({ ...p, [key]: e.target.value }));
  const dsField = (key) => (e) => setDatasetForm((p) => ({ ...p, [key]: e.target.value }));
  const mapField = (key) => (e) => setMappingForm((p) => ({ ...p, [key]: e.target.value }));
  const rsField = (key) => (e) => setRuleSetForm((p) => ({ ...p, [key]: e.target.value }));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>New Reconciliation</h1>
          <p className="muted">Step-by-step wizard. Expand each step, fill in details, and create.</p>
        </div>
        <div className="actions">
          <Link className="button button-secondary" to="/configs">Back to Configs</Link>
          {lastJobId && (
            <button type="button" onClick={() => navigate(`/results/${lastJobId}`)}>
              View Results
            </button>
          )}
        </div>
      </div>

      <div className="steps">
        <StepBadge idx={1} title="System" done={done.system} />
        <StepBadge idx={2} title="Schema" done={done.schema} />
        <StepBadge idx={3} title="Datasets" done={done.datasets} />
        <StepBadge idx={4} title="Mapping" done={done.mapping} />
        <StepBadge idx={5} title="Rule Set" done={done.ruleSet} />
        <StepBadge idx={6} title="Run Job" done={done.job} />
      </div>

      {/* --- Step 1: System --- */}
      <Collapsible
        title="1) System"
        subtitle={systemId ? `Created: ${systemId}` : "Define the data source connection"}
        defaultOpen
      >
        <div className="card" style={{ marginBottom: 12 }}>
          <label className="field field-inline-check">
            <input
              type="checkbox"
              checked={useExistingSystem}
              onChange={(e) => setUseExistingSystem(e.target.checked)}
            />
            <span>Use existing system</span>
          </label>
          {useExistingSystem ? (
            <div className="form-grid">
              <ExistingPicker
                label="Existing Systems"
                items={systems}
                value={selectedSystemId}
                onChange={setSelectedSystemId}
                getId={(s) => s.system_id}
                getName={(s) => s.system_name}
                getMeta={(s) => s.system_type}
              />
              <div className="actions" style={{ alignSelf: "end" }}>
                <button type="button" className="button" disabled={!selectedSystemId || loading} onClick={applyExistingSystem}>
                  Use Selected
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Create a new system if you haven’t created one yet.
            </p>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>System ID *</span>
            <HelpText>A unique identifier for this system (e.g. "file_local", "oracle_prod").</HelpText>
            <input value={systemForm.system_id} onChange={sysField("system_id")} placeholder="file_local" />
          </label>
          <label className="field">
            <span>Name *</span>
            <input value={systemForm.system_name} onChange={sysField("system_name")} placeholder="Local Files" />
          </label>
          <label className="field">
            <span>Type *</span>
            <HelpText>Choose the type of data source you are connecting to.</HelpText>
            <select
              value={systemForm.system_type}
              onChange={(e) => {
                setSystemForm((p) => ({ ...p, system_type: e.target.value }));
                setConnectionConfig({});
              }}
            >
              <option value="FILE">FILE - Local CSV / JSON files</option>
              <option value="ORACLE">ORACLE - Oracle Database</option>
              <option value="MONGODB">MONGODB - MongoDB</option>
              <option value="API">API - REST API Endpoint</option>
            </select>
          </label>
          <label className="field">
            <span>Description</span>
            <input value={systemForm.description} onChange={sysField("description")} placeholder="Optional description" />
          </label>
        </div>
        <ConnectionConfigForm
          systemType={systemForm.system_type}
          value={connectionConfig}
          onChange={setConnectionConfig}
        />
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" onClick={createSystem} disabled={loading}>
            Create System
          </button>
        </div>
      </Collapsible>

      {/* --- Step 2: Schema --- */}
      <Collapsible
        title="2) Schema"
        subtitle={schemaId ? `Created: ${schemaId}` : "Define the fields and data types"}
        defaultOpen={false}
      >
        <div className="card" style={{ marginBottom: 12 }}>
          <label className="field field-inline-check">
            <input
              type="checkbox"
              checked={useExistingSchema}
              onChange={(e) => setUseExistingSchema(e.target.checked)}
            />
            <span>Use existing schema</span>
          </label>
          {useExistingSchema ? (
            <div className="form-grid">
              <ExistingPicker
                label="Existing Schemas"
                items={schemas}
                value={selectedSchemaId}
                onChange={setSelectedSchemaId}
                getId={(s) => s.schema_id}
                getName={(s) => s.schema_name}
              />
              <div className="actions" style={{ alignSelf: "end" }}>
                <button type="button" className="button" disabled={!selectedSchemaId || loading} onClick={applyExistingSchema}>
                  Use Selected
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Create a new schema to define fields and types.
            </p>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Schema ID *</span>
            <input value={schemaForm.schema_id} onChange={schField("schema_id")} placeholder="csv_records_schema" />
          </label>
          <label className="field">
            <span>Name *</span>
            <input value={schemaForm.schema_name} onChange={schField("schema_name")} placeholder="CSV Records Schema" />
          </label>
        </div>
        <FieldBuilder fields={schemaFields} onChange={setSchemaFields} />
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" onClick={createSchema} disabled={!systemId || loading}>
            Create Schema
          </button>
        </div>
      </Collapsible>

      {/* --- Step 3: Datasets --- */}
      <Collapsible
        title="3) Datasets"
        subtitle={done.datasets ? `Source: ${sourceDatasetId} / Target: ${targetDatasetId}` : "Create source and target datasets"}
        defaultOpen={false}
      >
        <div className="card" style={{ marginBottom: 12 }}>
          <label className="field field-inline-check">
            <input
              type="checkbox"
              checked={useExistingDatasets}
              onChange={(e) => setUseExistingDatasets(e.target.checked)}
            />
            <span>Use existing datasets</span>
          </label>
          {useExistingDatasets ? (
            <div className="grid two">
              <ExistingPicker
                label="Existing Source Dataset"
                items={datasets}
                value={selectedSourceDatasetId}
                onChange={setSelectedSourceDatasetId}
                getId={(d) => d.dataset_id}
                getName={(d) => d.dataset_name}
                getMeta={(d) => d.dataset_type}
              />
              <ExistingPicker
                label="Existing Target Dataset"
                items={datasets}
                value={selectedTargetDatasetId}
                onChange={setSelectedTargetDatasetId}
                getId={(d) => d.dataset_id}
                getName={(d) => d.dataset_name}
                getMeta={(d) => d.dataset_type}
              />
              <div className="actions">
                <button
                  type="button"
                  className="button"
                  disabled={!selectedSourceDatasetId || !selectedTargetDatasetId || loading}
                  onClick={applyExistingDatasets}
                >
                  Use Selected
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Create source + target datasets (or reuse existing).
            </p>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Source Dataset ID *</span>
            <input value={datasetForm.source_dataset_id} onChange={dsField("source_dataset_id")} placeholder="csv_source" />
          </label>
          <label className="field">
            <span>Source Name *</span>
            <input value={datasetForm.source_dataset_name} onChange={dsField("source_dataset_name")} placeholder="CSV Source" />
          </label>
          <label className="field">
            <span>Target Dataset ID *</span>
            <input value={datasetForm.target_dataset_id} onChange={dsField("target_dataset_id")} placeholder="csv_target" />
          </label>
          <label className="field">
            <span>Target Name *</span>
            <input value={datasetForm.target_dataset_name} onChange={dsField("target_dataset_name")} placeholder="CSV Target" />
          </label>
          <label className="field">
            <span>Source File / Table Name *</span>
            <HelpText>Physical name of the source (filename for FILE, table name for DB).</HelpText>
            <input value={datasetForm.physical_source} onChange={dsField("physical_source")} placeholder="source.csv" />
          </label>
          <label className="field">
            <span>Target File / Table Name *</span>
            <input value={datasetForm.physical_target} onChange={dsField("physical_target")} placeholder="target.csv" />
          </label>
          <label className="field">
            <span>Dataset Type</span>
            <select value={datasetForm.dataset_type} onChange={dsField("dataset_type")}>
              <option value="FILE">FILE</option>
              <option value="TABLE">TABLE</option>
              <option value="COLLECTION">COLLECTION</option>
              <option value="VIEW">VIEW</option>
            </select>
          </label>
        </div>
        <h4 style={{ margin: "16px 0 8px" }}>Filter Options</h4>
        <FilterConfigForm
          systemType={systemForm.system_type}
          value={filterConfig}
          onChange={setFilterConfig}
        />
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" onClick={createDatasets} disabled={!systemId || !schemaId || loading}>
            Create Datasets
          </button>
        </div>
      </Collapsible>

      {/* --- Step 4: Mapping --- */}
      <Collapsible
        title="4) Mapping"
        subtitle={mappingId ? `Created: ${mappingId}` : "Map source fields to target fields"}
        defaultOpen={false}
      >
        <div className="card" style={{ marginBottom: 12 }}>
          <label className="field field-inline-check">
            <input
              type="checkbox"
              checked={useExistingMapping}
              onChange={(e) => setUseExistingMapping(e.target.checked)}
            />
            <span>Use existing mapping</span>
          </label>
          {useExistingMapping ? (
            <div className="form-grid">
              <ExistingPicker
                label="Existing Mappings"
                items={mappings}
                value={selectedMappingId}
                onChange={setSelectedMappingId}
                getId={(m) => m.mapping_id}
                getName={(m) => m.mapping_name}
              />
              <div className="actions" style={{ alignSelf: "end" }}>
                <button type="button" className="button" disabled={!selectedMappingId || loading} onClick={applyExistingMapping}>
                  Use Selected
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Create a mapping + field mappings (or reuse existing).
            </p>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Mapping ID *</span>
            <input value={mappingForm.mapping_id} onChange={mapField("mapping_id")} placeholder="file_mapping" />
          </label>
          <label className="field">
            <span>Name *</span>
            <input value={mappingForm.mapping_name} onChange={mapField("mapping_name")} placeholder="File to File Mapping" />
          </label>
        </div>
        <h4 style={{ margin: "16px 0 8px" }}>Field Mappings</h4>
        <MappingBuilder mappings={fieldMappings} onChange={setFieldMappings} />
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" onClick={createMappingAndFields} disabled={!schemaId || loading}>
            Create Mapping + Fields
          </button>
        </div>
      </Collapsible>

      {/* --- Step 5: Rule Set --- */}
      <Collapsible
        title="5) Rule Set"
        subtitle={ruleSetId ? `Created: ${ruleSetId}` : "Configure matching and comparison rules"}
        defaultOpen={false}
      >
        <div className="card" style={{ marginBottom: 12 }}>
          <label className="field field-inline-check">
            <input
              type="checkbox"
              checked={useExistingRuleSet}
              onChange={(e) => setUseExistingRuleSet(e.target.checked)}
            />
            <span>Use existing rule set</span>
          </label>
          {useExistingRuleSet ? (
            <div className="form-grid">
              <ExistingPicker
                label="Existing Rule Sets"
                items={ruleSets}
                value={selectedRuleSetId}
                onChange={setSelectedRuleSetId}
                getId={(r) => r.rule_set_id}
                getName={(r) => r.rule_set_name}
                getMeta={(r) => r.matching_strategy}
              />
              <div className="actions" style={{ alignSelf: "end" }}>
                <button type="button" className="button" disabled={!selectedRuleSetId || loading} onClick={applyExistingRuleSet}>
                  Use Selected
                </button>
              </div>
            </div>
          ) : (
            <p className="muted" style={{ margin: 0 }}>
              Create a new rule set (or reuse an existing one).
            </p>
          )}
        </div>
        <div className="form-grid">
          <label className="field">
            <span>Rule Set ID *</span>
            <input value={ruleSetForm.rule_set_id} onChange={rsField("rule_set_id")} placeholder="csv_recon" />
          </label>
          <label className="field">
            <span>Name *</span>
            <input value={ruleSetForm.rule_set_name} onChange={rsField("rule_set_name")} placeholder="CSV Reconciliation" />
          </label>
          <label className="field">
            <span>Matching Strategy</span>
            <HelpText>EXACT: records must match on exact key values. FUZZY: approximate matching.</HelpText>
            <select value={ruleSetForm.matching_strategy} onChange={rsField("matching_strategy")}>
              <option value="EXACT">EXACT - Exact key match</option>
              <option value="FUZZY">FUZZY - Approximate match</option>
            </select>
          </label>
        </div>

        <h4 style={{ margin: "16px 0 8px" }}>Matching Keys</h4>
        <MatchingKeyBuilder
          keys={matchingKeys}
          trimWhitespace={trimWhitespace}
          onChange={setMatchingKeys}
          onTrimChange={setTrimWhitespace}
        />

        <h4 style={{ margin: "16px 0 8px" }}>Comparison Rules</h4>
        <ComparisonRuleBuilder rules={comparisonRules} onChange={setComparisonRules} />

        <div className="actions" style={{ marginTop: 12 }}>
          <button
            type="button"
            onClick={createRuleSetAndRules}
            disabled={!sourceDatasetId || !targetDatasetId || !mappingId || loading}
          >
            Create Rule Set + Rules
          </button>
        </div>
      </Collapsible>

      {/* --- Step 6: Run --- */}
      <Collapsible
        title="6) Run Job"
        subtitle={lastJobId ? `Last job: ${lastJobId}` : "Execute the reconciliation"}
        defaultOpen={false}
      >
        <HelpText>Once all config entities are created, run the job to start reconciliation.</HelpText>
        <div className="actions" style={{ marginTop: 8 }}>
          <button type="button" onClick={runJob} disabled={!ruleSetId || loading}>
            Run Job
          </button>
          {lastJobId && (
            <button type="button" className="button button-secondary" onClick={() => navigate(`/results/${lastJobId}`)}>
              Open Results
            </button>
          )}
        </div>
      </Collapsible>
    </div>
  );
}
