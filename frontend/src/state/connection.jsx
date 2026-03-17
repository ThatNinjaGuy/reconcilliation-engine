import { createContext, useContext, useEffect, useMemo, useState } from "react";

const ConnectionContext = createContext(null);

export function ConnectionProvider({ children }) {
  const [baseUrl, setBaseUrl] = useState(
    () => localStorage.getItem("genrecon.baseUrl") || "http://localhost:8000"
  );
  const [apiKey, setApiKey] = useState(
    () => localStorage.getItem("genrecon.apiKey") || ""
  );

  useEffect(() => {
    localStorage.setItem("genrecon.baseUrl", baseUrl);
  }, [baseUrl]);

  useEffect(() => {
    localStorage.setItem("genrecon.apiKey", apiKey);
  }, [apiKey]);

  const value = useMemo(
    () => ({ baseUrl, setBaseUrl, apiKey, setApiKey }),
    [baseUrl, apiKey]
  );

  return (
    <ConnectionContext.Provider value={value}>
      {children}
    </ConnectionContext.Provider>
  );
}

export function useConnection() {
  const ctx = useContext(ConnectionContext);
  if (!ctx) throw new Error("useConnection must be used within ConnectionProvider");
  return ctx;
}

