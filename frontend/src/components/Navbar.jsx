import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <div className="navbar">
      <div className="navbar-brand">Syncora</div>
      <nav className="navbar-links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Dashboard
        </NavLink>
        <NavLink to="/configs" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Configs
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Settings
        </NavLink>
        <NavLink to="/docs" className={({ isActive }) => (isActive ? "navlink active" : "navlink")}>
          Docs
        </NavLink>
      </nav>
    </div>
  );
}
