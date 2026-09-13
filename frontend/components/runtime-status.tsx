"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { AgentRuntimeStatus } from "../lib/types";

export function runtimeLabel(status: AgentRuntimeStatus | null): string {
  if (status?.runtime_verified) return "Verified";
  if (status?.runtime_configured) return "AgentCore configured — pending verification";
  return "Local";
}

export function RuntimeStatus() {
  const [status, setStatus] = useState<AgentRuntimeStatus | null>(null);
  useEffect(() => { void api.agentStatus().then(setStatus).catch(() => undefined); }, []);
  return <p className="text-xs text-slate-500">Agent runtime: <b className="text-slate-700">{runtimeLabel(status)}</b></p>;
}
