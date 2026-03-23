import "./App.css";

import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar.jsx";
import ToastContainer from "./components/ToastContainer.jsx";
import { ConnectionProvider } from "./state/connection.jsx";
import { ToastsProvider } from "./state/toasts.jsx";

import Dashboard from "./pages/Dashboard.jsx";
import Configs from "./pages/Configs.jsx";
import ConfigWizard from "./pages/ConfigWizard.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import Settings from "./pages/Settings.jsx";
import DocsLayout from "./pages/docs/DocsLayout.jsx";
import DocsHome from "./pages/docs/DocsHome.jsx";
import DocsConcepts from "./pages/docs/DocsConcepts.jsx";
import DocsSystems from "./pages/docs/DocsSystems.jsx";
import {
  DocsComparisonRules,
  DocsDatasets,
  DocsMappings,
  DocsReferenceDatasets,
  DocsRuleSets,
  DocsSchemas,
} from "./pages/docs/DocsConfigs.jsx";
import {
  DocsConnectorApi,
  DocsConnectorFile,
  DocsConnectorMongodb,
  DocsConnectorOracle,
} from "./pages/docs/DocsConnectors.jsx";

function Layout() {
  return (
    <div className="app-shell">
      <Navbar />
      <ToastContainer />
      <div className="app-content">
        <Outlet />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ConnectionProvider>
      <ToastsProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/configs" element={<Configs />} />
            <Route path="/configs/new" element={<ConfigWizard />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/docs" element={<DocsLayout />}>
              <Route index element={<DocsHome />} />
              <Route path="concepts" element={<DocsConcepts />} />
              <Route path="systems" element={<DocsSystems />} />
              <Route path="connectors/file" element={<DocsConnectorFile />} />
              <Route path="connectors/oracle" element={<DocsConnectorOracle />} />
              <Route path="connectors/mongodb" element={<DocsConnectorMongodb />} />
              <Route path="connectors/api" element={<DocsConnectorApi />} />
              <Route path="schemas" element={<DocsSchemas />} />
              <Route path="datasets" element={<DocsDatasets />} />
              <Route path="mappings" element={<DocsMappings />} />
              <Route path="rule-sets" element={<DocsRuleSets />} />
              <Route path="comparison-rules" element={<DocsComparisonRules />} />
              <Route path="reference-datasets" element={<DocsReferenceDatasets />} />
            </Route>
            <Route path="/results/:jobId" element={<ResultsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ToastsProvider>
    </ConnectionProvider>
  );
}
