import type { Dashboard, RescueDetail } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new Error(`Relay API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export const api = {
  dashboard: () => request<Dashboard>("/api/v1/dashboard"),
  rescue: (id: string) => request<RescueDetail>(`/api/v1/rescues/${id}/command-center`),
  runHero: () => request<{ rescue_id: string }>("/api/v1/demo/hero", { method: "POST" }),
  resolveDecision: (id: string, resolution: string) => request(`/api/v1/decisions/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolution, actor_id: "40000000-0000-4000-8000-000000000001" })
  })
};
