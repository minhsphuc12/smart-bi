"use client";

import Link from "next/link";
import { useState } from "react";

import { apiRequest } from "../../lib/api";

function MessageBubble({ message }) {
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
        <div className="row-spread" style={{ alignItems: "flex-start" }}>
          <div>
            <p className="badge" style={{ marginBottom: 8 }}>
              Answer
            </p>
            <p style={{ margin: 0, fontSize: "1.05rem" }}>{message.answer}</p>
          </div>
          <div className="row" style={{ gap: 8, justifyContent: "flex-end" }}>
            <span className="badge">{`Confidence ${Math.round((message.confidence || 0) * 100)}%`}</span>
            {lowConfidence ? <span className="badge badge-warn">Review suggested</span> : null}
          </div>
        </div>

        {warnings.length ? (
          <div className="badge badge-warn" style={{ alignSelf: "flex-start" }}>
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
          <p style={{ margin: "0 0 8px", fontWeight: 700 }}>Result preview</p>
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

export default function AskPageClient() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;
    setError("");
    setLoading(true);
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: "user", text: trimmed }]);
    setQuestion("");
    try {
      const data = await apiRequest("/chat/questions", { method: "POST", body: { question: trimmed } });
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

  return (
    <main className="page stack" style={{ maxWidth: 960, minHeight: "70vh" }}>
      <header className="stack" style={{ gap: 8 }}>
        <h1 style={{ margin: 0 }}>Ask Data</h1>
        <p style={{ margin: 0, color: "var(--text-muted)" }}>
          Pose a business question, inspect the narrative answer, then peel back SQL and tabular evidence.
          Responses use the MVP chat endpoint with simulated models.
        </p>
      </header>

      <div
        className="stack"
        style={{
          flex: 1,
          gap: 16,
          padding: 18,
          borderRadius: "var(--radius)",
          border: "1px dashed var(--border)",
          background: "rgba(255,255,255,0.6)"
        }}
      >
        {messages.length === 0 ? (
          <div className="empty" style={{ background: "#fff" }}>
            No questions yet. Try{" "}
            <span className="mono" style={{ color: "var(--text)" }}>
              Revenue by day last week?
            </span>
          </div>
        ) : (
          <div className="stack" style={{ gap: 16 }}>
            {messages.map((m) => (
              <MessageBubble key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      <form className="card stack" style={{ padding: 16, gap: 12 }} onSubmit={onSubmit}>
        <label htmlFor="q" className="sr-only">
          Question
        </label>
        <textarea
          id="q"
          placeholder="Ask about revenue, customers, inventory…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
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
            SQL is collapsed by default—expand the disclosure triangle to audit the statement.
          </p>
          <div className="row">
            <Link href="/dashboards" className="btn btn-ghost" style={{ textDecoration: "none" }}>
              Open dashboards
            </Link>
            <button className="btn btn-primary" type="submit" disabled={loading || !question.trim()}>
              {loading ? "Thinking…" : "Ask"}
            </button>
          </div>
        </div>
      </form>
    </main>
  );
}
