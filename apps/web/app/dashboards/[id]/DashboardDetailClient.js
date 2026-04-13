"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "../../../lib/api";
import { WidgetAreaChart, WidgetDataTable, WidgetKpiValue } from "../widgetCharts";

function GenMetaStrip({ meta }) {
  const dg = meta?.dashboard_gen;
  if (!dg || typeof dg !== "object") return null;
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
      <span className={`badge ${dg.live ? "" : "badge-warn"}`}>{dg.live ? "LLM live" : "Simulated / offline"}</span>
      {dg.parse_fallback ? <span className="badge badge-warn">Heuristic layout</span> : null}
      <span className="mono">
        {dg.provider || "—"} · {dg.model || "—"}
      </span>
      {dg.error ? (
        <span className="badge badge-danger" style={{ whiteSpace: "pre-wrap", maxWidth: "100%" }}>
          {String(dg.error)}
        </span>
      ) : null}
    </div>
  );
}

function WidgetCard({ widget, index, dataResult }) {
  const t = (widget.type || "").toLowerCase();
  const isChart = t === "line" || t === "bar" || t === "area";
  const isKpi = t === "kpi";
  const isTable = t === "table";

  const err = dataResult?.error;
  const cols = dataResult?.columns;
  const rows = dataResult?.rows;
  const hasData = Array.isArray(cols) && Array.isArray(rows) && !err;

  return (
    <div className="card stack" style={{ padding: 16, gap: 10 }}>
      <div className="row-spread">
        <strong style={{ textTransform: "capitalize" }}>{widget.type}</strong>
        <span className="badge">#{index + 1}</span>
      </div>
      <p style={{ margin: 0, fontWeight: 600 }}>{widget.title}</p>
      {widget.description ? (
        <p style={{ margin: 0, fontSize: "0.9rem", color: "var(--text-muted)" }}>{widget.description}</p>
      ) : null}

      {err ? (
        <p role="alert" className="badge badge-danger" style={{ whiteSpace: "pre-wrap", fontWeight: 400 }}>
          {err}
        </p>
      ) : null}

      {hasData && isKpi ? (
        <div
          style={{
            padding: "16px 14px",
            borderRadius: 10,
            background: "var(--surface-muted)",
            border: "1px solid var(--border)"
          }}
        >
          <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase" }}>
            {widget.field || cols[0] || "metric"}
          </p>
          <div style={{ marginTop: 6 }}>
            <WidgetKpiValue columns={cols} rows={rows} fieldHint={widget.field} />
          </div>
        </div>
      ) : null}

      {hasData && isChart ? (
        <div style={{ width: "100%" }}>
          <div className="row" style={{ gap: 10, fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 6 }}>
            {widget.x ? (
              <span>
                <strong>X</strong> <span className="mono">{widget.x}</span>
              </span>
            ) : null}
            {widget.y ? (
              <span>
                <strong>Y</strong> <span className="mono">{widget.y}</span>
              </span>
            ) : null}
          </div>
          <WidgetAreaChart
            columns={cols}
            rows={rows}
            xHint={widget.x}
            yHint={widget.y}
            variant={t === "bar" ? "bar" : t === "area" ? "area" : "line"}
          />
        </div>
      ) : null}

      {hasData && isTable ? <WidgetDataTable columns={cols} rows={rows} /> : null}

      {!hasData && !err ? (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
          Run <strong>Load live data</strong> after the widget includes executable <span className="mono">sql</span>{" "}
          (regenerate with a datasource selected so the model can emit queries).
        </p>
      ) : null}

      <details>
        <summary style={{ cursor: "pointer", fontWeight: 600, fontSize: "0.85rem" }}>SQL &amp; spec</summary>
        <div className="stack" style={{ gap: 8, marginTop: 8 }}>
          {dataResult?.sql_executed ? (
            <>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-muted)" }}>Executed (policy-hardened)</p>
              <pre className="mono sql-block" style={{ fontSize: "0.7rem", maxHeight: 160 }}>
                {dataResult.sql_executed}
              </pre>
            </>
          ) : widget.sql ? (
            <>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-muted)" }}>Widget SQL (raw)</p>
              <pre className="mono sql-block" style={{ fontSize: "0.7rem", maxHeight: 160 }}>
                {widget.sql}
              </pre>
            </>
          ) : (
            <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>No SQL on this widget.</p>
          )}
          <pre className="mono sql-block" style={{ fontSize: "0.7rem", maxHeight: 120 }}>
            {JSON.stringify(widget, null, 2)}
          </pre>
        </div>
      </details>
    </div>
  );
}

