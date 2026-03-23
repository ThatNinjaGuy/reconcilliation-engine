import { useToasts } from "../state/toasts.jsx";

export default function ToastContainer() {
  const { toasts, removeToast } = useToasts();

  return (
    <div className="toast-container" aria-live="polite" aria-relevant="additions">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.type}`}>
          <div className="toast-head">
            <div className="toast-title">{t.title}</div>
            <button className="toast-close" onClick={() => removeToast(t.id)}>
              ✕
            </button>
          </div>
          {t.message ? <div className="toast-message">{t.message}</div> : null}
        </div>
      ))}
    </div>
  );
}

