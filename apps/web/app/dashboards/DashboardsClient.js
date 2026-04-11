"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "../../lib/api";

export default function DashboardsClient() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("Executive overview");
  const [prompt, setPrompt] = useState("Line chart for revenue by order date with a KPI for totals.");

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const data = await apiRequest("/dashboards");
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onCreate(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiRequest("/dashboards", { method: "POST", body: { title, prompt } });
      setOpen(false);
      setPrompt("Line chart for revenue by order date with a KPI for totals.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page stack">
      <header className="row-spread" style={{ alignItems: "flex-start", gap: 16 }}>
        <div className="stack" style={{ gap: 8 }}>
          <h1 style={{ margin: 0 }}>Dashboards</h1>
          <p style={{ margin: 0, color: "var(--text-muted)", maxWidth: 720 }}>
            Create a dashboard from a natural-language prompt, then open it to preview widgets, review
            versions, and run AI-assisted edits with an inline preview payload.
          </p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setOpen(true)} disabled={loading}>
          New dashboard
        </button>
      </header>

      {error ? (
        <p role="alert" className="badge badge-danger">
          {error}
        </p>
      ) : null}

      <div className="row" style={{ gap: 10 }}>
        <button type="button" className="btn btn-ghost" onClick={() => load()} disabled={loading}>
          Refresh list
        </button>
        <Link href="/ask" className="btn btn-ghost" style={{ textDecoration: "none" }}>
          Ask a question
        </Link>
      </div>

      {open ? (
        <div className="card stack" style={{ padding: 22 }} role="dialog" aria-modal="true" aria-labelledby="dash-create-title">
          <div className="row-spread">
            <h2 id="dash-create-title" style={{ margin: 0 }}>
              Create from prompt
            </h2>
            <button type="button" className="btn btn-ghost" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
          <form className="stack" style={{ gap: 0 }} onSubmit={onCreate}>
            <div className="field">
              <label htmlFor="dash-title">Title</label>
              <input id="dash-title" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="dash-prompt">Prompt</label>
              <textarea id="dash-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
            </div>
            <div className="row">
              <button className="btn btn-primary" type="submit" disabled={loading}>
                Generate
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {items.length === 0 ? (
        <div className="empty">No dashboards yet. Use “New dashboard” to run the stub generator.</div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: 16
          }}
        >
          {items.map((d) => (
            <Link
              key={d.id}
              href={`/dashboards/${d.id}`}
              className="card stack"
              style={{
                padding: 18,
                textDecoration: "none",
                color: "inherit",
                borderColor: "var(--border)",
                transition: "transform 0.12s ease"
              }}
            >
              <div className="row-spread" style={{ alignItems: "flex-start" }}>
                <h3 style={{ margin: 0 }}>{d.title}</h3>
                <span className="badge">#{d.id}</span>
              </div>
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
                {d.spec?.widgets?.length || 0} widget(s) · Model {d.created_by_model || "n/a"}
              </p>
              <span style={{ color: "var(--accent)", fontWeight: 700 }}>Open →</span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
