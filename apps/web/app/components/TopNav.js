"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { getApiBase } from "../../lib/api";
import { useAuth } from "../providers";

const linkBase = {
  textDecoration: "none",
  fontWeight: 600,
  color: "var(--text)",
  padding: "6px 10px",
  borderRadius: 8
};

export function TopNav() {
  const pathname = usePathname();
  const { session, ready, isAdmin, logout } = useAuth();
  const apiBase = getApiBase();

  const active = (href) =>
    pathname === href || (href !== "/" && pathname?.startsWith(href))
      ? { ...linkBase, background: "var(--accent-soft)", color: "var(--accent-hover)" }
      : linkBase;

  return (
    <header
      style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
        position: "sticky",
        top: 0,
        zIndex: 20
      }}
    >
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          padding: "12px 20px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12
        }}
      >
        <Link href="/" style={{ ...linkBase, fontWeight: 800, fontFamily: "var(--font-display)" }}>
          Smart BI
        </Link>
        <nav style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 4, flex: 1 }}>
          <Link href="/ask" style={active("/ask")}>
            Ask Data
          </Link>
          <Link href="/dashboards" style={active("/dashboards")}>
            Dashboards
          </Link>
          {ready && isAdmin ? (
            <Link href="/admin" style={active("/admin")}>
              Admin
            </Link>
          ) : null}
          <a href={`${apiBase}/docs`} target="_blank" rel="noopener noreferrer" style={linkBase}>
            API docs ↗
          </a>
          <a href={`${apiBase}/health`} target="_blank" rel="noopener noreferrer" style={linkBase}>
            Health ↗
          </a>
        </nav>
        <div className="row" style={{ gap: 10 }}>
          {ready && session ? (
            <>
              <span className="badge" title="Dev stub session">
                {session.role === "admin" ? "Admin" : "User"}
              </span>
              <button type="button" className="btn btn-ghost" onClick={() => logout()}>
                Sign out
              </button>
            </>
          ) : ready ? (
            <Link href="/login" className="btn btn-primary" style={{ textDecoration: "none" }}>
              Sign in
            </Link>
          ) : null}
        </div>
      </div>
    </header>
  );
}
