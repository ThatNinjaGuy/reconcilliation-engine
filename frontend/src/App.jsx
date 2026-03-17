import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { DiffView } from "./DiffView.jsx";
import ResultsPage from "./ResultsPage.jsx";

const Section = ({ title, description, children }) => (
  <section className="section">
    <div className="section-header">
      <div>
        <h2>{title}</h2>
        {description ? <p className="muted">{description}</p> : null}
      </div>
    </div>
    <div className="section-body">{children}</div>
  </section>
);

const ResponsePanel = ({ label, data }) => (
  <div className="response">
    <div className="response-title">{label}</div>
    <pre>{data ? JSON.stringify(data, null, 2) : "No response yet."}</pre>
  </div>
);

function App() {
  const [route, setRoute] = useState(() =>
    window.location.pathname.startsWith("/results") ? "results" : "console"
  );

  // lightweight path router (no deps)
  useEffect(() => {
    const onNav = () => {
      setRoute(window.location.pathname.startsWith("/results") ? "results" : "console");
    };
    window.addEventListener("popstate", onNav);
    return () => window.removeEventListener("popstate", onNav);
  }, []);

  if (route === "results") {
    return <ResultsPage />;
  }

  const [baseUrl, setBaseUrl] = useState(
    () => localStorage.getItem("genrecon.baseUrl") || "http://localhost:8000"
  );
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("genrecon.apiKey") || ""
  );
  const [status, setStatus] = useState(null);
  const [responses, setResponses] = useState({});

  const headers = useMemo(() => {
    const base = {};
    if (apiKey) {
      base.Authorization = `Bearer ${apiKey}`;
    }
    return base;
  }, [apiKey]);

  const saveConnection = () => {
    localStorage.setItem("genrecon.baseUrl", baseUrl);
    localStorage.setItem("genrecon.apiKey", apiKey);
    setStatus({ type: "success", message: "Connection settings saved." });
  };

  const parseJson = (value, fallback = {}) => {
    if (!value || !value.trim()) {
      return fallback;
    }
    return JSON.parse(value);
  };

  const request = async (key, path, options = {}) => {
    const url = `${baseUrl}${path}`;
    setStatus({ type: "info", message: `Requesting ${path}...` });
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          ...headers,
          ...options.headers,
          ...(options.body ? { "Content-Type": "application/json" } : {}),
        },
      });
      const isJson = response.headers
        .get("content-type")
        ?.includes("application/json");
      const payload = isJson ? await response.json() : await response.text();
      if (!response.ok) {
        throw new Error(
          payload?.detail || payload?.error?.message || "Request failed"
        );
      }
      setResponses((prev) => ({ ...prev, [key]: payload }));
      setStatus({ type: "success", message: "Request completed." });
      return payload;
    } catch (error) {
      setStatus({ type: "error", message: error.message });
      throw error;
    }
  };

  const [systemForm, setSystemForm] = useState({
    system_id: "",
    system_name: "",
    system_type: "ORACLE",
    description: "",
    connection_config:
      '{\n  "host": "",\n  "port": 1521,\n  "service_name": "",\n  "username": "",\n  "password": ""\n}',
  });
  const [systemUpdateId, setSystemUpdateId] = useState("");
  const [systemUpdateJson, setSystemUpdateJson] = useState(
    '{\n  "description": ""\n}'
  );
  const [systemGetId, setSystemGetId] = useState("");
  const [systemDeleteId, setSystemDeleteId] = useState("");

  const [schemaForm, setSchemaForm] = useState({
    schema_id: "",
    schema_name: "",
    fields: '{\n  "fields": []\n}',
    constraints: "{}",
  });
  const [schemaUpdateId, setSchemaUpdateId] = useState("");
  const [schemaUpdateJson, setSchemaUpdateJson] = useState(
    '{\n  "description": ""\n}'
  );
  const [schemaGetId, setSchemaGetId] = useState("");
  const [schemaDeleteId, setSchemaDeleteId] = useState("");

  const [datasetForm, setDatasetForm] = useState({
    dataset_id: "",
    dataset_name: "",
    system_id: "",
    schema_id: "",
    physical_name: "",
    dataset_type: "TABLE",
    partition_config: "{}",
    filter_config: "{}",
    metadata: "{}",
  });
  const [datasetUpdateId, setDatasetUpdateId] = useState("");
  const [datasetUpdateJson, setDatasetUpdateJson] = useState(
    '{\n  "dataset_name": ""\n}'
  );
  const [datasetGetId, setDatasetGetId] = useState("");
  const [datasetDeleteId, setDatasetDeleteId] = useState("");

  const [mappingForm, setMappingForm] = useState({
    mapping_id: "",
    mapping_name: "",
    source_schema_id: "",
    target_schema_id: "",
    description: "",
  });
  const [mappingUpdateId, setMappingUpdateId] = useState("");
  const [mappingUpdateJson, setMappingUpdateJson] = useState(
    '{\n  "description": ""\n}'
  );
  const [mappingDeleteId, setMappingDeleteId] = useState("");

  const [fieldMappingForm, setFieldMappingForm] = useState({
    mapping_id: "",
    target_field_id: "",
    source_expression: "",
    transform_chain: '{\n  "steps": []\n}',
    pre_validations: '{\n  "validations": []\n}',
    post_validations: '{\n  "validations": []\n}',
    is_active: true,
  });
  const [fieldMappingUpdateId, setFieldMappingUpdateId] = useState("");
  const [fieldMappingUpdateJson, setFieldMappingUpdateJson] = useState(
    '{\n  "source_expression": ""\n}'
  );
  const [fieldMappingDeleteId, setFieldMappingDeleteId] = useState("");

  const [ruleSetForm, setRuleSetForm] = useState({
    rule_set_id: "",
    rule_set_name: "",
    source_dataset_id: "",
    target_dataset_id: "",
    mapping_id: "",
    matching_strategy: "EXACT",
    matching_keys: '{\n  "keys": []\n}',
    scope_config: "{}",
    tolerance_config: "{}",
  });
  const [ruleSetUpdateId, setRuleSetUpdateId] = useState("");
  const [ruleSetUpdateJson, setRuleSetUpdateJson] = useState(
    '{\n  "rule_set_name": ""\n}'
  );
  const [ruleSetDeleteId, setRuleSetDeleteId] = useState("");

  const [comparisonRuleForm, setComparisonRuleForm] = useState({
    rule_set_id: "",
    target_field_id: "",
    comparator_type: "EXACT",
    comparator_params: "{}",
    ignore_field: false,
  });

  const [referenceForm, setReferenceForm] = useState({
    reference_dataset_id: "",
    reference_name: "",
    source_type: "CSV",
    source_config: '{\n  "file_path": ""\n}',
    key_fields: '{\n  "fields": []\n}',
    value_fields: "{}",
    cache_config: "{}",
  });
  const [referenceUpdateId, setReferenceUpdateId] = useState("");
  const [referenceUpdateJson, setReferenceUpdateJson] = useState(
    '{\n  "description": ""\n}'
  );
  const [referenceDeleteId, setReferenceDeleteId] = useState("");

  const [jobRuleSetId, setJobRuleSetId] = useState("");
  const [jobFilters, setJobFilters] = useState("{}");
  const [jobIdLookup, setJobIdLookup] = useState("");

  const [resultsJobId, setResultsJobId] = useState("");
  const [resultsFieldId, setResultsFieldId] = useState("");
  const [resultsSeverity, setResultsSeverity] = useState("");
  const [resultsLimit, setResultsLimit] = useState(100);
  const [resultsOffset, setResultsOffset] = useState(0);

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>GenRecon Console</h1>
          <p className="muted">
            Configure systems, schemas, mappings, and run reconciliations.
          </p>
        </div>
        <div className="actions">
          <button
            type="button"
            onClick={() => {
              window.history.pushState({}, "", "/results");
              setRoute("results");
            }}
          >
            Results Page
          </button>
        </div>
        <div className={`status ${status?.type || ""}`}>
          {status?.message || "Ready."}
        </div>
      </header>

      <Section
        title="Connection"
        description="Configure the backend URL and API key."
      >
        <div className="form-grid">
          <div className="field">
            <label>Base URL</label>
            <input
              value={baseUrl}
              onChange={(event) => setBaseUrl(event.target.value)}
              placeholder="http://localhost:8000"
            />
          </div>
          <div className="field">
            <label>API Key</label>
            <input
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Optional"
            />
          </div>
        </div>
        <div className="actions">
          <button onClick={saveConnection}>Save</button>
          <button onClick={() => request("health", "/health")}>
            Health Check
          </button>
        </div>
        <ResponsePanel label="Health" data={responses.health} />
      </Section>

      <Section
        title="Systems"
        description="Register source and target systems."
      >
        <div className="grid two">
          <div className="card">
            <h3>Create System</h3>
            <div className="field">
              <label>System ID</label>
              <input
                value={systemForm.system_id}
                onChange={(event) =>
                  setSystemForm((prev) => ({
                    ...prev,
                    system_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={systemForm.system_name}
                onChange={(event) =>
                  setSystemForm((prev) => ({
                    ...prev,
                    system_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Type</label>
              <select
                value={systemForm.system_type}
                onChange={(event) =>
                  setSystemForm((prev) => ({
                    ...prev,
                    system_type: event.target.value,
                  }))
                }
              >
                <option value="ORACLE">ORACLE</option>
                <option value="MONGODB">MONGODB</option>
                <option value="FILE">FILE</option>
                <option value="API">API</option>
              </select>
            </div>
            <div className="field">
              <label>Description</label>
              <input
                value={systemForm.description}
                onChange={(event) =>
                  setSystemForm((prev) => ({
                    ...prev,
                    description: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Connection Config (JSON)</label>
              <textarea
                value={systemForm.connection_config}
                onChange={(event) =>
                  setSystemForm((prev) => ({
                    ...prev,
                    connection_config: event.target.value,
                  }))
                }
                rows={7}
              />
            </div>
            <button
              onClick={() =>
                request("systemsCreate", "/api/v1/systems", {
                  method: "POST",
                  body: JSON.stringify({
                    ...systemForm,
                    connection_config: parseJson(systemForm.connection_config),
                  }),
                })
              }
            >
              Create
            </button>
          </div>

          <div className="card">
            <h3>Manage Systems</h3>
            <div className="field">
              <label>System ID</label>
              <input
                value={systemGetId}
                onChange={(event) => setSystemGetId(event.target.value)}
                placeholder="Lookup ID"
              />
            </div>
            <div className="actions">
              <button onClick={() => request("systemsList", "/api/v1/systems")}>
                List
              </button>
              <button
                onClick={() =>
                  request("systemsGet", `/api/v1/systems/${systemGetId}`)
                }
              >
                Get
              </button>
              <button
                onClick={() =>
                  request(
                    "systemsTest",
                    `/api/v1/systems/${systemGetId}/test`,
                    { method: "POST" }
                  )
                }
              >
                Test
              </button>
            </div>
            <div className="divider" />
            <div className="field">
              <label>Update ID</label>
              <input
                value={systemUpdateId}
                onChange={(event) => setSystemUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={systemUpdateJson}
                onChange={(event) => setSystemUpdateJson(event.target.value)}
                rows={5}
              />
            </div>
            <button
              onClick={() =>
                request("systemsUpdate", `/api/v1/systems/${systemUpdateId}`, {
                  method: "PUT",
                  body: JSON.stringify(parseJson(systemUpdateJson)),
                })
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={systemDeleteId}
                onChange={(event) => setSystemDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request("systemsDelete", `/api/v1/systems/${systemDeleteId}`, {
                  method: "DELETE",
                })
              }
            >
              Delete
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Systems Response"
          data={
            responses.systemsList ||
            responses.systemsGet ||
            responses.systemsCreate ||
            responses.systemsUpdate ||
            responses.systemsTest
          }
        />
      </Section>

      <Section
        title="Schemas"
        description="Define logical schemas for datasets."
      >
        <div className="grid two">
          <div className="card">
            <h3>Create Schema</h3>
            <div className="field">
              <label>Schema ID</label>
              <input
                value={schemaForm.schema_id}
                onChange={(event) =>
                  setSchemaForm((prev) => ({
                    ...prev,
                    schema_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={schemaForm.schema_name}
                onChange={(event) =>
                  setSchemaForm((prev) => ({
                    ...prev,
                    schema_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Fields (JSON)</label>
              <textarea
                value={schemaForm.fields}
                onChange={(event) =>
                  setSchemaForm((prev) => ({
                    ...prev,
                    fields: event.target.value,
                  }))
                }
                rows={7}
              />
            </div>
            <div className="field">
              <label>Constraints (JSON)</label>
              <textarea
                value={schemaForm.constraints}
                onChange={(event) =>
                  setSchemaForm((prev) => ({
                    ...prev,
                    constraints: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request("schemasCreate", "/api/v1/schemas", {
                  method: "POST",
                  body: JSON.stringify({
                    schema_id: schemaForm.schema_id,
                    schema_name: schemaForm.schema_name,
                    fields: parseJson(schemaForm.fields, { fields: [] }),
                    constraints: parseJson(schemaForm.constraints, {}),
                  }),
                })
              }
            >
              Create
            </button>
          </div>
          <div className="card">
            <h3>Manage Schemas</h3>
            <div className="field">
              <label>Schema ID</label>
              <input
                value={schemaGetId}
                onChange={(event) => setSchemaGetId(event.target.value)}
              />
            </div>
            <div className="actions">
              <button onClick={() => request("schemasList", "/api/v1/schemas")}>
                List
              </button>
              <button
                onClick={() =>
                  request("schemasGet", `/api/v1/schemas/${schemaGetId}`)
                }
              >
                Get
              </button>
              <button
                onClick={() =>
                  request(
                    "schemasValidate",
                    `/api/v1/schemas/${schemaGetId}/validate`,
                    { method: "POST" }
                  )
                }
              >
                Validate
              </button>
            </div>
            <div className="divider" />
            <div className="field">
              <label>Update ID</label>
              <input
                value={schemaUpdateId}
                onChange={(event) => setSchemaUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={schemaUpdateJson}
                onChange={(event) => setSchemaUpdateJson(event.target.value)}
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request("schemasUpdate", `/api/v1/schemas/${schemaUpdateId}`, {
                  method: "PUT",
                  body: JSON.stringify(parseJson(schemaUpdateJson)),
                })
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={schemaDeleteId}
                onChange={(event) => setSchemaDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request("schemasDelete", `/api/v1/schemas/${schemaDeleteId}`, {
                  method: "DELETE",
                })
              }
            >
              Delete
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Schemas Response"
          data={
            responses.schemasList ||
            responses.schemasGet ||
            responses.schemasCreate ||
            responses.schemasUpdate ||
            responses.schemasValidate
          }
        />
      </Section>

      <Section title="Datasets" description="Register physical datasets.">
        <div className="grid two">
          <div className="card">
            <h3>Create Dataset</h3>
            <div className="field">
              <label>Dataset ID</label>
              <input
                value={datasetForm.dataset_id}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    dataset_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={datasetForm.dataset_name}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    dataset_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>System ID</label>
              <input
                value={datasetForm.system_id}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    system_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Schema ID</label>
              <input
                value={datasetForm.schema_id}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    schema_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Physical Name</label>
              <input
                value={datasetForm.physical_name}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    physical_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Dataset Type</label>
              <select
                value={datasetForm.dataset_type}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    dataset_type: event.target.value,
                  }))
                }
              >
                <option value="TABLE">TABLE</option>
                <option value="COLLECTION">COLLECTION</option>
                <option value="VIEW">VIEW</option>
                <option value="FILE">FILE</option>
              </select>
            </div>
            <div className="field">
              <label>Partition Config (JSON)</label>
              <textarea
                value={datasetForm.partition_config}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    partition_config: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Filter Config (JSON)</label>
              <textarea
                value={datasetForm.filter_config}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    filter_config: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Metadata (JSON)</label>
              <textarea
                value={datasetForm.metadata}
                onChange={(event) =>
                  setDatasetForm((prev) => ({
                    ...prev,
                    metadata: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request("datasetsCreate", "/api/v1/datasets", {
                  method: "POST",
                  body: JSON.stringify({
                    dataset_id: datasetForm.dataset_id,
                    dataset_name: datasetForm.dataset_name,
                    system_id: datasetForm.system_id,
                    schema_id: datasetForm.schema_id,
                    physical_name: datasetForm.physical_name,
                    dataset_type: datasetForm.dataset_type,
                    partition_config: parseJson(
                      datasetForm.partition_config,
                      {}
                    ),
                    filter_config: parseJson(datasetForm.filter_config, {}),
                    metadata: parseJson(datasetForm.metadata, {}),
                  }),
                })
              }
            >
              Create
            </button>
          </div>
          <div className="card">
            <h3>Manage Datasets</h3>
            <div className="field">
              <label>Dataset ID</label>
              <input
                value={datasetGetId}
                onChange={(event) => setDatasetGetId(event.target.value)}
              />
            </div>
            <div className="actions">
              <button
                onClick={() => request("datasetsList", "/api/v1/datasets")}
              >
                List
              </button>
              <button
                onClick={() =>
                  request("datasetsGet", `/api/v1/datasets/${datasetGetId}`)
                }
              >
                Get
              </button>
              <button
                onClick={() =>
                  request(
                    "datasetsSample",
                    `/api/v1/datasets/${datasetGetId}/sample`
                  )
                }
              >
                Sample
              </button>
              <button
                onClick={() =>
                  request(
                    "datasetsValidate",
                    `/api/v1/datasets/${datasetGetId}/validate`,
                    { method: "POST" }
                  )
                }
              >
                Validate
              </button>
            </div>
            <div className="divider" />
            <div className="field">
              <label>Update ID</label>
              <input
                value={datasetUpdateId}
                onChange={(event) => setDatasetUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={datasetUpdateJson}
                onChange={(event) => setDatasetUpdateJson(event.target.value)}
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "datasetsUpdate",
                  `/api/v1/datasets/${datasetUpdateId}`,
                  {
                    method: "PUT",
                    body: JSON.stringify(parseJson(datasetUpdateJson)),
                  }
                )
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={datasetDeleteId}
                onChange={(event) => setDatasetDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request(
                  "datasetsDelete",
                  `/api/v1/datasets/${datasetDeleteId}`,
                  { method: "DELETE" }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Datasets Response"
          data={
            responses.datasetsList ||
            responses.datasetsGet ||
            responses.datasetsCreate ||
            responses.datasetsUpdate ||
            responses.datasetsValidate ||
            responses.datasetsSample
          }
        />
      </Section>

      <Section
        title="Mappings"
        description="Define mappings and transformations."
      >
        <div className="grid two">
          <div className="card">
            <h3>Create Mapping</h3>
            <div className="field">
              <label>Mapping ID</label>
              <input
                value={mappingForm.mapping_id}
                onChange={(event) =>
                  setMappingForm((prev) => ({
                    ...prev,
                    mapping_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={mappingForm.mapping_name}
                onChange={(event) =>
                  setMappingForm((prev) => ({
                    ...prev,
                    mapping_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Source Schema ID</label>
              <input
                value={mappingForm.source_schema_id}
                onChange={(event) =>
                  setMappingForm((prev) => ({
                    ...prev,
                    source_schema_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Target Schema ID</label>
              <input
                value={mappingForm.target_schema_id}
                onChange={(event) =>
                  setMappingForm((prev) => ({
                    ...prev,
                    target_schema_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Description</label>
              <input
                value={mappingForm.description}
                onChange={(event) =>
                  setMappingForm((prev) => ({
                    ...prev,
                    description: event.target.value,
                  }))
                }
              />
            </div>
            <button
              onClick={() =>
                request("mappingsCreate", "/api/v1/mappings", {
                  method: "POST",
                  body: JSON.stringify(mappingForm),
                })
              }
            >
              Create
            </button>
          </div>
          <div className="card">
            <h3>Manage Mappings</h3>
            <div className="actions">
              <button
                onClick={() => request("mappingsList", "/api/v1/mappings")}
              >
                List
              </button>
            </div>
            <div className="field">
              <label>Update ID</label>
              <input
                value={mappingUpdateId}
                onChange={(event) => setMappingUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={mappingUpdateJson}
                onChange={(event) => setMappingUpdateJson(event.target.value)}
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "mappingsUpdate",
                  `/api/v1/mappings/${mappingUpdateId}`,
                  {
                    method: "PUT",
                    body: JSON.stringify(parseJson(mappingUpdateJson)),
                  }
                )
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={mappingDeleteId}
                onChange={(event) => setMappingDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request(
                  "mappingsDelete",
                  `/api/v1/mappings/${mappingDeleteId}`,
                  { method: "DELETE" }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>
        <div className="grid two">
          <div className="card">
            <h3>Add Field Mapping</h3>
            <div className="field">
              <label>Mapping ID</label>
              <input
                value={fieldMappingForm.mapping_id}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    mapping_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Target Field ID</label>
              <input
                value={fieldMappingForm.target_field_id}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    target_field_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Source Expression</label>
              <input
                value={fieldMappingForm.source_expression}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    source_expression: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Transform Chain (JSON)</label>
              <textarea
                value={fieldMappingForm.transform_chain}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    transform_chain: event.target.value,
                  }))
                }
                rows={4}
              />
            </div>
            <div className="field">
              <label>Pre Validations (JSON)</label>
              <textarea
                value={fieldMappingForm.pre_validations}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    pre_validations: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Post Validations (JSON)</label>
              <textarea
                value={fieldMappingForm.post_validations}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    post_validations: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "fieldMappingCreate",
                  `/api/v1/mappings/${fieldMappingForm.mapping_id}/field-mappings`,
                  {
                    method: "POST",
                    body: JSON.stringify({
                      mapping_id: fieldMappingForm.mapping_id,
                      target_field_id: fieldMappingForm.target_field_id,
                      source_expression:
                        fieldMappingForm.source_expression || null,
                      transform_chain: parseJson(
                        fieldMappingForm.transform_chain,
                        { steps: [] }
                      ),
                      pre_validations: parseJson(
                        fieldMappingForm.pre_validations,
                        { validations: [] }
                      ),
                      post_validations: parseJson(
                        fieldMappingForm.post_validations,
                        { validations: [] }
                      ),
                      is_active: fieldMappingForm.is_active,
                    }),
                  }
                )
              }
            >
              Add Field Mapping
            </button>
          </div>
          <div className="card">
            <h3>Manage Field Mappings</h3>
            <div className="field">
              <label>Mapping ID</label>
              <input
                value={fieldMappingForm.mapping_id}
                onChange={(event) =>
                  setFieldMappingForm((prev) => ({
                    ...prev,
                    mapping_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="actions">
              <button
                onClick={() =>
                  request(
                    "fieldMappingList",
                    `/api/v1/mappings/${fieldMappingForm.mapping_id}/field-mappings`
                  )
                }
              >
                List
              </button>
            </div>
            <div className="divider" />
            <div className="field">
              <label>Update Field Mapping ID</label>
              <input
                value={fieldMappingUpdateId}
                onChange={(event) =>
                  setFieldMappingUpdateId(event.target.value)
                }
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={fieldMappingUpdateJson}
                onChange={(event) =>
                  setFieldMappingUpdateJson(event.target.value)
                }
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "fieldMappingUpdate",
                  `/api/v1/mappings/${fieldMappingForm.mapping_id}/field-mappings/${fieldMappingUpdateId}`,
                  {
                    method: "PUT",
                    body: JSON.stringify(parseJson(fieldMappingUpdateJson)),
                  }
                )
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete Field Mapping ID</label>
              <input
                value={fieldMappingDeleteId}
                onChange={(event) =>
                  setFieldMappingDeleteId(event.target.value)
                }
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request(
                  "fieldMappingDelete",
                  `/api/v1/mappings/${fieldMappingForm.mapping_id}/field-mappings/${fieldMappingDeleteId}`,
                  { method: "DELETE" }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Mappings Response"
          data={
            responses.mappingsList ||
            responses.mappingsCreate ||
            responses.fieldMappingList ||
            responses.fieldMappingCreate ||
            responses.mappingsUpdate
          }
        />
      </Section>

      <Section title="Rule Sets" description="Configure reconciliation rules.">
        <div className="grid two">
          <div className="card">
            <h3>Create Rule Set</h3>
            <div className="field">
              <label>Rule Set ID</label>
              <input
                value={ruleSetForm.rule_set_id}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    rule_set_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={ruleSetForm.rule_set_name}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    rule_set_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Source Dataset ID</label>
              <input
                value={ruleSetForm.source_dataset_id}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    source_dataset_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Target Dataset ID</label>
              <input
                value={ruleSetForm.target_dataset_id}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    target_dataset_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Mapping ID</label>
              <input
                value={ruleSetForm.mapping_id}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    mapping_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Matching Strategy</label>
              <select
                value={ruleSetForm.matching_strategy}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    matching_strategy: event.target.value,
                  }))
                }
              >
                <option value="EXACT">EXACT</option>
                <option value="FUZZY">FUZZY</option>
              </select>
            </div>
            <div className="field">
              <label>Matching Keys (JSON)</label>
              <textarea
                value={ruleSetForm.matching_keys}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    matching_keys: event.target.value,
                  }))
                }
                rows={4}
              />
            </div>
            <div className="field">
              <label>Scope Config (JSON)</label>
              <textarea
                value={ruleSetForm.scope_config}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    scope_config: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Tolerance Config (JSON)</label>
              <textarea
                value={ruleSetForm.tolerance_config}
                onChange={(event) =>
                  setRuleSetForm((prev) => ({
                    ...prev,
                    tolerance_config: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request("ruleSetsCreate", "/api/v1/rule-sets", {
                  method: "POST",
                  body: JSON.stringify({
                    rule_set_id: ruleSetForm.rule_set_id,
                    rule_set_name: ruleSetForm.rule_set_name,
                    source_dataset_id: ruleSetForm.source_dataset_id,
                    target_dataset_id: ruleSetForm.target_dataset_id,
                    mapping_id: ruleSetForm.mapping_id,
                    matching_strategy: ruleSetForm.matching_strategy,
                    matching_keys: parseJson(ruleSetForm.matching_keys, {
                      keys: [],
                    }),
                    scope_config: parseJson(ruleSetForm.scope_config, {}),
                    tolerance_config: parseJson(
                      ruleSetForm.tolerance_config,
                      {}
                    ),
                  }),
                })
              }
            >
              Create
            </button>
          </div>
          <div className="card">
            <h3>Manage Rule Sets</h3>
            <div className="actions">
              <button
                onClick={() => request("ruleSetsList", "/api/v1/rule-sets")}
              >
                List
              </button>
            </div>
            <div className="field">
              <label>Update ID</label>
              <input
                value={ruleSetUpdateId}
                onChange={(event) => setRuleSetUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={ruleSetUpdateJson}
                onChange={(event) => setRuleSetUpdateJson(event.target.value)}
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "ruleSetsUpdate",
                  `/api/v1/rule-sets/${ruleSetUpdateId}`,
                  {
                    method: "PUT",
                    body: JSON.stringify(parseJson(ruleSetUpdateJson)),
                  }
                )
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={ruleSetDeleteId}
                onChange={(event) => setRuleSetDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request(
                  "ruleSetsDelete",
                  `/api/v1/rule-sets/${ruleSetDeleteId}`,
                  { method: "DELETE" }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>

        <div className="grid two">
          <div className="card">
            <h3>Add Comparison Rule</h3>
            <div className="field">
              <label>Rule Set ID</label>
              <input
                value={comparisonRuleForm.rule_set_id}
                onChange={(event) =>
                  setComparisonRuleForm((prev) => ({
                    ...prev,
                    rule_set_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Target Field ID</label>
              <input
                value={comparisonRuleForm.target_field_id}
                onChange={(event) =>
                  setComparisonRuleForm((prev) => ({
                    ...prev,
                    target_field_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Comparator Type</label>
              <select
                value={comparisonRuleForm.comparator_type}
                onChange={(event) =>
                  setComparisonRuleForm((prev) => ({
                    ...prev,
                    comparator_type: event.target.value,
                  }))
                }
              >
                <option value="EXACT">EXACT</option>
                <option value="NUMERIC_TOLERANCE">NUMERIC_TOLERANCE</option>
                <option value="DATE_WINDOW">DATE_WINDOW</option>
                <option value="CASE_INSENSITIVE">CASE_INSENSITIVE</option>
                <option value="REGEX">REGEX</option>
                <option value="NULL_EQUALS_EMPTY">NULL_EQUALS_EMPTY</option>
                <option value="CUSTOM">CUSTOM</option>
              </select>
            </div>
            <div className="field">
              <label>Comparator Params (JSON)</label>
              <textarea
                value={comparisonRuleForm.comparator_params}
                onChange={(event) =>
                  setComparisonRuleForm((prev) => ({
                    ...prev,
                    comparator_params: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field inline">
              <label>
                <input
                  type="checkbox"
                  checked={comparisonRuleForm.ignore_field}
                  onChange={(event) =>
                    setComparisonRuleForm((prev) => ({
                      ...prev,
                      ignore_field: event.target.checked,
                    }))
                  }
                />
                Ignore Field
              </label>
            </div>
            <button
              onClick={() =>
                request(
                  "comparisonRuleCreate",
                  `/api/v1/rule-sets/${comparisonRuleForm.rule_set_id}/comparison-rules`,
                  {
                    method: "POST",
                    body: JSON.stringify({
                      rule_set_id: comparisonRuleForm.rule_set_id,
                      target_field_id: comparisonRuleForm.target_field_id,
                      comparator_type: comparisonRuleForm.comparator_type,
                      comparator_params: parseJson(
                        comparisonRuleForm.comparator_params,
                        {}
                      ),
                      ignore_field: comparisonRuleForm.ignore_field,
                      is_active: true,
                    }),
                  }
                )
              }
            >
              Add Comparison Rule
            </button>
          </div>
          <div className="card">
            <h3>List Comparison Rules</h3>
            <div className="field">
              <label>Rule Set ID</label>
              <input
                value={comparisonRuleForm.rule_set_id}
                onChange={(event) =>
                  setComparisonRuleForm((prev) => ({
                    ...prev,
                    rule_set_id: event.target.value,
                  }))
                }
              />
            </div>
            <button
              onClick={() =>
                request(
                  "comparisonRuleList",
                  `/api/v1/rule-sets/${comparisonRuleForm.rule_set_id}/comparison-rules`
                )
              }
            >
              List
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Rule Set Response"
          data={
            responses.ruleSetsList ||
            responses.ruleSetsCreate ||
            responses.comparisonRuleList ||
            responses.comparisonRuleCreate
          }
        />
      </Section>

      <Section
        title="Reference Datasets"
        description="Manage reference lookup data."
      >
        <div className="grid two">
          <div className="card">
            <h3>Create Reference Dataset</h3>
            <div className="field">
              <label>Reference ID</label>
              <input
                value={referenceForm.reference_dataset_id}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    reference_dataset_id: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Name</label>
              <input
                value={referenceForm.reference_name}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    reference_name: event.target.value,
                  }))
                }
              />
            </div>
            <div className="field">
              <label>Source Type</label>
              <select
                value={referenceForm.source_type}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    source_type: event.target.value,
                  }))
                }
              >
                <option value="CSV">CSV</option>
                <option value="ORACLE">ORACLE</option>
                <option value="MONGODB">MONGODB</option>
                <option value="INLINE">INLINE</option>
              </select>
            </div>
            <div className="field">
              <label>Source Config (JSON)</label>
              <textarea
                value={referenceForm.source_config}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    source_config: event.target.value,
                  }))
                }
                rows={4}
              />
            </div>
            <div className="field">
              <label>Key Fields (JSON)</label>
              <textarea
                value={referenceForm.key_fields}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    key_fields: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Value Fields (JSON)</label>
              <textarea
                value={referenceForm.value_fields}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    value_fields: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <div className="field">
              <label>Cache Config (JSON)</label>
              <textarea
                value={referenceForm.cache_config}
                onChange={(event) =>
                  setReferenceForm((prev) => ({
                    ...prev,
                    cache_config: event.target.value,
                  }))
                }
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request("referencesCreate", "/api/v1/reference-datasets", {
                  method: "POST",
                  body: JSON.stringify({
                    reference_dataset_id: referenceForm.reference_dataset_id,
                    reference_name: referenceForm.reference_name,
                    source_type: referenceForm.source_type,
                    source_config: parseJson(referenceForm.source_config, {}),
                    key_fields: parseJson(referenceForm.key_fields, {}),
                    value_fields: parseJson(referenceForm.value_fields, {}),
                    cache_config: parseJson(referenceForm.cache_config, {}),
                  }),
                })
              }
            >
              Create
            </button>
          </div>
          <div className="card">
            <h3>Manage Reference Datasets</h3>
            <div className="actions">
              <button
                onClick={() =>
                  request("referencesList", "/api/v1/reference-datasets")
                }
              >
                List
              </button>
            </div>
            <div className="field">
              <label>Update ID</label>
              <input
                value={referenceUpdateId}
                onChange={(event) => setReferenceUpdateId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Update Payload (JSON)</label>
              <textarea
                value={referenceUpdateJson}
                onChange={(event) => setReferenceUpdateJson(event.target.value)}
                rows={4}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "referencesUpdate",
                  `/api/v1/reference-datasets/${referenceUpdateId}`,
                  {
                    method: "PUT",
                    body: JSON.stringify(parseJson(referenceUpdateJson)),
                  }
                )
              }
            >
              Update
            </button>
            <div className="divider" />
            <div className="field">
              <label>Delete ID</label>
              <input
                value={referenceDeleteId}
                onChange={(event) => setReferenceDeleteId(event.target.value)}
              />
            </div>
            <button
              className="danger"
              onClick={() =>
                request(
                  "referencesDelete",
                  `/api/v1/reference-datasets/${referenceDeleteId}`,
                  { method: "DELETE" }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>
        <ResponsePanel
          label="Reference Dataset Response"
          data={
            responses.referencesList ||
            responses.referencesCreate ||
            responses.referencesUpdate
          }
        />
      </Section>

      <Section title="Jobs" description="Execute reconciliation jobs.">
        <div className="grid two">
          <div className="card">
            <h3>Create Job</h3>
            <div className="field">
              <label>Rule Set ID</label>
              <input
                value={jobRuleSetId}
                onChange={(event) => setJobRuleSetId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Filters (JSON)</label>
              <textarea
                value={jobFilters}
                onChange={(event) => setJobFilters(event.target.value)}
                rows={3}
              />
            </div>
            <button
              onClick={() =>
                request("jobsCreate", "/api/v1/jobs", {
                  method: "POST",
                  body: JSON.stringify({
                    rule_set_id: jobRuleSetId,
                    filters: parseJson(jobFilters, {}),
                  }),
                })
              }
            >
              Create Job
            </button>
          </div>
          <div className="card">
            <h3>Manage Jobs</h3>
            <div className="field">
              <label>Job ID</label>
              <input
                value={jobIdLookup}
                onChange={(event) => setJobIdLookup(event.target.value)}
              />
            </div>
            <div className="actions">
              <button onClick={() => request("jobsList", "/api/v1/jobs")}>
                List
              </button>
              <button
                onClick={() =>
                  request("jobsGet", `/api/v1/jobs/${jobIdLookup}`)
                }
              >
                Get
              </button>
              <button
                className="danger"
                onClick={() =>
                  request("jobsCancel", `/api/v1/jobs/${jobIdLookup}`, {
                    method: "DELETE",
                  })
                }
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
        <ResponsePanel
          label="Jobs Response"
          data={responses.jobsList || responses.jobsGet || responses.jobsCreate}
        />
      </Section>

      <Section title="Results" description="Query reconciliation results.">
        <div className="grid two">
          <div className="card">
            <h3>Diff View (Side-by-Side Compare)</h3>
            <div className="field">
              <label>Job ID</label>
              <input
                value={resultsJobId}
                onChange={(event) => setResultsJobId(event.target.value)}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "resultsDiffView",
                  `/api/v1/results/${resultsJobId}/diff-view?limit=500&offset=0`
                )
              }
            >
              Load Diff View
            </button>
          </div>
          <div className="card">
            <h3>Summary</h3>
            <div className="field">
              <label>Job ID</label>
              <input
                value={resultsJobId}
                onChange={(event) => setResultsJobId(event.target.value)}
              />
            </div>
            <button
              onClick={() =>
                request(
                  "resultsSummary",
                  `/api/v1/results/${resultsJobId}/summary`
                )
              }
            >
              Fetch Summary
            </button>
          </div>
          <div className="card">
            <h3>Discrepancies</h3>
            <div className="field">
              <label>Job ID</label>
              <input
                value={resultsJobId}
                onChange={(event) => setResultsJobId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Field ID (optional)</label>
              <input
                value={resultsFieldId}
                onChange={(event) => setResultsFieldId(event.target.value)}
              />
            </div>
            <div className="field">
              <label>Severity (optional)</label>
              <input
                value={resultsSeverity}
                onChange={(event) => setResultsSeverity(event.target.value)}
              />
            </div>
            <div className="field inline">
              <label>
                Limit
                <input
                  type="number"
                  value={resultsLimit}
                  onChange={(event) =>
                    setResultsLimit(Number(event.target.value))
                  }
                />
              </label>
              <label>
                Offset
                <input
                  type="number"
                  value={resultsOffset}
                  onChange={(event) =>
                    setResultsOffset(Number(event.target.value))
                  }
                />
              </label>
            </div>
            <button
              onClick={() =>
                request(
                  "resultsDiscrepancies",
                  `/api/v1/results/${resultsJobId}/discrepancies?field_id=${resultsFieldId}&severity=${resultsSeverity}&limit=${resultsLimit}&offset=${resultsOffset}`
                )
              }
            >
              Fetch Discrepancies
            </button>
          </div>
        </div>
        <div className="grid two">
          <div className="card">
            <h3>Unmatched Source</h3>
            <button
              onClick={() =>
                request(
                  "resultsUnmatchedSource",
                  `/api/v1/results/${resultsJobId}/unmatched-source`
                )
              }
            >
              Fetch Unmatched Source
            </button>
          </div>
          <div className="card">
            <h3>Unmatched Target</h3>
            <button
              onClick={() =>
                request(
                  "resultsUnmatchedTarget",
                  `/api/v1/results/${resultsJobId}/unmatched-target`
                )
              }
            >
              Fetch Unmatched Target
            </button>
          </div>
        </div>
        {responses.resultsDiffView && (
          <div className="diff-view-section">
            <h3>Side-by-Side Diff</h3>
            <DiffView data={responses.resultsDiffView} />
          </div>
        )}
        <ResponsePanel
          label="Results Response (raw)"
          data={
            responses.resultsSummary ||
            responses.resultsDiscrepancies ||
            responses.resultsUnmatchedSource ||
            responses.resultsUnmatchedTarget ||
            (responses.resultsDiffView ? "Diff view loaded (see above)" : null)
          }
        />
      </Section>
    </div>
  );
}

export default App;
