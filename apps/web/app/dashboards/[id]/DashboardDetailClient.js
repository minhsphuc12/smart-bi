"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { apiRequest } from "../../../lib/api";

function WidgetCard({ widget, index }) {
  return (
    <div className="card stack" style={{ padding: 16, gap: 8 }}>
      <div className="row-spread">
        <strong style={{ textTransform: "capitalize" }}>{widget.type}</strong>
        <span className="badge">#{index + 1}</span>
      </div>
      <p style={{ margin: 0, fontWeight: 600 }}>{widget.title}</p>
      <pre className="mono" style={{ margin: 0, fontSize: "0.8rem", color: "var(--text-muted)" }}>
        {JSON.stringify(widget, null, 2)}
      </pre>
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
  const [lastNote, setLastNote] = useState("");

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

  async function onAiEdit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await apiRequest(`/dashboards/${id}/ai-edit`, {
        method: "POST",
        body: { prompt: editPrompt }
      });
      setPreview(res.preview);
      setLastNote(res.dashboard?.spec ? "AI edit applied (stub adds a KPI widget)." : "");
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
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
                </p>
              </div>
              <button type="button" className="btn btn-ghost" onClick={() => load()} disabled={busy}>
                Refresh
              </button>
            </div>
          </header>

          <section className="stack">
            <h2 style={{ margin: 0 }}>Widget preview</h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
                gap: 14
              }}
            >
              {dashboard.spec?.widgets?.map((w, i) => (
                <WidgetCard key={`${w.title}-${i}`} widget={w} index={i} />
              ))}
            </div>
          </section>

          <section className="card stack" style={{ padding: 22 }}>
            <h2 style={{ marginTop: 0 }}>AI edit (preview)</h2>
            <p style={{ marginTop: 0, color: "var(--text-muted)" }}>
              The MVP API applies edits immediately and returns the proposed spec as{" "}
              <span className="mono">preview</span>. Compare the JSON below before sharing externally.
            </p>
            <form className="stack" style={{ gap: 12 }} onSubmit={onAiEdit}>
              <div className="field">
                <label htmlFor="ai-prompt">Instruction</label>
                <textarea id="ai-prompt" value={editPrompt} onChange={(e) => setEditPrompt(e.target.value)} />
              </div>
              <button className="btn btn-primary" type="submit" disabled={busy}>
                {busy ? "Running…" : "Run AI edit"}
              </button>
            </form>
            {lastNote ? <p className="badge">{lastNote}</p> : null}
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
                        <td>{v.change_note}</td>
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
