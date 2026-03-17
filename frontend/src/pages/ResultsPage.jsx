import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useApi } from "../hooks/useApi.js";
import DiffView from "../components/DiffView.jsx";

function Tabs({ active, setActive }) {
  const tabs = [
    { key: "diff", label: "Diff View" },
    { key: "summary", label: "Summary" },
    { key: "discrepancies", label: "Discrepancies" },
    { key: "unmatched_source", label: "Unmatched Source" },
    { key: "unmatched_target", label: "Unmatched Target" },
  ];
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <button
          key={t.key}
          type="button"
          className={active === t.key ? "tab active" : "tab"}
          onClick={() => setActive(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

function SummaryCards({ summary }) {
  if (!summary) return <p className="muted">No summary data.</p>;
  const items = [
    { label: "Total Source Records", value: summary.total_source_records },
    { label: "Total Target Records", value: summary.total_target_records },
    { label: "Matched Records", value: summary.matched_records },
    { label: "Matched (No Discrepancy)", value: summary.matched_with_no_discrepancy },
    { label: "Matched (With Discrepancy)", value: summary.matched_with_discrepancy },
    { label: "Unmatched Source", value: summary.unmatched_source_records },
    { label: "Unmatched Target", value: summary.unmatched_target_records },
    { label: "Total Field Discrepancies", value: summary.total_field_discrepancies },
    { label: "Match Rate", value: `${Number(summary.match_rate_percent || 0).toFixed(2)}%` },
    { label: "Accuracy Rate", value: `${Number(summary.accuracy_rate_percent || 0).toFixed(2)}%` },
  ];

  const fieldCounts = summary.field_discrepancy_counts || {};
  const hasFieldCounts = Object.keys(fieldCounts).length > 0;

  return (
    <div>
      <div className="grid three" style={{ marginBottom: 16 }}>
        {items.map((it) => (
          <div key={it.label} className="card card-kpi">
            <div className="kpi">{it.value ?? "—"}</div>
            <div className="kpi-label">{it.label}</div>
          </div>
        ))}
      </div>
      {hasFieldCounts && (
        <div className="card">
          <h3>Discrepancies by Field</h3>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Field</th><th>Count</th></tr>
              </thead>
              <tbody>
                {Object.entries(fieldCounts).sort((a, b) => b[1] - a[1]).map(([field, count]) => (
                  <tr key={field}>
                    <td className="mono">{field}</td>
                    <td>{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function DiscrepancyTable({ data }) {
  if (!data || data.length === 0) return <p className="muted">No discrepancies.</p>;

  return (
    <div className="card">
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Record Key</th>
              <th>Field</th>
              <th>Source Value</th>
              <th>Target Value</th>
              <th>Difference</th>
              <th>Comparator</th>
              <th>Severity</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d, i) => (
              <tr key={i}>
                <td className="mono">{d.record_key}</td>
                <td className="mono">{d.field_id}</td>
                <td>{d.source_value ?? "—"}</td>
                <td>{d.target_value ?? "—"}</td>
                <td>{d.difference ?? "—"}</td>
                <td><span className="badge">{d.comparator_type}</span></td>
                <td>
                  <span className={
                    d.severity === "HIGH" ? "badge badge-danger" :
                    d.severity === "MEDIUM" ? "badge badge-info" :
                    "badge"
                  }>{d.severity || "—"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UnmatchedTable({ data, side }) {
  if (!data || data.length === 0) return <p className="muted">No unmatched {side} records.</p>;

  const allFields = new Set();
  data.forEach((rec) => {
    const fields = rec.fields || rec;
    if (typeof fields === "object" && fields !== null) {
      Object.keys(fields).forEach((k) => { if (k !== "metadata" && k !== "transformation_errors" && k !== "source_metadata") allFields.add(k); });
    }
  });
  const columns = [...allFields].sort();

  if (columns.length === 0) {
    return (
      <div className="card">
        <p className="muted">Records found but no displayable fields.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              {columns.map((c) => <th key={c}>{c}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.map((rec, i) => {
              const fields = rec.fields || rec;
              return (
                <tr key={i}>
                  {columns.map((c) => (
                    <td key={c} className="mono">{fields[c] !== undefined ? String(fields[c]) : "—"}</td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const { jobId } = useParams();
  const { request, loading } = useApi();
  const [activeTab, setActiveTab] = useState("diff");
  const [summary, setSummary] = useState(null);
  const [diffView, setDiffView] = useState(null);
  const [discrepancies, setDiscrepancies] = useState(null);
  const [unmatchedSource, setUnmatchedSource] = useState(null);
  const [unmatchedTarget, setUnmatchedTarget] = useState(null);

  useEffect(() => {
    const load = async () => {
      const [s, d] = await Promise.all([
        request(`/api/v1/results/${jobId}/summary`, {}, { toast: false }),
        request(`/api/v1/results/${jobId}/diff-view?limit=2000&offset=0`, {}, { toast: false }),
      ]);
      setSummary(s);
      setDiffView(d);
    };
    load().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const kpis = useMemo(() => {
    if (!summary) return null;
    return {
      matched: summary.matched_records,
      mismatched: summary.matched_with_discrepancy,
      unmatchedSource: summary.unmatched_source_records,
      unmatchedTarget: summary.unmatched_target_records,
      accuracy: summary.accuracy_rate_percent,
    };
  }, [summary]);

  const loadTab = async (tab) => {
    if (tab === "discrepancies" && !discrepancies) {
      setDiscrepancies(
        await request(`/api/v1/results/${jobId}/discrepancies?limit=2000&offset=0`, {}, { toast: false })
      );
    }
    if (tab === "unmatched_source" && !unmatchedSource) {
      setUnmatchedSource(
        await request(`/api/v1/results/${jobId}/unmatched-source?limit=2000&offset=0`, {}, { toast: false })
      );
    }
    if (tab === "unmatched_target" && !unmatchedTarget) {
      setUnmatchedTarget(
        await request(`/api/v1/results/${jobId}/unmatched-target?limit=2000&offset=0`, {}, { toast: false })
      );
    }
  };

  useEffect(() => {
    loadTab(activeTab).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Results</h1>
          <p className="muted">Job <span className="mono">{jobId}</span></p>
        </div>
        <div className="actions">
          <Link className="button button-secondary" to="/">Back to Dashboard</Link>
          <button
            type="button"
            onClick={() => request(`/api/v1/results/${jobId}/diff-view?limit=2000&offset=0`).then(setDiffView)}
            disabled={loading}
          >
            Refresh Diff
          </button>
        </div>
      </div>

      {kpis && (
        <div className="grid five">
          <div className="card card-kpi">
            <div className="kpi">{kpis.matched}</div>
            <div className="kpi-label">Matched</div>
          </div>
          <div className="card card-kpi">
            <div className="kpi">{kpis.mismatched}</div>
            <div className="kpi-label">Mismatched</div>
          </div>
          <div className="card card-kpi">
            <div className="kpi">{kpis.unmatchedSource}</div>
            <div className="kpi-label">Only Source</div>
          </div>
          <div className="card card-kpi">
            <div className="kpi">{kpis.unmatchedTarget}</div>
            <div className="kpi-label">Only Target</div>
          </div>
          <div className="card card-kpi">
            <div className="kpi">{Number(kpis.accuracy || 0).toFixed(2)}%</div>
            <div className="kpi-label">Accuracy</div>
          </div>
        </div>
      )}

      <Tabs active={activeTab} setActive={setActiveTab} />

      {activeTab === "diff" && <DiffView data={diffView} />}
      {activeTab === "summary" && <SummaryCards summary={summary} />}
      {activeTab === "discrepancies" && <DiscrepancyTable data={discrepancies} />}
      {activeTab === "unmatched_source" && <UnmatchedTable data={unmatchedSource} side="source" />}
      {activeTab === "unmatched_target" && <UnmatchedTable data={unmatchedTarget} side="target" />}
    </div>
  );
}
