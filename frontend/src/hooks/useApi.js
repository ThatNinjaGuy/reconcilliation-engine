import { useCallback, useMemo, useState } from "react";
import { useConnection } from "../state/connection.jsx";
import { useToasts } from "../state/toasts.jsx";

export function useApi() {
  const { baseUrl, apiKey } = useConnection();
  const { pushToast } = useToasts();
  const [loading, setLoading] = useState(false);

  const headers = useMemo(() => {
    const h = {};
    if (apiKey) h.Authorization = `Bearer ${apiKey}`;
    return h;
  }, [apiKey]);

  const request = useCallback(
    async (path, options = {}, { toast = true, successMessage } = {}) => {
      setLoading(true);
      try {
        const response = await fetch(`${baseUrl}${path}`, {
          ...options,
          headers: {
            ...headers,
            ...options.headers,
            ...(options.body ? { "Content-Type": "application/json" } : {}),
          },
        });

        const isJson = response.headers
          .get("content-type")
          ?.includes("application/json");
        const payload = isJson ? await response.json() : await response.text();

        if (!response.ok) {
          const msg =
            payload?.detail || payload?.error?.message || "Request failed";
          if (toast) pushToast({ type: "error", title: "Request failed", message: msg });
          throw new Error(msg);
        }

        if (toast) {
          pushToast({
            type: "success",
            title: "Success",
            message: successMessage || `${options.method || "GET"} ${path}`,
          });
        }
        return payload;
      } finally {
        setLoading(false);
      }
    },
    [baseUrl, headers, pushToast]
  );

  return { request, loading };
}

