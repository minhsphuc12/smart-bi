import Link from "next/link";

export const metadata = {
  title: "Smart BI MVP",
  description: "Smart BI web app"
};

const navLink = {
  marginRight: 20,
  color: "#1a1a1a",
  textDecoration: "none",
  fontWeight: 500
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, Arial, sans-serif", margin: 0 }}>
        <header
          style={{
            borderBottom: "1px solid #e5e5e5",
            padding: "12px 24px",
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8
          }}
        >
          <Link href="/" style={{ ...navLink, fontWeight: 700 }}>
            Smart BI
          </Link>
          <nav style={{ display: "flex", flexWrap: "wrap", alignItems: "center" }}>
            <Link href="/ask" style={navLink}>
              Ask Data
            </Link>
            <Link href="/dashboards" style={navLink}>
              Dashboards
            </Link>
            <Link href="/admin" style={navLink}>
              Admin
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              style={navLink}
            >
              API docs ↗
            </a>
            <a
              href="http://localhost:8000/health"
              target="_blank"
              rel="noopener noreferrer"
              style={navLink}
            >
              Health ↗
            </a>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
