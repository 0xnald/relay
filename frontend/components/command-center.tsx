"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, ApiError } from "../lib/api";
import type { AgentRuntimeStatus, Dashboard, HeroSummary, NetworkDriver, NetworkRecipient, Rescue, RescueDetail } from "../lib/types";
import { AppShell, type View } from "./app-shell";
import { ErrorCard } from "./ui";
import { ActivityView } from "./views/activity";
import { DecisionsView } from "./views/decisions";
import { DemoView } from "./views/demo";
import { NetworkView } from "./views/network";
import { OverviewView } from "./views/overview";
import { PoliciesView } from "./views/policies";
import { RescueDetailView } from "./views/rescue-detail";
import { RescuesView } from "./views/rescues";

const POLL_MS = 3000;
const STALE_MS = 15_000;
const ACTIVITY_RESCUES = 5;

function describe(error: unknown): string {
  if (error instanceof ApiError) return `The Relay API responded with HTTP ${error.status}.`;
  if (error instanceof TypeError) return "The Relay API could not be reached.";
  return "Unexpected error while talking to the Relay API.";
}

export function CommandCenter({ initialView = "Overview" }: { initialView?: View }) {
  const [view, setView] = useState<View>(initialView);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [runtime, setRuntime] = useState<AgentRuntimeStatus | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [now, setNow] = useState(() => Date.now());

  const [detail, setDetail] = useState<RescueDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, RescueDetail>>({});
  const [detailsError, setDetailsError] = useState<string | null>(null);

  const [recipients, setRecipients] = useState<NetworkRecipient[] | null>(null);
  const [drivers, setDrivers] = useState<NetworkDriver[] | null>(null);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const [heroBusy, setHeroBusy] = useState(false);
  const [heroResult, setHeroResult] = useState<HeroSummary | null>(null);
  const [heroError, setHeroError] = useState<string | null>(null);
  const inflight = useRef(false);

  /* Dashboard + runtime status: the same two calls as before, polled every 3 s. */
  const load = useCallback(async () => {
    if (inflight.current) return;
    inflight.current = true;
    setRefreshing(true);
    try {
      const [nextDashboard, nextRuntime] = await Promise.all([api.dashboard(), api.agentStatus()]);
      setDashboard(nextDashboard);
      setRuntime(nextRuntime);
      setLoadError(null);
      setLastRefresh(Date.now());
    } catch (error) {
      setLoadError(describe(error));
    } finally {
      inflight.current = false;
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => { void load(); }, 0);
    return () => window.clearTimeout(timer);
  }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => { void load(); }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 10_000);
    return () => window.clearInterval(timer);
  }, []);

  /* Network lists: existing endpoints, loaded once and refreshed when a run finishes. */
  const loadNetwork = useCallback(async () => {
    try {
      const [nextRecipients, nextDrivers] = await Promise.all([api.recipients(), api.drivers()]);
      setRecipients(nextRecipients);
      setDrivers(nextDrivers);
      setNetworkError(null);
    } catch (error) {
      setNetworkError(describe(error));
    }
  }, []);
  useEffect(() => {
    const timer = window.setTimeout(() => { void loadNetwork(); }, 0);
    return () => window.clearTimeout(timer);
  }, [loadNetwork]);

  const resolveName = useCallback((id: string): string | undefined => {
    return recipients?.find((item) => item.id === id)?.name ?? drivers?.find((item) => item.id === id)?.name;
  }, [recipients, drivers]);

  /* Rescue detail (command-center endpoint). */
  const open = useCallback(async (target: Rescue | string) => {
    const id = typeof target === "string" ? target : target.id;
    setDetailLoading(true);
    setDetailError(null);
    setView("Rescues");
    window.scrollTo({ top: 0 });
    try {
      const next = await api.rescue(id);
      setDetail(next);
      setDetails((previous) => ({ ...previous, [id]: next }));
    } catch (error) {
      setDetailError(describe(error));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  /* Details cache for Overview (latest rescue) and Activity (recent rescues); refetched only when
     a rescue's updated_at changes so polling stays cheap. */
  const wanted = useMemo(() => {
    const rescues = dashboard?.rescues ?? [];
    if (view === "Activity") return rescues.slice(0, ACTIVITY_RESCUES);
    if (view === "Overview") return rescues.slice(0, 1);
    return [];
  }, [dashboard, view]);
  useEffect(() => {
    const missing = wanted.filter((rescue) => details[rescue.id]?.rescue.updated_at !== rescue.updated_at);
    if (!missing.length) return;
    let cancelled = false;
    void Promise.all(missing.map(async (rescue) => [rescue.id, await api.rescue(rescue.id)] as const))
      .then((entries) => { if (!cancelled) { setDetails((previous) => ({ ...previous, ...Object.fromEntries(entries) })); setDetailsError(null); } })
      .catch((error: unknown) => { if (!cancelled) setDetailsError(describe(error)); });
    return () => { cancelled = true; };
  }, [wanted, details]);

  const runHero = useCallback(async () => {
    setHeroBusy(true);
    setHeroError(null);
    setView("Demo");
    try {
      const result = await api.runHero();
      setHeroResult(result);
      await Promise.all([load(), loadNetwork()]);
      await open(result.rescue_id);
    } catch (error) {
      setHeroError(describe(error));
    } finally {
      setHeroBusy(false);
    }
  }, [load, loadNetwork, open]);

  const resolveDecision = useCallback(async (id: string, option: string) => {
    await api.resolveDecision(id, option);
    await load();
    if (detail) await open(detail.rescue.id);
  }, [detail, load, open]);

  const navigate = useCallback((next: View) => { setDetail(null); setDetailError(null); setView(next); window.scrollTo({ top: 0 }); }, []);

  const stale = lastRefresh !== null && now - lastRefresh > STALE_MS;
  const online = loadError === null;
  const latest = dashboard?.rescues[0];
  const latestDetail = latest ? details[latest.id] ?? null : null;

  let content: ReactNode;
  if (detail || detailLoading || detailError) {
    content = detailError
      ? <ErrorCard title="Unable to load rescue details" message={detailError} onRetry={() => detail && void open(detail.rescue.id)} />
      : <RescueDetailView detail={detail} loading={detailLoading} onBack={() => navigate("Rescues")} resolveName={resolveName} onResolveDecision={resolveDecision} now={now} />;
  } else if (view === "Overview") {
    content = <OverviewView dashboard={dashboard} loading={!dashboard && !loadError} online={online} runtime={runtime} latestDetail={latestDetail} latestLoading={Boolean(latest) && !latestDetail} now={now} onOpen={open} onRunDemo={runHero} onViewAll={() => navigate("Rescues")} onViewDecisions={() => navigate("Decisions")} demoBusy={heroBusy} />;
  } else if (view === "Rescues") {
    content = <RescuesView dashboard={dashboard} loading={!dashboard && !loadError} now={now} onOpen={open} />;
  } else if (view === "Network") {
    content = <NetworkView recipients={recipients} drivers={drivers} dashboard={dashboard} error={networkError} onRetry={loadNetwork} />;
  } else if (view === "Decisions") {
    content = <DecisionsView dashboard={dashboard} loading={!dashboard && !loadError} now={now} onResolve={resolveDecision} onOpenRescue={open} />;
  } else if (view === "Activity") {
    content = <ActivityView dashboard={dashboard} details={details} loading={wanted.some((rescue) => !details[rescue.id])} error={detailsError} onRetry={() => setDetails({})} onOpenRescue={open} />;
  } else if (view === "Policies") {
    content = <PoliciesView />;
  } else {
    content = <DemoView busy={heroBusy} result={heroResult} error={heroError} onRun={runHero} onOpenRescue={open} resolveName={resolveName} />;
  }

  return (
    <AppShell view={view} section={detail ? `Rescue ${detail.rescue.short_code}` : undefined} onNavigate={navigate} runtime={runtime} demo={dashboard?.demo ?? true} lastRefresh={lastRefresh} stale={stale} online={online} refreshing={refreshing} onRefresh={() => void load()}>
      {loadError && <div className="mb-6"><ErrorCard message={`${loadError} Polling continues every ${POLL_MS / 1000} s.`} onRetry={() => void load()} offline={!lastRefresh} /></div>}
      {content}
    </AppShell>
  );
}
