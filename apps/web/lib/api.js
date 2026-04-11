const STORAGE_KEY = "smartbi_session";

/**
 * API base URL for browser fetch.
 * - If NEXT_PUBLIC_API_URL is set (e.g. production or Playwright), use it.
 * - Otherwise use same-origin /api-proxy (see next.config.js rewrites → FastAPI) to avoid CORS and
 *   mismatches between localhost vs 127.0.0.1.
 */
export function getApiBase() {
  const fromEnv =
    typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
      ? String(process.env.NEXT_PUBLIC_API_URL).replace(/\/$/, "")
      : "";
  return fromEnv || "/api-proxy";
}

export function getStoredSession() {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(session) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredSession() {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * @param {string} path
 * @param {{ method?: string, body?: unknown, token?: string | null }} [options]
 */
export async function apiRequest(path, options = {}) {
  const { method = "GET", body, token } = options;
  const headers = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  const authToken = token === null ? null : token ?? getStoredSession()?.access_token;
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }
  let res;
  try {
    res = await fetch(`${getApiBase()}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body)
    });
  } catch (e) {
    const isNetwork =
      e instanceof TypeError &&
      (String(e.message).includes("fetch") || String(e.message).includes("Failed to fetch"));
    if (isNetwork) {
      throw new Error(
        "Could not reach the API. From apps/api run: uvicorn app.main:app --reload --port 8000. " +
          "If the API uses another host/port, set SMART_BI_API_ORIGIN for Next rewrites or NEXT_PUBLIC_API_URL for direct calls."
      );
    }
    throw e;
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) {
    const detail =
      typeof data === "object" && data !== null && "detail" in data ? data.detail : data;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => (typeof d === "object" ? d.msg : String(d))).join("; ")
          : res.statusText;
    const err = new Error(message || "Request failed");
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}
