"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { apiRequest } from "../../lib/api";

const SUGGESTIONS = [
  "How many rows are in orders?",
  "Show latest records for customer_id",
  "Sum of revenue by day last week?",
  "What columns mention inventory?"
];

function exportCsv(columns, rows) {
  const esc = (v) => {
    const s = String(v ?? "");
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const lines = [columns.map(esc).join(",")];
  for (const row of rows) {
    lines.push(row.map(esc).join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "ask-data-export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function EvidenceStrip({ evidence }) {
  if (!evidence || typeof evidence !== "object") return null;
  const kind = evidence.query_kind || "—";
  const table = evidence.table || "—";
  const rc = evidence.row_count;
  const ms = evidence.execution_ms;
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
      <span className="mono">kind: {kind}</span>
      <span className="mono">table: {table}</span>
      {typeof rc === "number" ? <span>{rc} rows</span> : null}
      {typeof ms === "number" && ms > 0 ? <span>{ms} ms</span> : null}
    </div>
  );
}

function MessageBubble({ message, onCopy }) {
  if (message.role === "user") {
    return (
      <div style={{ alignSelf: "flex-end", maxWidth: "min(720px, 100%)" }}>
        <div className="card" style={{ padding: 14, background: "var(--surface-muted)", borderColor: "var(--border)" }}>
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{message.text}</p>
        </div>
      </div>
    );
  }

  const lowConfidence = typeof message.confidence === "number" && message.confidence < 0.7;
  const warnings = Array.isArray(message.warnings) ? message.warnings : [];

  return (
    <div style={{ alignSelf: "stretch" }} className="stack">
      <div className="card stack" style={{ padding: 18, gap: 14 }}>
        <div className="row-spread" style={{ alignItems: "flex-start", gap: 12 }}>
          <div style={{ flex: "1 1 240px" }}>
            <p className="badge" style={{ marginBottom: 8 }}>
              Answer
            </p>
            <p style={{ margin: 0, fontSize: "1.05rem", whiteSpace: "pre-wrap" }}>{message.answer}</p>
          </div>
          <div className="stack" style={{ gap: 8, alignItems: "flex-end", flexShrink: 0 }}>
            <div className="row" style={{ gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
              <span className="badge">{`Confidence ${Math.round((message.confidence || 0) * 100)}%`}</span>
              {lowConfidence ? <span className="badge badge-warn">Review suggested</span> : null}
            </div>
            <button type="button" className="btn btn-ghost" style={{ fontSize: "0.85rem", padding: "6px 12px" }} onClick={() => onCopy(message.answer)}>
              Copy answer
            </button>
          </div>
        </div>

        <EvidenceStrip evidence={message.evidence} />

        {warnings.length ? (
          <div className="badge badge-warn" style={{ alignSelf: "flex-start", whiteSpace: "pre-wrap" }}>
            {warnings.join(" · ")}
          </div>
        ) : null}

        <details>
          <summary style={{ cursor: "pointer", fontWeight: 700 }}>SQL used</summary>
          <pre className="sql-block" style={{ marginTop: 10 }}>
            {message.sql}
          </pre>
        </details>

        <div>
          <div className="row-spread" style={{ marginBottom: 8, alignItems: "center" }}>
            <p style={{ margin: 0, fontWeight: 700 }}>Result preview</p>
            {message.columns?.length && message.rows?.length ? (
              <button
                type="button"
                className="btn btn-ghost"
                style={{ fontSize: "0.85rem", padding: "6px 12px" }}
                onClick={() => exportCsv(message.columns, message.rows)}
              >
                Download CSV
              </button>
            ) : null}
          </div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  {message.columns?.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {message.rows?.length ? (
                  message.rows.map((row, idx) => (
                    <tr key={idx}>
                      {row.map((cell, i) => (
                        <td key={i} className="mono">
                          {String(cell)}
                        </td>
                      ))}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={message.columns?.length || 1} style={{ color: "var(--text-muted)" }}>
                      Empty result set
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {message.meta ? (
          <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.85rem" }} className="mono">
            Models · SQL: {message.meta.sql_model} · Answer: {message.meta.answer_model}
          </p>
        ) : null}
      </div>
    </div>
  );
}

function LoadingCard() {
  return (
    <div className="card stack" style={{ padding: 18, gap: 12, alignSelf: "stretch", opacity: 0.85 }}>
      <div style={{ height: 14, width: 88, borderRadius: 8, background: "var(--surface-muted)" }} />
      <div style={{ height: 20, width: "92%", borderRadius: 8, background: "var(--surface-muted)" }} />
      <div style={{ height: 20, width: "78%", borderRadius: 8, background: "var(--surface-muted)" }} />
      <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>Running read-only preview…</p>
    </div>
  );
}

export default function AskPageClient() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [connections, setConnections] = useState([]);
  const [connectionId, setConnectionId] = useState("");
  const bottomRef = useRef(null);

  const loadConnections = useCallback(async () => {
    try {
      const data = await apiRequest("/admin/connections");
      setConnections(Array.isArray(data) ? data : []);
    } catch {
      setConnections([]);
    }
  }, []);

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
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const copyAnswer = useCallback((text) => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(text);
    }
  }, []);

  const clearConversation = useCallback(() => {
    setMessages([]);
    setError("");
  }, []);

  async function onSubmit(e) {
    e?.preventDefault?.();
    const trimmed = question.trim();
    if (!trimmed) return;
    if (connectionId === "" || Number.isNaN(Number(connectionId))) {
      setError("Choose a datasource connection in the sidebar.");
      return;
    }
    setError("");
    setLoading(true);
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: trimmed }]);
    setQuestion("");
    try {
      const body = { question: trimmed, connection_id: Number(connectionId) };
      const data = await apiRequest("/chat/questions", { method: "POST", body });
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          answer: data.answer,
          sql: data.sql,
          columns: data.columns,
          rows: data.rows,
          confidence: data.confidence,
          warnings: data.warnings,
          evidence: data.evidence,
          meta: data.meta
        }
      ]);
    } catch (err) {
      setError(err.message || "Request failed");
      setMessages((prev) => prev.slice(0, -1));
      setQuestion(trimmed);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (!loading && question.trim()) {
        void onSubmit();
      }
    }
  }

  return (
    <main className="page" style={{ maxWidth: 1120, minHeight: "72vh" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr)",
          gap: 24,
          alignItems: "start"
        }}
        className="ask-page-grid"
      >
        <style>{`
          @media (min-width: 960px) {
            .ask-page-grid { grid-template-columns: minmax(0, 1fr) minmax(260px, 300px) !important; }
          }
        `}</style>

        <div className="stack" style={{ gap: 20, minWidth: 0 }}>
          <header className="row-spread" style={{ alignItems: "flex-start", gap: 16 }}>
            <div className="stack" style={{ gap: 8 }}>
              <h1 style={{ margin: 0 }}>Ask Data</h1>
              <p style={{ margin: 0, color: "var(--text-muted)", maxWidth: 720 }}>
                Ask in natural language against a configured datasource, inspect the narrative, then audit SQL and
                tabular evidence. The API runs read-only NL2SQL (LLM + semantic layer + live schema, sqlglot policy)
                when provider API keys are configured—never writes. Missing keys return a clear error instead of a
                degraded preview.
              </p>
            </div>
            <div className="row" style={{ gap: 8, flexShrink: 0 }}>
              <button type="button" className="btn btn-ghost" onClick={clearConversation} disabled={messages.length === 0}>
                New conversation
              </button>
              <Link href="/dashboards" className="btn btn-ghost" style={{ textDecoration: "none" }}>
                Dashboards
              </Link>
            </div>
          </header>

          <div
            className="stack"
            style={{
              flex: 1,
              gap: 16,
              padding: 18,
              borderRadius: "var(--radius)",
              border: "1px dashed var(--border)",
              background: "rgba(255,255,255,0.65)",
              minHeight: 320,
              maxHeight: "min(62vh, 720px)",
              overflowY: "auto"
            }}
          >
            {messages.length === 0 && !loading ? (
              <div className="stack" style={{ gap: 16 }}>
                <div className="empty" style={{ background: "#fff" }}>
                  No questions yet. Pick a suggestion or type your own. Answers always use the datasource you select in
                  the sidebar (capped, read-only).
                </div>
                <div className="row" style={{ gap: 8, flexWrap: "wrap" }}>
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="btn btn-ghost"
                      style={{ fontSize: "0.85rem", padding: "8px 12px" }}
                      onClick={() => setQuestion(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="stack" style={{ gap: 16 }}>
                {messages.map((m) => (
                  <MessageBubble key={m.id} message={m} onCopy={copyAnswer} />
                ))}
                {loading ? <LoadingCard /> : null}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <form className="card stack" style={{ padding: 16, gap: 12 }} onSubmit={onSubmit}>
            <label htmlFor="q" className="sr-only">
              Question
            </label>
            <textarea
              id="q"
              placeholder="Ask about revenue, customers, row counts, totals…"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={onKeyDown}
              rows={3}
              disabled={loading}
            />
            {error ? (
              <p role="alert" className="badge badge-danger">
                {error}
              </p>
            ) : null}
            <div className="row-spread">
              <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.9rem" }}>
                Press <kbd className="mono">⌘</kbd> + <kbd className="mono">Enter</kbd> (or Ctrl+Enter) to send. SQL stays
                collapsed until you expand it.
              </p>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading || !question.trim() || connectionId === ""}
              >
                {loading ? "Working…" : "Ask"}
              </button>
            </div>
          </form>
        </div>

        <aside className="card stack" style={{ padding: 18, gap: 16, position: "sticky", top: 24 }}>
          <h2 style={{ margin: 0, fontSize: "1.1rem" }}>Datasource</h2>
          <div className="field" style={{ marginBottom: 0 }}>
            <label htmlFor="conn">Connection</label>
            <select id="conn" value={connectionId} onChange={(e) => setConnectionId(e.target.value)} disabled={loading}>
              <option value="">{connections.length ? "Select a connection…" : "No connections — add one in Admin"}</option>
              {connections.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  #{c.id} · {c.name} ({c.source_type})
                </option>
              ))}
            </select>
            <p style={{ margin: "6px 0 0", fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.45 }}>
              Run <strong>Introspect</strong> in Admin for faster first asks. Configure <strong>AI routing</strong>{" "}
              profiles and provider API keys on the server; without them, Ask returns an error instead of a stub answer.
            </p>
          </div>
          <div className="stack" style={{ gap: 10, fontSize: "0.88rem", color: "var(--text-muted)" }}>
            <p style={{ margin: 0, fontWeight: 700, color: "var(--text)" }}>
              Requirements
            </p>
            <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.5 }}>
              <li>
                <span className="mono">sql_gen</span> and <span className="mono">answer_gen</span> providers need valid
                API keys
              </li>
              <li>Generated SQL is read-only (SELECT / WITH), allowlisted to visible tables, row-capped</li>
            </ul>
          </div>
          <Link href="/admin" className="btn btn-ghost" style={{ textDecoration: "none", justifyContent: "center" }}>
            Open Admin
          </Link>
        </aside>
      </div>
    </main>
  );
}
