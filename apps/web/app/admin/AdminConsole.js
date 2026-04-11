"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { apiRequest } from "../../lib/api";
import { useAuth } from "../providers";

function useAsync(fn, deps) {
  useEffect(() => {
    fn();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

function SemanticEditor({ segment, title }) {
  const [items, setItems] = useState([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await apiRequest(`/admin/semantic/${segment}`);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e.message);
    }
  }, [segment]);

  useAsync(() => {
    load();
  }, [load]);

  async function onCreate(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await apiRequest(`/admin/semantic/${segment}`, {
        method: "POST",
        body: { name, description }
      });
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="row-spread">
        <h2 style={{ margin: 0 }}>{title}</h2>
        <button type="button" className="btn btn-ghost" onClick={() => load()} disabled={busy}>
          Refresh
        </button>
      </div>
      {error ? (
        <p className="badge badge-danger" role="alert">
          {error}
        </p>
      ) : null}

      <form className="card" style={{ padding: 18 }} onSubmit={onCreate}>
        <h3 style={{ marginTop: 0 }}>Add entry</h3>
        <div className="field">
          <label htmlFor={`${segment}-name`}>Name</label>
          <input
            id={`${segment}-name`}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor={`${segment}-desc`}>Description</label>
          <textarea id={`${segment}-desc`} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          Save new
        </button>
      </form>

      {items.length === 0 ? (
        <div className="empty">No rows yet. Add a table alias, metric, or term to guide Ask Data.</div>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Description</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <SemanticRow
                  key={item.id}
                  segment={segment}
                  item={item}
                  onSaved={load}
                  busy={busy}
                  setBusy={setBusy}
                  setError={setError}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SemanticRow({ segment, item, onSaved, busy, setBusy, setError }) {
  const [desc, setDesc] = useState(item.description || "");

  useEffect(() => {
    setDesc(item.description || "");
  }, [item.description, item.id]);

  async function onSave() {
    setBusy(true);
    setError("");
    try {
      await apiRequest(`/admin/semantic/${segment}/${item.id}`, {
        method: "PUT",
        body: { name: item.name, description: desc }
      });
      await onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td className="mono">{item.id}</td>
      <td style={{ fontWeight: 600 }}>{item.name}</td>
      <td style={{ minWidth: 220 }}>
        <textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} style={{ width: "100%" }} />
      </td>
      <td>
        <button type="button" className="btn btn-ghost" onClick={onSave} disabled={busy}>
          Save
        </button>
      </td>
    </tr>
  );
}

const AI_TASKS = ["sql_gen", "answer_gen", "dashboard_gen", "extract_classify"];

const SOURCE_TYPE_LABELS = {
  oracle: "Oracle",
  postgresql: "PostgreSQL",
  mysql: "MySQL"
};

export default function AdminConsole() {
  const { ready, isAdmin } = useAuth();
  const [mainTab, setMainTab] = useState("connections");
  const [semanticTab, setSemanticTab] = useState("tables");

  const [connections, setConnections] = useState([]);
  const [connError, setConnError] = useState("");
  const [connBusy, setConnBusy] = useState(false);
  const [form, setForm] = useState({
    source_type: "oracle",
    name: "Local Oracle",
    host: "localhost",
    port: 1521,
    service_name: "ORCLPDB1",
    database: "",
    username: "app_user",
    password: ""
  });

  const defaultPortForSource = (t) => {
    if (t === "postgresql") return 5432;
    if (t === "mysql") return 3306;
    return 1521;
  };

  function setSourceType(nextType) {
    setForm((f) => ({
      ...f,
      source_type: nextType,
      port: defaultPortForSource(nextType)
    }));
  }

  function connectionTargetDisplay(c) {
    const kind = c.source_type || "oracle";
    const suffix = kind === "oracle" ? c.service_name : c.database;
    return `${c.host}:${c.port}/${suffix || "—"}`;
  }
  const [actionMessage, setActionMessage] = useState("");
  const [introspect, setIntrospect] = useState(null);

  const loadConnections = useCallback(async () => {
    setConnError("");
    try {
      const data = await apiRequest("/admin/connections");
      setConnections(Array.isArray(data) ? data : []);
    } catch (e) {
      setConnError(e.message);
    }
  }, []);

  useEffect(() => {
    if (ready && isAdmin && mainTab === "connections") {
      loadConnections();
    }
  }, [ready, isAdmin, mainTab, loadConnections]);

  async function createConnection(e) {
    e.preventDefault();
    setConnBusy(true);
    setConnError("");
    setActionMessage("");
    try {
      await apiRequest("/admin/connections", { method: "POST", body: form });
      setForm((f) => ({ ...f, password: "" }));
      await loadConnections();
      setActionMessage("Connection saved (in-memory stub).");
    } catch (err) {
      setConnError(err.message);
    } finally {
      setConnBusy(false);
    }
  }

  async function testConnection(id) {
    setConnBusy(true);
    setConnError("");
    setActionMessage("");
    try {
      const res = await apiRequest(`/admin/connections/${id}/test`, { method: "POST" });
      setActionMessage(`Test: ${res.status} (connection #${res.connection_id})`);
    } catch (e) {
      setConnError(e.message);
    } finally {
      setConnBusy(false);
    }
  }

  async function runIntrospect(id) {
    setConnBusy(true);
    setConnError("");
    setActionMessage("");
    try {
      const res = await apiRequest(`/admin/connections/${id}/introspect`, { method: "POST" });
      setIntrospect(res);
      setActionMessage("Introspection finished (sample schema).");
    } catch (e) {
      setConnError(e.message);
    } finally {
      setConnBusy(false);
    }
  }

  const [profiles, setProfiles] = useState({});
  const [aiError, setAiError] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiMessage, setAiMessage] = useState("");
  const [routingForm, setRoutingForm] = useState({
    task: "sql_gen",
    provider: "providerA",
    model: "sql-model",
    temperature: 0,
    max_tokens: 1200,
    timeout: 30,
    cost_limit: 1
  });

  const loadProfiles = useCallback(async () => {
    setAiError("");
    try {
      const data = await apiRequest("/admin/ai-routing/profiles");
      setProfiles(data && typeof data === "object" ? data : {});
    } catch (e) {
      setAiError(e.message);
    }
  }, []);

  useEffect(() => {
    if (ready && isAdmin && mainTab === "ai") {
      loadProfiles();
    }
  }, [ready, isAdmin, mainTab, loadProfiles]);

  async function saveProfile(e) {
    e.preventDefault();
    setAiBusy(true);
    setAiError("");
    setAiMessage("");
    try {
      await apiRequest("/admin/ai-routing/profiles", { method: "POST", body: routingForm });
      await loadProfiles();
      setAiMessage("Profile saved.");
    } catch (e) {
      setAiError(e.message);
    } finally {
      setAiBusy(false);
    }
  }

  async function validateProfile() {
    setAiBusy(true);
    setAiError("");
    setAiMessage("");
    try {
      const res = await apiRequest("/admin/ai-routing/validate", { method: "POST", body: routingForm });
      setAiMessage(`${res.status} for task ${res.task}`);
    } catch (e) {
      setAiError(e.message);
    } finally {
      setAiBusy(false);
    }
  }

  const profileEntries = useMemo(() => Object.entries(profiles), [profiles]);

  if (!ready) {
    return (
      <main className="page">
        <p style={{ color: "var(--text-muted)" }}>Loading…</p>
      </main>
    );
  }

  if (!isAdmin) {
    return (
      <main className="page stack" style={{ maxWidth: 640 }}>
        <h1 style={{ marginBottom: 8 }}>Admin console</h1>
        <div className="card stack" style={{ padding: 22 }}>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Admin tools are limited to the Admin role. Sign in with a username that starts with{" "}
            <span className="mono">admin</span> (development stub).
          </p>
          <div className="row">
            <Link className="btn btn-primary" href="/login" style={{ textDecoration: "none" }}>
              Sign in
            </Link>
            <Link className="btn btn-ghost" href="/" style={{ textDecoration: "none" }}>
              Home
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="page stack">
      <header className="stack" style={{ gap: 8 }}>
        <h1 style={{ margin: 0 }}>Admin console</h1>
        <p style={{ margin: 0, color: "var(--text-muted)", maxWidth: 820 }}>
          Manage database connections (Oracle, PostgreSQL, MySQL), semantic metadata, and AI routing
          profiles. All endpoints are backed by the FastAPI MVP stubs—perfect for exercising the UX
          before production services land.
        </p>
      </header>

      <div className="tabs" role="tablist" aria-label="Admin sections">
        {[
          { id: "connections", label: "Connections" },
          { id: "semantic", label: "Semantic layer" },
          { id: "ai", label: "AI routing" }
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            className="tab"
            aria-selected={mainTab === tab.id}
            onClick={() => setMainTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mainTab === "connections" ? (
        <section className="stack">
          <div className="card stack" style={{ padding: 22 }}>
            <h2 style={{ marginTop: 0 }}>New connection</h2>
            <form className="stack" style={{ gap: 0 }} onSubmit={createConnection}>
              <div className="field" style={{ maxWidth: 320 }}>
                <label htmlFor="c-source">Source type</label>
                <select
                  id="c-source"
                  value={form.source_type}
                  onChange={(e) => setSourceType(e.target.value)}
                >
                  <option value="oracle">Oracle</option>
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mysql">MySQL</option>
                </select>
              </div>
              <div className="row" style={{ gap: 16 }}>
                <div className="field" style={{ flex: "1 1 200px" }}>
                  <label htmlFor="c-name">Name</label>
                  <input
                    id="c-name"
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    required
                  />
                </div>
                <div className="field" style={{ flex: "1 1 200px" }}>
                  <label htmlFor="c-host">Host</label>
                  <input
                    id="c-host"
                    value={form.host}
                    onChange={(e) => setForm({ ...form, host: e.target.value })}
                    required
                  />
                </div>
                <div className="field" style={{ flex: "1 1 120px" }}>
                  <label htmlFor="c-port">Port</label>
                  <input
                    id="c-port"
                    type="number"
                    value={form.port}
                    onChange={(e) => setForm({ ...form, port: Number(e.target.value) })}
                    required
                  />
                </div>
              </div>
              {form.source_type === "oracle" ? (
                <div className="field">
                  <label htmlFor="c-service">Service name</label>
                  <input
                    id="c-service"
                    value={form.service_name}
                    onChange={(e) => setForm({ ...form, service_name: e.target.value })}
                    required
                  />
                </div>
              ) : (
                <div className="field">
                  <label htmlFor="c-database">Database name</label>
                  <input
                    id="c-database"
                    value={form.database}
                    onChange={(e) => setForm({ ...form, database: e.target.value })}
                    required
                  />
                </div>
              )}
              <div className="row" style={{ gap: 16 }}>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="c-user">Username</label>
                  <input
                    id="c-user"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value })}
                    autoComplete="off"
                    required
                  />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="c-pass">Password</label>
                  <input
                    id="c-pass"
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    autoComplete="new-password"
                  />
                </div>
              </div>
              {connError ? (
                <p className="badge badge-danger" role="alert">
                  {connError}
                </p>
              ) : null}
              {actionMessage ? <p className="badge">{actionMessage}</p> : null}
              <button className="btn btn-primary" type="submit" disabled={connBusy}>
                Save connection
              </button>
            </form>
          </div>

          <div className="card stack" style={{ padding: 22 }}>
            <div className="row-spread">
              <h2 style={{ margin: 0 }}>Saved connections</h2>
              <button type="button" className="btn btn-ghost" onClick={() => loadConnections()} disabled={connBusy}>
                Refresh
              </button>
            </div>
            {connections.length === 0 ? (
              <div className="empty">No connections yet. Create one to enable test and introspect actions.</div>
            ) : (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Target</th>
                      <th>User</th>
                      <th>Secret</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {connections.map((c) => (
                      <tr key={c.id}>
                        <td className="mono">{c.id}</td>
                        <td style={{ fontWeight: 600 }}>{c.name}</td>
                        <td className="mono">{SOURCE_TYPE_LABELS[c.source_type || "oracle"]}</td>
                        <td className="mono">{connectionTargetDisplay(c)}</td>
                        <td>{c.username}</td>
                        <td>{c.password}</td>
                        <td className="row" style={{ gap: 8 }}>
                          <button type="button" className="btn btn-ghost" onClick={() => testConnection(c.id)} disabled={connBusy}>
                            Test
                          </button>
                          <button
                            type="button"
                            className="btn btn-ghost"
                            onClick={() => runIntrospect(c.id)}
                            disabled={connBusy}
                          >
                            Introspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {introspect ? (
              <div className="stack" style={{ marginTop: 8 }}>
                <h3 style={{ margin: 0 }}>Latest introspection</h3>
                <div className="table-wrap">
                  <table className="data">
                    <thead>
                      <tr>
                        <th>Table</th>
                        <th>Columns</th>
                      </tr>
                    </thead>
                    <tbody>
                      {introspect.tables?.map((t) => (
                        <tr key={t.name}>
                          <td className="mono">{t.name}</td>
                          <td>{t.columns?.join(", ")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </div>
        </section>
      ) : null}

      {mainTab === "semantic" ? (
        <section className="stack">
          <div className="tabs" role="tablist" aria-label="Semantic editors">
            {[
              { id: "tables", label: "Tables" },
              { id: "relationships", label: "Relationships" },
              { id: "dictionary", label: "Dictionary" },
              { id: "metrics", label: "Metrics" }
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                className="tab"
                aria-selected={semanticTab === tab.id}
                onClick={() => setSemanticTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          {semanticTab === "tables" ? <SemanticEditor segment="tables" title="Table dictionary" /> : null}
          {semanticTab === "relationships" ? (
            <SemanticEditor segment="relationships" title="Relationship overrides" />
          ) : null}
          {semanticTab === "dictionary" ? <SemanticEditor segment="dictionary" title="Business terms" /> : null}
          {semanticTab === "metrics" ? <SemanticEditor segment="metrics" title="Metrics" /> : null}
        </section>
      ) : null}

      {mainTab === "ai" ? (
        <section className="stack">
          <div className="card stack" style={{ padding: 22 }}>
            <h2 style={{ marginTop: 0 }}>Routing profile</h2>
            <p style={{ marginTop: 0, color: "var(--text-muted)" }}>
              Choose a task key, tune provider settings, validate, then save. Values stay in the API
              process memory until restart.
            </p>
            <form className="stack" style={{ gap: 0 }} onSubmit={saveProfile}>
              <div className="field">
                <label htmlFor="task">Task</label>
                <select
                  id="task"
                  value={routingForm.task}
                  onChange={(e) => setRoutingForm({ ...routingForm, task: e.target.value })}
                >
                  {AI_TASKS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div className="row" style={{ gap: 16 }}>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="provider">Provider</label>
                  <input
                    id="provider"
                    value={routingForm.provider}
                    onChange={(e) => setRoutingForm({ ...routingForm, provider: e.target.value })}
                    required
                  />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="model">Model</label>
                  <input
                    id="model"
                    value={routingForm.model}
                    onChange={(e) => setRoutingForm({ ...routingForm, model: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="row" style={{ gap: 16 }}>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="temp">Temperature</label>
                  <input
                    id="temp"
                    type="number"
                    step="0.05"
                    value={routingForm.temperature}
                    onChange={(e) => setRoutingForm({ ...routingForm, temperature: Number(e.target.value) })}
                  />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="maxtok">Max tokens</label>
                  <input
                    id="maxtok"
                    type="number"
                    value={routingForm.max_tokens}
                    onChange={(e) => setRoutingForm({ ...routingForm, max_tokens: Number(e.target.value) })}
                  />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="timeout">Timeout (s)</label>
                  <input
                    id="timeout"
                    type="number"
                    value={routingForm.timeout}
                    onChange={(e) => setRoutingForm({ ...routingForm, timeout: Number(e.target.value) })}
                  />
                </div>
                <div className="field" style={{ flex: 1 }}>
                  <label htmlFor="cost">Cost limit</label>
                  <input
                    id="cost"
                    type="number"
                    step="0.1"
                    value={routingForm.cost_limit}
                    onChange={(e) => setRoutingForm({ ...routingForm, cost_limit: Number(e.target.value) })}
                  />
                </div>
              </div>
              {aiError ? (
                <p className="badge badge-danger" role="alert">
                  {aiError}
                </p>
              ) : null}
              {aiMessage ? <p className="badge">{aiMessage}</p> : null}
              <div className="row">
                <button className="btn btn-primary" type="submit" disabled={aiBusy}>
                  Save profile
                </button>
                <button type="button" className="btn btn-ghost" onClick={validateProfile} disabled={aiBusy}>
                  Validate configuration
                </button>
              </div>
            </form>
          </div>

          <div className="card stack" style={{ padding: 22 }}>
            <div className="row-spread">
              <h2 style={{ margin: 0 }}>Active profiles</h2>
              <button type="button" className="btn btn-ghost" onClick={() => loadProfiles()} disabled={aiBusy}>
                Refresh
              </button>
            </div>
            {profileEntries.length === 0 ? (
              <div className="empty">No profiles returned.</div>
            ) : (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Provider</th>
                      <th>Model</th>
                      <th>Temp</th>
                      <th>Max tokens</th>
                    </tr>
                  </thead>
                  <tbody>
                    {profileEntries.map(([task, cfg]) => (
                      <tr key={task}>
                        <td className="mono">{task}</td>
                        <td>{cfg.provider}</td>
                        <td>{cfg.model}</td>
                        <td>{cfg.temperature}</td>
                        <td>{cfg.max_tokens}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      ) : null}
    </main>
  );
}
