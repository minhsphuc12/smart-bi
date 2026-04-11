const sections = [
  "Admin: Oracle connection and semantic layer",
  "Ask Data: answer + SQL + result table",
  "Dashboard: create and edit with AI",
  "AI Routing: multiple providers/models by task"
];

export default function HomePage() {
  return (
    <main style={{ maxWidth: 860, margin: "40px auto", padding: "0 16px" }}>
      <h1>Smart BI MVP</h1>
      <p>Next.js frontend is ready. Backend service should run at <code>http://localhost:8000</code>.</p>
      <ul>
        {sections.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </main>
  );
}
