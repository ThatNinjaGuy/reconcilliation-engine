import { useId, useState } from "react";

export default function Collapsible({ title, subtitle, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div className="collapsible">
      <button
        type="button"
        className="collapsible-head"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((o) => !o)}
      >
        <div className="collapsible-title">
          <div className="collapsible-title-text">{title}</div>
          {subtitle ? <div className="collapsible-subtitle">{subtitle}</div> : null}
        </div>
        <div className="collapsible-icon">{open ? "▾" : "▸"}</div>
      </button>
      {open ? (
        <div id={contentId} className="collapsible-body">
          {children}
        </div>
      ) : null}
    </div>
  );
}

