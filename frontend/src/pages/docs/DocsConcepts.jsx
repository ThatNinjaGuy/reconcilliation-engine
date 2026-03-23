export default function DocsConcepts() {
  return (
    <div className="page">
      <div className="card">
        <h3>Mental Model (Beginner First)</h3>
        <p className="muted">
          Think of Syncora as a pipeline:
          <span className="mono"> read source -&gt; normalize -&gt; compare with target -&gt; report differences</span>.
        </p>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>Entity</th><th>What It Is</th><th>Why It Exists</th></tr>
            </thead>
            <tbody>
              <tr><td>System</td><td>Connection details to a technology</td><td>So Syncora knows how to connect (file path, DB host, etc.)</td></tr>
              <tr><td>Schema</td><td>Canonical shape of records</td><td>So data from different sources is interpreted consistently</td></tr>
              <tr><td>Dataset</td><td>Concrete data object + schema + system</td><td>So Syncora knows exactly which file/table/collection to read</td></tr>
              <tr><td>Mapping</td><td>How source fields become target fields</td><td>So unlike systems can still be compared fairly</td></tr>
              <tr><td>Rule Set</td><td>Matching + comparison settings</td><td>So Syncora knows which records correspond and how strict comparison is</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Glossary (Plain English)</h3>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Term</th><th>Plain Meaning</th></tr></thead>
            <tbody>
              <tr><td>Canonical</td><td>Standard internal shape used by Syncora for fair comparison.</td></tr>
              <tr><td>Physical</td><td>Actual source-side name/path (CSV column, DB column, JSON path).</td></tr>
              <tr><td>Transformation</td><td>Changing source value format/content before comparison.</td></tr>
              <tr><td>Lookup</td><td>Find a value from a side/reference table using a key.</td></tr>
              <tr><td>Matching key</td><td>Fields used to decide which source record matches which target record.</td></tr>
              <tr><td>Composite key</td><td>Matching key made from 2+ fields together.</td></tr>
              <tr><td>Comparator</td><td>Rule that decides whether two field values are equal.</td></tr>
              <tr><td>Discrepancy</td><td>A mismatch detected for a field or record.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3>Why Dataset Is Needed If Schema Already Exists</h3>
        <p className="muted">
          A schema only defines structure. It does not point to real data.
          A dataset binds structure to a real source object:
        </p>
        <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>Schema says: "There is a field called `invoice_id`."</li>
          <li>Dataset says: "Read it from file `invoice_source.csv` using `system_id=file_local`."</li>
        </ul>
        <p className="muted">
          You can reuse the same schema for many datasets (daily files, monthly partitions, multiple regions).
        </p>
      </div>

      <div className="card">
        <h3>Relationship Example (End-to-End)</h3>
        <pre className="codeblock">{`Business problem:
Compare invoice records from source CSV and target Oracle table.

System:
- FILE system points to /data/recon
- ORACLE system points to db host/user/pass

Schema:
- Canonical fields: company_id, invoice_id, amount, status

Dataset:
- Source dataset: physical_name=invoice_source.csv (FILE)
- Target dataset: physical_name=FINANCE.INVOICE_TABLE (ORACLE)

Mapping:
- source cust_status -> canonical status
- source amount_text -> canonical amount (to_decimal transform)

Rule Set:
- matching keys: [company_id, invoice_id]
- comparison rule on amount: NUMERIC_TOLERANCE 0.01

Result:
- Records pair by composite key, then field-level differences are reported.`}</pre>
      </div>

      <div className="card">
        <h3>Why Field ID, Field Name, and Physical Mapping Are Separate</h3>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Part</th><th>Purpose</th><th>Typical Example</th></tr></thead>
            <tbody>
              <tr>
                <td className="mono">field_id</td>
                <td>Stable machine key used in mappings/rules/comparators.</td>
                <td className="mono">invoice_id</td>
              </tr>
              <tr>
                <td className="mono">field_name</td>
                <td>Human-friendly label for UI/readability.</td>
                <td>Invoice ID</td>
              </tr>
              <tr>
                <td className="mono">physical_mapping</td>
                <td>Where the raw value comes from in source object.</td>
                <td className="mono">{`{"csv_column":"INV_ID"}`}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="muted">
          Keep them the same for simple projects. Split them when source names are messy or inconsistent.
        </p>
      </div>

      <div className="card">
        <h3>When They Should Be Same vs Different</h3>
        <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li><strong>Same</strong>: clean source columns (`invoice_id`, `amount`) and no naming cleanup needed.</li>
          <li><strong>Different</strong>: source has `INV_ID`, target has `InvoiceNo`, but canonical field stays `invoice_id`.</li>
          <li><strong>Different</strong>: multilingual or legacy names where you want one standard internal vocabulary.</li>
        </ul>
      </div>

      <div className="card">
        <h3>How Reference Dataset Connects to Main Dataset</h3>
        <p className="muted">
          Reference datasets are not compared directly. They are used during transformation as lookups.
          In backend, this is done by transform type <span className="mono">lookup</span> via reference manager cache.
        </p>
        <pre className="codeblock">{`Example:
source row.customer_country_code = "IN"
reference dataset has rows: code -> country_name
lookup transform sets target field country_name = "India"`}</pre>
      </div>

      <div className="card">
        <h3>Transformation Lifecycle (What Happens Internally)</h3>
        <ol className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>Source row is read using source dataset + source schema physical mappings.</li>
          <li>For each field mapping, Syncora evaluates `source_expression` or executes `transform_chain` steps.</li>
          <li>Optional pre-validations run before transform; post-validations run after transform.</li>
          <li>Output becomes transformed source canonical row.</li>
          <li>Matcher pairs transformed source rows with target rows using rule set matching keys.</li>
          <li>Comparator checks each target field, using comparison rules when defined.</li>
        </ol>
      </div>
    </div>
  );
}
