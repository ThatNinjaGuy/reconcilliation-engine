import { createContext, useCallback, useContext, useMemo, useState } from "react";

const ToastsContext = createContext(null);

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export function ToastsProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback((toast) => {
    const id = uid();
    const item = {
      id,
      type: toast.type || "info",
      title: toast.title || "Info",
      message: toast.message || "",
      createdAt: Date.now(),
      timeoutMs: toast.timeoutMs ?? 4000,
    };
    setToasts((prev) => [item, ...prev].slice(0, 5));
    window.setTimeout(() => removeToast(id), item.timeoutMs);
  }, [removeToast]);

  const value = useMemo(() => ({ toasts, pushToast, removeToast }), [toasts, pushToast, removeToast]);

  return <ToastsContext.Provider value={value}>{children}</ToastsContext.Provider>;
}

export function useToasts() {
  const ctx = useContext(ToastsContext);
  if (!ctx) throw new Error("useToasts must be used within ToastsProvider");
  return ctx;
}

