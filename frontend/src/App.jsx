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
            <Route path="/results/:jobId" element={<ResultsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </ToastsProvider>
    </ConnectionProvider>
  );
}
