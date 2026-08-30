// Relative requests work when FastAPI serves the built UI and when Vite
// proxies the same paths during local development.
const API_URL = import.meta.env.VITE_API_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

export const getDashboard = (persona = "Category Manager") =>
  request(`/api/v1/dashboard?persona=${encodeURIComponent(persona)}`);
export const getNarrative = (id, persona) =>
  request(`/api/v1/alerts/${id}/narrative?persona=${encodeURIComponent(persona)}`);
export const getAlert = (id) =>
  request(`/api/v1/alerts/${id}`);
export const investigateAlert = (id, persona) =>
  request(`/api/v1/alerts/${id}/investigate?persona=${encodeURIComponent(persona)}`);
export const saveDecision = (id, body) =>
  request(`/api/v1/alerts/${id}/decisions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
export const resetDemo = () =>
  request("/api/v1/reset-demo", { method: "POST" });
