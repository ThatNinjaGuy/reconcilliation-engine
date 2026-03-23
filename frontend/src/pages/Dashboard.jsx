import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";

function statusClass(status) {
  const s = (status || "").toUpperCase();
  if (s === "COMPLETED") return "badge badge-success";
  if (s === "FAILED") return "badge badge-danger";
  if (s === "RUNNING") return "badge badge-info";
  return "badge";
}

export default function Dashboard() {
  const { request, loading } = useApi();
  const [jobs, setJobs] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadJobs = async () => {
    const data = await request(
      "/api/v1/jobs?limit=50&offset=0",
      {},
      // Don't spam success toasts during auto-refresh.
      { toast: false }
    );
    const sorted = [...(data || [])].sort((a, b) => {
      const ad = a?.created_at ? Date.parse(a.created_at) : 0;
      const bd = b?.created_at ? Date.parse(b.created_at) : 0;
      return bd - ad;
    });
    setJobs(sorted);
  };

  useEffect(() => {
    loadJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(loadJobs, 10000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh]);

  const summary = useMemo(() => {
    const list = jobs || [];
    const total = list.length;
    const by = (st) => list.filter((j) => (j.status || "").toUpperCase() === st).length;
    return {
      total,
      completed: by("COMPLETED"),
      failed: by("FAILED"),
      running: by("RUNNING"),
    };
  }, [jobs]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Jobs and quick access to results.</p>
        </div>
        <div className="actions">
          <Link className="button" to="/configs/new">
            New Reconciliation
          </Link>
          <button type="button" onClick={loadJobs} disabled={loading}>
            Refresh
          </button>
          <label className="toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh
          </label>
        </div>
      </div>

      <div className="grid three">
        <div className="card">
          <div className="card-kpi">
            <div className="kpi">{summary.total}</div>
            <div className="kpi-label">Total jobs</div>
          </div>
        </div>
        <div className="card">
          <div className="card-kpi">
            <div className="kpi">{summary.running}</div>
            <div className="kpi-label">Running</div>
          </div>
        </div>
        <div className="card">
          <div className="card-kpi">
            <div className="kpi">{summary.failed}</div>
            <div className="kpi-label">Failed</div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Recent Jobs</h2>
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Job ID</th>
                <th>Rule Set</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {(jobs || []).map((j) => (
                <tr key={j.job_id}>
                  <td className="mono">{j.job_id}</td>
                  <td className="mono">{j.rule_set_id}</td>
                  <td>
                    <span className={statusClass(j.status)}>{j.status}</span>
                  </td>
                  <td>{j.progress_percent ?? "—"}%</td>
                  <td className="mono small">{j.created_at}</td>
                  <td>
                    <div className="actions">
                      <Link className="button button-secondary" to={`/results/${j.job_id}`}>
                        View Results
                      </Link>
                      <button
                        type="button"
                        onClick={() =>
                          request(
                            "/api/v1/jobs",
                            {
                              method: "POST",
                              body: JSON.stringify({ rule_set_id: j.rule_set_id, filters: {} }),
                            },
                            { successMessage: `Job started for ${j.rule_set_id}` }
                          ).then(loadJobs)
                        }
                      >
                        Re-run
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {jobs && jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="muted">
                    No jobs yet. Create a config and run a reconciliation.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

