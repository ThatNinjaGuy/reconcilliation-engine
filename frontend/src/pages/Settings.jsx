import { useState } from "react";
import { useConnection } from "../state/connection.jsx";
import { useApi } from "../hooks/useApi.js";

export default function Settings() {
  const { baseUrl, setBaseUrl, apiKey, setApiKey } = useConnection();
  const { request, loading } = useApi();
  const [showKey, setShowKey] = useState(false);

  const testConnection = async () => {
    try {
      await request("/api/v1/systems?limit=1", {}, { successMessage: "Connection successful" });
    } catch {
      /* error toast is shown by useApi */
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">Configure your connection to the Syncora backend.</p>
        </div>
      </div>

      <div className="card" style={{ maxWidth: 600 }}>
        <h3>Connection</h3>

        <label className="field">
          <span>Base URL</span>
          <span className="help-text">The URL where the Syncora API server is running.</span>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="http://localhost:8000"
          />
        </label>

        <label className="field">
          <span>API Key</span>
          <span className="help-text">
            Optional. Set if the backend requires token-based authentication.
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <input
              style={{ flex: 1 }}
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Optional"
            />
            <button
              type="button"
              className="button button-secondary"
              style={{ whiteSpace: "nowrap" }}
              onClick={() => setShowKey((s) => !s)}
            >
              {showKey ? "Hide" : "Show"}
            </button>
          </div>
        </label>

        <div className="actions">
          <button type="button" onClick={testConnection} disabled={loading}>
            {loading ? "Testing..." : "Test Connection"}
          </button>
        </div>
      </div>
    </div>
  );
}
