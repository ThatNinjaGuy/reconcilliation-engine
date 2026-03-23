import { NavLink, Outlet } from "react-router-dom";

const LINKS = [
  { to: "/docs", end: true, label: "Overview" },
  { to: "/docs/concepts", label: "Core Concepts" },
  { to: "/docs/systems", label: "Systems" },
  { to: "/docs/connectors/file", label: "Connector: FILE" },
  { to: "/docs/connectors/oracle", label: "Connector: ORACLE" },
  { to: "/docs/connectors/mongodb", label: "Connector: MONGODB" },
  { to: "/docs/connectors/api", label: "Connector: API" },
  { to: "/docs/schemas", label: "Schemas" },
  { to: "/docs/datasets", label: "Datasets" },
  { to: "/docs/mappings", label: "Mappings" },
  { to: "/docs/rule-sets", label: "Rule Sets" },
  { to: "/docs/comparison-rules", label: "Comparison Rules" },
  { to: "/docs/reference-datasets", label: "Reference Datasets" },
];

export default function DocsLayout() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Syncora Documentation</h1>
          <p className="muted">Self-service configuration guide with field-level references and examples.</p>
        </div>
      </div>
      <div className="docs-layout">
        <aside className="docs-sidebar card">
          <h3 style={{ margin: 0 }}>Sections</h3>
          <nav className="docs-nav">
            {LINKS.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                end={l.end}
                className={({ isActive }) => (isActive ? "docs-link active" : "docs-link")}
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="docs-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
