import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import api from "./api/client";
import Logo from "./components/Logo";
import { getErrorMessage } from "./utils/errors";

function StatusPage() {
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState({ status: "loading", message: "" });

  useEffect(() => {
    let active = true;
    api
      .get("/health/")
      .then(({ data }) => {
        if (active) setResult({ status: "ok", message: data.service });
      })
      .catch((error) => {
        if (active) setResult({ status: "error", message: getErrorMessage(error) });
      });
    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = () => {
    setResult({ status: "loading", message: "" });
    setAttempt((n) => n + 1);
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center gap-6 p-6">
      <Logo />
      <p className="text-slate-600">Business made clearer.</p>

      <section
        aria-live="polite"
        className="w-full rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <h1 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          API connection
        </h1>

        {result.status === "loading" && <p className="mt-2 text-slate-700">Checking connection…</p>}

        {result.status === "ok" && (
          <p className="mt-2 font-medium text-brand-700">✓ Connected to {result.message}</p>
        )}

        {result.status === "error" && (
          <div role="alert" className="mt-2">
            <p className="font-medium text-red-700">✕ Could not connect</p>
            <p className="mt-1 text-sm text-slate-700">{result.message}</p>
            <button
              type="button"
              onClick={retry}
              className="mt-3 rounded-lg bg-brand-700 px-4 py-2 text-sm font-medium text-white hover:bg-brand-900"
            >
              Try again
            </button>
          </div>
        )}
      </section>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="*" element={<StatusPage />} />
    </Routes>
  );
}
