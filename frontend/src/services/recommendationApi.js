// Centralised access to the RecomAI FastAPI backend.
// This is the ONLY file that knows where the backend lives.

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");

const REQUEST_TIMEOUT_MS =
  Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS) || 300000;

/**
 * Error with a `kind` the UI can react to:
 *  network | timeout | not_found | validation | unavailable | server
 */
export class ApiError extends Error {
  constructor(message, { kind = "server", status = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

function kindForStatus(status) {
  if (status === 404) return "not_found";
  if (status === 422 || status === 400) return "validation";
  if (status === 503) return "unavailable";
  return "server";
}

function describeDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((d) => d && d.msg).filter(Boolean);
    if (messages.length) return messages.join("; ");
  }
  return null;
}

async function request(path, { params, signal, timeoutMs = REQUEST_TIMEOUT_MS } = {}) {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });

  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const forwardAbort = () => controller.abort();
  if (signal) {
    if (signal.aborted) controller.abort();
    else signal.addEventListener("abort", forwardAbort, { once: true });
  }

  try {
    let response;
    try {
      response = await fetch(url, {
        signal: controller.signal,
        headers: { Accept: "application/json" },
      });
    } catch (error) {
      if (error.name === "AbortError") {
        if (timedOut) {
          throw new ApiError(
            "The request took too long. The server may still be loading its models - please try again in a moment.",
            { kind: "timeout" }
          );
        }
        throw error; // cancelled by the caller; callers ignore AbortError
      }
      throw new ApiError(
        `Cannot reach the RecomAI API at ${API_BASE_URL}. Make sure the backend is running.`,
        { kind: "network" }
      );
    }

    let body = null;
    try {
      body = await response.json();
    } catch {
      /* non-JSON body */
    }

    if (!response.ok) {
      const message =
        describeDetail(body && body.detail) ||
        `The server returned an error (HTTP ${response.status}).`;
      throw new ApiError(message, {
        kind: kindForStatus(response.status),
        status: response.status,
      });
    }
    return body;
  } finally {
    clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", forwardAbort);
  }
}

export function checkHealth(signal) {
  return request("/api/health", { signal, timeoutMs: 5000 });
}

export function searchItems(domain, query, { limit = 8, signal } = {}) {
  return request(`/api/${domain}/search`, {
    params: { q: query, limit },
    signal,
    timeoutMs: 60000,
  });
}

export function getRecommendations(
  domain,
  { itemId, method = "hybrid", topN = 12, signal } = {}
) {
  return request(`/api/${domain}/recommendations`, {
    params: { item_id: itemId, method, top_n: topN },
    signal,
  });
}
