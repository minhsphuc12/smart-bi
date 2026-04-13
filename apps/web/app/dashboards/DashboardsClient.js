"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "../../lib/api";

function GenMetaStrip({ meta }) {
  const dg = meta?.dashboard_gen;
  if (!dg || typeof dg !== "object") return null;
  const live = dg.live;
  return (
    <div
      className="row"
      style={{
        flexWrap: "wrap",
        gap: 8,
        padding: "10px 12px",
        borderRadius: 10,
        background: "var(--surface-muted)",
        border: "1px solid var(--border)",
        fontSize: "0.8rem",
        color: "var(--text-muted)"
      }}
    >
      <span className={`badge ${live ? "" : "badge-warn"}`}>{live ? "LLM live" : "Offline"}</span>
      <span className="mono">
        {dg.provider || "—"} · {dg.model || "—"}
      </span>
      {dg.error ? (
        <span className="badge badge-danger" style={{ whiteSpace: "pre-wrap" }}>
          {String(dg.error)}
        </span>
      ) : null}
    </div>
  );
}

export default function DashboardsClient() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("Executive overview");
  const [prompt, setPrompt] = useState(
    "Line chart for revenue by order date with a KPI for totals."
  );
  const [connections, setConnections] = useState([]);
  const [connectionId, setConnectionId] = useState("");
  const [lastCreateMeta, setLastCreateMeta] = useState(null);

  const loadConnections = useCallback(async () => {
    try {
      const data = await apiRequest("/admin/connections");
      setConnections(Array.isArray(data) ? data : []);
    } catch {
      setConnections([]);
    }
  }, []);

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

  useEffect(() => {
    loadConnections();
  }, [loadConnections]);

  useEffect(() => {
    if (!connections.length) {
      setConnectionId("");
      return;
    }
    setConnectionId((prev) => {
      if (prev === "") return String(connections[0].id);
      const stillThere = connections.some((c) => String(c.id) === prev);
      return stillThere ? prev : String(connections[0].id);
    });
  }, [connections]);

  async function onCreate(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setLastCreateMeta(null);
    try {
      const body = { title, prompt };
      if (connectionId !== "" && !Number.isNaN(Number(connectionId))) {
        body.connection_id = Number(connectionId);
      }
      const created = await apiRequest("/dashboards", { method: "POST", body });
      setLastCreateMeta(created.meta || null);
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
            Describe the layout you want; the API calls <span className="mono">dashboard_gen</span> over HTTPS (provider
            API keys required). Pick a <strong>datasource</strong> so the model can emit per-widget{" "}
            <span className="mono">sql</span>, then on the dashboard page use <strong>Load live data</strong> to run
            those queries and render charts.
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

      {lastCreateMeta ? (
        <div className="stack" style={{ gap: 8 }}>
          <p style={{ margin: 0, fontWeight: 700 }}>Last create — generation</p>
          <GenMetaStrip meta={lastCreateMeta} />
        </div>
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
        <div
          className="card stack"
          style={{ padding: 22 }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="dash-create-title"
        >
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
            {connections.length ? (
              <div className="field">
                <label htmlFor="dash-conn">Datasource context (optional)</label>
                <select
                  id="dash-conn"
                  value={connectionId}
                  onChange={(e) => setConnectionId(e.target.value)}
                  aria-label="Datasource for schema hints"
                >
                  {connections.map((c) => (
                    <option key={c.id} value={String(c.id)}>
                      {c.name || `Connection ${c.id}`} (#{c.id})
                    </option>
                  ))}
                </select>
                <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Uses cached introspection only; run <strong>Introspect</strong> in Admin if the list is empty
                  server-side.
                </p>
              </div>
            ) : null}
            <div className="field">
              <label htmlFor="dash-prompt">Prompt</label>
              <textarea id="dash-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} required />
            </div>
            <div className="row">
              <button className="btn btn-primary" type="submit" disabled={loading}>
                {loading ? "Generating…" : "Generate"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {items.length === 0 ? (
        <div className="empty">
          No dashboards yet. Use “New dashboard” to generate a spec from your prompt (requires configured LLM API keys).
        </div>
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
              {d.meta?.dashboard_gen ? (
                <p style={{ margin: 0, fontSize: "0.8rem" }}>
                  <span className={d.meta.dashboard_gen.live ? "badge" : "badge badge-warn"}>
                    {d.meta.dashboard_gen.live ? "LLM" : "Offline"}
                  </span>
                </p>
              ) : null}
              <span style={{ color: "var(--accent)", fontWeight: 700 }}>Open →</span>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