export default function DashboardDetailClient() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params?.id);
  const [dashboard, setDashboard] = useState(null);
  const [versions, setVersions] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [editPrompt, setEditPrompt] = useState("Add a KPI card for total revenue.");
  const [preview, setPreview] = useState(null);
  const [lastEditMeta, setLastEditMeta] = useState(null);
  const [connections, setConnections] = useState([]);
  const [connectionId, setConnectionId] = useState("");
  const [series, setSeries] = useState(null);
  const [dataError, setDataError] = useState("");

  const loadConnections = useCallback(async () => {
    try {
      const data = await apiRequest("/admin/connections");
      setConnections(Array.isArray(data) ? data : []);
    } catch {
      setConnections([]);
    }
  }, []);

  const load = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    setError("");
    setBusy(true);
    try {
      const dash = await apiRequest(`/dashboards/${id}`);
      setDashboard(dash);
      const vers = await apiRequest(`/dashboards/${id}/versions`);
      setVersions(Array.isArray(vers) ? vers : []);
      setPreview(null);
      setSeries(null);
      setDataError("");
    } catch (e) {
      setError(e.message);
      setDashboard(null);
    } finally {
      setBusy(false);
    }
  }, [id]);

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

  useEffect(() => {
    if (!dashboard) return;
    const saved = dashboard.connection_id;
    if (saved !== undefined && saved !== null && connections.some((c) => String(c.id) === String(saved))) {
      setConnectionId(String(saved));
    }
  }, [dashboard, connections]);

  async function onLoadLiveData() {
    if (connectionId === "" || Number.isNaN(Number(connectionId))) {
      setDataError("Choose a datasource.");
      return;
    }
    setDataError("");
    setBusy(true);
    try {
      const res = await apiRequest(`/dashboards/${id}/run-queries`, {
        method: "POST",
        body: { connection_id: Number(connectionId) }
      });
      setSeries(Array.isArray(res.series) ? res.series : []);
    } catch (e) {
      setDataError(e.message || "Failed to run queries");
      setSeries(null);
    } finally {
      setBusy(false);
    }
  }

  async function onAiEdit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setLastEditMeta(null);
    try {
      const body = { prompt: editPrompt };
      if (connectionId !== "" && !Number.isNaN(Number(connectionId))) {
        body.connection_id = Number(connectionId);
      }
      const res = await apiRequest(`/dashboards/${id}/ai-edit`, {
        method: "POST",
        body
      });
      setPreview(res.preview);
      setLastEditMeta(res.meta || null);
      setSeries(null);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function dataForIndex(i) {
    if (!series || !Array.isArray(series)) return null;
    return series.find((s) => s.widget_index === i) || null;
  }

  if (!Number.isFinite(id)) {
    return (
      <main className="page">
        <p>Invalid dashboard id.</p>
      </main>
    );
  }

  return (
    <main className="page stack" style={{ maxWidth: 1100 }}>
      <div className="row" style={{ gap: 12 }}>
        <button type="button" className="btn btn-ghost" onClick={() => router.push("/dashboards")}>
          ← All dashboards
        </button>
        <Link href="/ask" className="btn btn-ghost" style={{ textDecoration: "none" }}>
          Ask Data
        </Link>
      </div>

      {error ? (
        <p role="alert" className="badge badge-danger">
          {error}
        </p>
      ) : null}

      {!dashboard && !error ? (
        <p style={{ color: "var(--text-muted)" }}>{busy ? "Loading…" : "Not found."}</p>
      ) : null}

      {dashboard ? (
        <>
          <header className="stack" style={{ gap: 8 }}>
            <div className="row-spread" style={{ alignItems: "flex-start", gap: 12 }}>
              <div>
                <p className="badge" style={{ marginBottom: 8 }}>
                  Dashboard #{dashboard.id}
                </p>
                <h1 style={{ margin: 0 }}>{dashboard.title}</h1>
                <p style={{ margin: 0, color: "var(--text-muted)" }}>
                  Generated with model <span className="mono">{dashboard.created_by_model || "n/a"}</span>
                  {dashboard.connection_id != null ? (
                    <>
                      {" "}
                      · Saved datasource <span className="mono">#{dashboard.connection_id}</span>
                    </>
                  ) : null}
                </p>
              </div>
              <button type="button" className="btn btn-ghost" onClick={() => load()} disabled={busy}>
                Refresh
              </button>
            </div>
            <GenMetaStrip meta={dashboard.meta} />
          </header>

          <section className="card stack" style={{ padding: 18, gap: 12 }}>
            <div className="row-spread" style={{ alignItems: "flex-end", gap: 12, flexWrap: "wrap" }}>
              <div>
                <h2 style={{ margin: 0 }}>Live data</h2>
                <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: "0.9rem", maxWidth: 640 }}>
                  Executes each widget&apos;s <span className="mono">sql</span> on the server (read-only, same table
                  allowlist as Ask Data). Create or AI-edit the dashboard <strong>with a datasource</strong> so widgets
                  include SQL; then choose connection and load.
                </p>
              </div>
              <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                {connections.length ? (
                  <select
                    className="field"
                    style={{ minWidth: 200, padding: "8px 10px", borderRadius: 8 }}
                    value={connectionId}
                    onChange={(e) => setConnectionId(e.target.value)}
                    aria-label="Datasource for queries"
                  >
                    {connections.map((c) => (
                      <option key={c.id} value={String(c.id)}>
                        {c.name || `Connection ${c.id}`} (#{c.id})
                      </option>
                    ))}
                  </select>
                ) : null}
                <button type="button" className="btn btn-primary" onClick={() => void onLoadLiveData()} disabled={busy}>
                  {busy ? "Running…" : "Load live data"}
                </button>
              </div>
            </div>
            {dataError ? (
              <p role="alert" className="badge badge-danger">
                {dataError}
              </p>
            ) : null}
            {series?.length ? (
              <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
                Loaded {series.length} widget query result(s).
              </p>
            ) : null}
          </section>

          <section className="stack">
            <h2 style={{ margin: 0 }}>Widget preview</h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                gap: 14
              }}
            >
              {dashboard.spec?.widgets?.map((w, i) => (
                <WidgetCard key={`${w.title}-${i}`} widget={w} index={i} dataResult={dataForIndex(i)} />
              ))}
            </div>
          </section>

          <section className="card stack" style={{ padding: 22 }}>
            <h2 style={{ marginTop: 0 }}>AI edit</h2>
            <p style={{ marginTop: 0, color: "var(--text-muted)" }}>
              The model receives your current widget list as JSON and must return the full updated spec. The API
              saves the new version immediately and returns <span className="mono">preview</span> for inspection.
              Pass the same datasource to refresh <span className="mono">sql</span> hints.
            </p>
            {connections.length ? (
              <div className="field">
                <label htmlFor="edit-conn">Datasource context (optional)</label>
                <select
                  id="edit-conn"
                  value={connectionId}
                  onChange={(e) => setConnectionId(e.target.value)}
                  aria-label="Datasource for schema hints on edit"
                >
                  {connections.map((c) => (
                    <option key={c.id} value={String(c.id)}>
                      {c.name || `Connection ${c.id}`} (#{c.id})
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
            <form className="stack" style={{ gap: 12 }} onSubmit={onAiEdit}>
              <div className="field">
                <label htmlFor="ai-prompt">Instruction</label>
                <textarea id="ai-prompt" value={editPrompt} onChange={(e) => setEditPrompt(e.target.value)} />
              </div>
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Running…" : "Run AI edit"}
              </button>
            </form>
            {lastEditMeta ? (
              <div className="stack" style={{ gap: 8 }}>
                <p style={{ margin: 0, fontWeight: 700 }}>Last edit — generation</p>
                <GenMetaStrip meta={lastEditMeta} />
              </div>
            ) : null}
            {preview ? (
              <div className="stack" style={{ gap: 10 }}>
                <h3 style={{ margin: 0 }}>Last preview payload</h3>
                <pre className="sql-block" style={{ maxHeight: 320 }}>
                  {JSON.stringify(preview, null, 2)}
                </pre>
              </div>
            ) : null}
          </section>

          <section className="stack">
            <h2 style={{ margin: 0 }}>Version history</h2>
            {versions.length === 0 ? (
              <div className="empty">No versions recorded.</div>
            ) : (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Change note</th>
                      <th>Widgets</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versions.map((v) => (
                      <tr key={v.version}>
                        <td className="mono">{v.version}</td>
                        <td style={{ maxWidth: 420, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
                          {v.change_note}
                        </td>
                        <td className="mono">{v.spec?.widgets?.length ?? 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
              Rollback to a prior version is not exposed in the API yet; history is read-only in the UI.
            </p>
          </section>
        </>
      ) : null}
    </main>
  );
}
