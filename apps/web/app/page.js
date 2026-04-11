import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page stack" style={{ maxWidth: 880 }}>
      <header className="stack" style={{ gap: 12 }}>
        <p className="badge" style={{ alignSelf: "flex-start" }}>
          MVP shell → product UI
        </p>
        <h1 style={{ margin: 0, fontSize: "2.1rem" }}>Welcome to Smart BI</h1>
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "1.05rem", maxWidth: 720 }}>
          Connect Oracle, curate the semantic layer, ask questions with evidence (SQL + results), and
          assemble dashboards with AI assistance. Use the top navigation to move through the primary
          journeys.
        </p>
      </header>

      <section className="card" style={{ padding: 22 }}>
        <h2 style={{ marginTop: 0 }}>Where to start</h2>
        <ol style={{ margin: 0, paddingLeft: 20, color: "var(--text-muted)", lineHeight: 1.7 }}>
          <li>
            <Link href="/login">Sign in</Link> — admin usernames begin with{" "}
            <span className="mono">admin</span>.
          </li>
          <li>
            <Link href="/admin">Admin</Link> — connections, semantic metadata, AI routing profiles.
          </li>
          <li>
            <Link href="/ask">Ask Data</Link> — question, answer card, SQL, table, confidence.
          </li>
          <li>
            <Link href="/dashboards">Dashboards</Link> — create from prompt, inspect versions, AI
            edit with preview.
          </li>
        </ol>
      </section>

      <section className="row" style={{ gap: 16, alignItems: "stretch" }}>
        <div className="card stack" style={{ padding: 20, flex: "1 1 240px" }}>
          <h3 style={{ margin: 0 }}>Evidence first</h3>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Answers ship with the SQL and a sample results grid so you can validate before sharing.
          </p>
        </div>
        <div className="card stack" style={{ padding: 20, flex: "1 1 240px" }}>
          <h3 style={{ margin: 0 }}>Progressive disclosure</h3>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            SQL stays tucked away by default; expand when you need the full statement.
          </p>
        </div>
        <div className="card stack" style={{ padding: 20, flex: "1 1 240px" }}>
          <h3 style={{ margin: 0 }}>Admin feedback</h3>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Connection tests and introspection surface inline status so setup never feels blind.
          </p>
        </div>
      </section>
    </main>
  );
}
