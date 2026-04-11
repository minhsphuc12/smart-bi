export default function AdminPage() {
  return (
    <main style={{ maxWidth: 860, margin: "40px auto", padding: "0 24px" }}>
      <h1>Admin</h1>
      <p style={{ color: "#444", lineHeight: 1.6 }}>
        Oracle connections, semantic layer, and AI routing screens are planned but not built in this
        frontend yet. Use{" "}
        <a href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">
          API docs
        </a>{" "}
        to exercise admin endpoints during development.
      </p>
    </main>
  );
}
