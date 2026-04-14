/**
 * Smoke test against an already-running stack (Next on :3000, API on :8000, api-proxy).
 * Run from repo root: node apps/web/scripts/browser-smoke-reuse-dev.js
 * Set HEADED=1 to open a visible Chromium window (local machine with display).
 */
const path = require("path");
const { chromium } = require("playwright-core");

const WEB = process.env.SMOKE_WEB_URL || "http://127.0.0.1:3000";
const headed = process.env.HEADED === "1";

async function main() {
  const browser = await chromium.launch({ headless: !headed, slowMo: headed ? 120 : 0 });
  const page = await browser.newPage();
  const out = [];

  try {
    // Same shape as `lib/api.js` after successful `/auth/login` (avoids flaky SPA redirect in automation).
    await page.addInitScript(() => {
      localStorage.setItem(
        "smartbi_session",
        JSON.stringify({
          access_token: "dev-token",
          token_type: "bearer",
          role: "admin",
          username: "admin"
        })
      );
    });

    await page.goto(`${WEB}/admin`, { waitUntil: "domcontentloaded", timeout: 30_000 });
    await page.getByRole("heading", { name: /Admin console/i }).waitFor({ timeout: 15_000 });
    out.push("admin page OK");

    await page.getByRole("tablist", { name: "Admin sections" }).getByRole("tab", { name: "Semantic layer" }).click();
    await page.getByRole("heading", { name: "Table dictionary" }).waitFor({ timeout: 10_000 });
    out.push("semantic tables OK");

    await page.getByRole("tablist", { name: "Semantic editors" }).getByRole("tab", { name: "Semantic Repo" }).click();
    await page.getByRole("heading", { name: "Semantic Repo (read-only)" }).waitFor({ timeout: 15_000 });
    out.push("semantic repo (mart yaml) tab OK");

    const martApi = await page.evaluate(async () => {
      const r = await fetch("/api-proxy/admin/semantic/mart/files", { headers: { Accept: "application/json" } });
      const j = await r.json().catch(() => ({}));
      return { status: r.status, exists: j.exists, nfiles: Array.isArray(j.files) ? j.files.length : -1 };
    });
    if (martApi.status !== 200) throw new Error(`mart/files HTTP ${martApi.status}`);
    out.push(`mart/files JSON: exists=${martApi.exists} files=${martApi.nfiles}`);

    await page.goto(`${WEB}/ask`, { waitUntil: "domcontentloaded", timeout: 30_000 });
    await page.getByRole("heading", { name: "Ask Data" }).waitFor({ timeout: 15_000 });
    out.push("ask data page OK");

    await page.goto(`${WEB}/dashboards`, { waitUntil: "domcontentloaded", timeout: 30_000 });
    await page.getByRole("heading", { name: "Dashboards" }).waitFor({ timeout: 15_000 });
    out.push("dashboards list OK");

    const shot = path.join(__dirname, "..", "e2e", "smoke-reuse-dev.png");
    await page.screenshot({ path: shot, fullPage: true });
    out.push(`screenshot: ${shot}`);
  } finally {
    await browser.close();
  }

  console.log(out.join("\n"));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
