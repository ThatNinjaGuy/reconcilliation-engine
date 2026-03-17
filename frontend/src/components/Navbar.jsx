import { NavLink } from "react-router-dom";

export default function Navbar() {
  return (
    <div className="navbar">
      <div className="navbar-brand">GenRecon</div>
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
      </nav>
    </div>
  );
}
