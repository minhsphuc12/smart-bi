"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { apiRequest } from "../../lib/api";
import { useAuth } from "../providers";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: { username, password },
        token: null
      });
      login({
        access_token: data.access_token,
        token_type: data.token_type,
        role: data.role,
        username
      });
      router.push("/");
      router.refresh();
    } catch (err) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page" style={{ maxWidth: 480 }}>
      <div className="card stack" style={{ padding: 28 }}>
        <div>
          <h1 style={{ margin: "0 0 8px" }}>Sign in</h1>
          <p style={{ margin: 0, color: "var(--text-muted)" }}>
            Development stub: usernames starting with <span className="mono">admin</span> receive
            the Admin role. No real authentication yet.
          </p>
        </div>
        <form className="stack" onSubmit={onSubmit} style={{ gap: 0 }}>
          <div className="field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          {error ? (
            <p role="alert" className="badge badge-danger" style={{ alignSelf: "flex-start" }}>
              {error}
            </p>
          ) : null}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn btn-primary" type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Continue"}
            </button>
            <Link href="/" className="btn btn-ghost" style={{ textDecoration: "none" }}>
              Cancel
            </Link>
          </div>
        </form>
      </div>
    </main>
  );
}
