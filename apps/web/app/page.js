const sections = [
  "Admin: Oracle connection and semantic layer",
  "Ask Data: answer + SQL + result table",
  "Dashboard: create and edit with AI",
  "AI Routing: multiple providers/models by task"
];

export default function HomePage() {
  return (
    <main style={{ maxWidth: 860, margin: "40px auto", padding: "0 24px" }}>
      <h1>Smart BI MVP</h1>
      <p style={{ lineHeight: 1.6 }}>
        This repository currently ships a <strong>thin Next.js shell</strong>: navigation and placeholder
        pages. The product UI (forms, chat, dashboards) still needs to be implemented per the UX
        roadmap in <code>docs/02-ux-roadmap.md</code>.
      </p>
      <p style={{ lineHeight: 1.6 }}>
        Start the API on port <code>8000</code> (see README), then use the top bar: in-app sections
        are stubs; <strong>API docs</strong> and <strong>Health</strong> open the running FastAPI
        service.
      </p>
      <h2 style={{ fontSize: "1.1rem", marginTop: 28 }}>MVP scope (from docs)</h2>
      <ul style={{ lineHeight: 1.7 }}>
        {sections.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </main>
  );
}
