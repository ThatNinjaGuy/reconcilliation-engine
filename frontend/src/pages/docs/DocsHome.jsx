export default function DocsHome() {
  return (
    <div className="page">
      <div className="card">
        <h3>Start Here (No Prior Knowledge Needed)</h3>
        <p className="muted">
          If this is your first time, read in this order:
          <span className="mono"> Core Concepts -&gt; Systems -&gt; Connector page -&gt; Schemas -&gt; Datasets -&gt; Mappings -&gt; Rule Sets -&gt; Comparison Rules</span>.
        </p>
      </div>

      <div className="card">
        <h3>One-Minute Explanation</h3>
        <p className="muted">
          Syncora compares data between two sides: source and target. Because each side may be stored differently
          (CSV, Oracle, Mongo), you first define a common language (schema), then map source to that language,
          and finally configure how records are matched and compared.
        </p>
      </div>

      <div className="card">
        <h3>Configuration Dependency Order</h3>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Create First</th>
                <th>Depends On</th>
                <th>Used By</th>
                <th>Why</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>System</td><td>None</td><td>Dataset</td><td>Connection definition.</td></tr>
              <tr><td>Schema</td><td>None</td><td>Dataset, Mapping</td><td>Canonical shape definition.</td></tr>
              <tr><td>Dataset</td><td>System + Schema</td><td>Rule Set</td><td>Points to real data object.</td></tr>
              <tr><td>Mapping</td><td>Schema</td><td>Rule Set</td><td>Transforms source into comparable shape.</td></tr>
              <tr><td>Rule Set</td><td>Source Dataset + Target Dataset + Mapping</td><td>Job</td><td>Match + compare logic.</td></tr>
              <tr><td>Comparison Rule</td><td>Rule Set</td><td>Rule Set execution</td><td>Per-field comparator override.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
