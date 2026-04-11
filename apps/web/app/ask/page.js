export default function AskDataPage() {
  return (
    <main style={{ maxWidth: 860, margin: "40px auto", padding: "0 24px" }}>
      <h1>Ask Data</h1>
      <p style={{ color: "#444", lineHeight: 1.6 }}>
        The chat workspace and answer cards (SQL + table) are not implemented in the web app yet. You
        can try the HTTP API from{" "}
        <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
          Swagger UI
        </a>{" "}
        while the UI is under construction.
      </p>
    </main>
  );
}
