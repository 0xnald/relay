import type { AgentRuntimeStatus, Dashboard, DecisionRequest, HeroSummary, NetworkDriver, NetworkRecipient, RescueDetail } from "./types";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, path: string) {
    super(`Relay API returned ${status} for ${path}`);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!response.ok) throw new ApiError(response.status, path);
  return response.json() as Promise<T>;
}

// Every call stays relative to the Next.js /api proxy (see next.config.ts).
export const api = {
  dashboard: () => request<Dashboard>("/api/v1/dashboard"),
  recipients: () => request<NetworkRecipient[]>("/api/v1/network/recipients"),
  drivers: () => request<NetworkDriver[]>("/api/v1/network/drivers"),
  agentStatus: () => request<AgentRuntimeStatus>("/api/v1/system/agent-status"),
  rescue: (id: string) => request<RescueDetail>(`/api/v1/rescues/${id}/command-center`),
  runHero: () => request<HeroSummary>("/api/v1/demo/hero", { method: "POST" }),
  resolveDecision: (id: string, resolution: string) => request<DecisionRequest>(`/api/v1/decisions/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolution, actor_id: "40000000-0000-4000-8000-000000000001" })
  })
};
