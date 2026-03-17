import { useEffect, useMemo, useState } from "react";
import { DiffView } from "./DiffView.jsx";

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

function getQuery() {
  const params = new URLSearchParams(window.location.search || "");
  return Object.fromEntries(params.entries());
}

export default function ResultsPage() {
  const [baseUrl, setBaseUrl] = useState(
    () => localStorage.getItem("genrecon.baseUrl") || "http://localhost:8000"
  );
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("genrecon.apiKey") || ""
  );

  const [status, setStatus] = useState(null);
  const [responses, setResponses] = useState({});

  const [jobId, setJobId] = useState(() => getQuery().job_id || "");

  useEffect(() => {
    const onNav = () => {
      const q = getQuery();
      if (q.job_id !== undefined) setJobId(q.job_id);
    };
    window.addEventListener("popstate", onNav);
    return () => window.removeEventListener("popstate", onNav);
  }, []);

  const headers = useMemo(() => {
    const base = {};
    if (apiKey) base.Authorization = `Bearer ${apiKey}`;
    return base;
  }, [apiKey]);

  const saveConnection = () => {
    localStorage.setItem("genrecon.baseUrl", baseUrl);
    localStorage.setItem("genrecon.apiKey", apiKey);
    setStatus({ type: "success", message: "Connection settings saved." });
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

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>GenRecon Results</h1>
          <p className="muted">A focused, Git-style diff view for one job.</p>
        </div>
        <div className={`status ${status?.type || ""}`}>
          {status?.message || "Ready."}
        </div>
      </header>

      <Section title="Connection" description="Uses the same settings as Console.">
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
          <button
            onClick={() => {
              window.history.pushState({}, "", "/");
              window.dispatchEvent(new PopStateEvent("popstate"));
            }}
          >
            Back to Console
          </button>
        </div>
      </Section>

      <Section title="Job Results" description="Load unified Git diff view in one click.">
        <div className="grid two">
          <div className="card">
            <h3>Unified Git Diff View</h3>
            <div className="field">
              <label>Job ID</label>
              <input
                value={jobId}
                onChange={(event) => setJobId(event.target.value)}
              />
            </div>
            <div className="actions">
              <button
                onClick={() =>
                  request(
                    "diffView",
                    `/api/v1/results/${jobId}/diff-view?limit=2000&offset=0`
                  )
                }
              >
                Load Git Diff View
              </button>
              <button
                onClick={() =>
                  request("summary", `/api/v1/results/${jobId}/summary`)
                }
              >
                Summary
              </button>
            </div>
            <p className="muted">
              Tip: you can open directly via{" "}
              <span style={{ fontFamily: "ui-monospace, monospace" }}>
                /results?job_id=JOB_xxx
              </span>
              .
            </p>
          </div>

          <div className="card">
            <h3>Separate Buttons (kept)</h3>
            <div className="actions">
              <button
                onClick={() =>
                  request("discrepancies", `/api/v1/results/${jobId}/discrepancies?limit=2000&offset=0`)
                }
              >
                Discrepancies
              </button>
              <button
                onClick={() =>
                  request("unmatchedSource", `/api/v1/results/${jobId}/unmatched-source?limit=2000&offset=0`)
                }
              >
                Unmatched Source
              </button>
              <button
                onClick={() =>
                  request("unmatchedTarget", `/api/v1/results/${jobId}/unmatched-target?limit=2000&offset=0`)
                }
              >
                Unmatched Target
              </button>
            </div>
          </div>
        </div>

        <div className="diff-view-section">
          <h3>Git-style Diff</h3>
          <DiffView data={responses.diffView} />
        </div>

        <ResponsePanel
          label="Raw response"
          data={
            responses.summary ||
            responses.diffView ||
            responses.discrepancies ||
            responses.unmatchedSource ||
            responses.unmatchedTarget
          }
        />
      </Section>
    </div>
  );
}

