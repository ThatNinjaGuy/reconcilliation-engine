export default function HelpText({ children }) {
  if (!children) return null;
  return <span className="help-text">{children}</span>;
}
