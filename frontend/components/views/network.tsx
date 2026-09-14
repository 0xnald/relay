"use client";

import { Building2, MapPin, Snowflake, Store, Truck, type LucideIcon } from "lucide-react";
import { label } from "../../lib/status";
import type { Dashboard, NetworkDriver, NetworkRecipient } from "../../lib/types";
import { CardSkeleton, cx, EmptyState, ErrorCard, Label, Mono, PageTitle, SectionHeader, StatusBadge } from "../ui";

type Props = { recipients: NetworkRecipient[] | null; drivers: NetworkDriver[] | null; dashboard: Dashboard | null; error: string | null; onRetry: () => void };

function CategoryHeading({ icon: Icon, title, count, description }: { icon: LucideIcon; title: string; count: number; description: string }) {
  return (
    <SectionHeader
      title={title}
      count={count}
      description={description}
      action={<span className="flex h-9 w-9 items-center justify-center rounded-card-sm border border-line bg-surface text-ink-2"><Icon size={16} strokeWidth={1.75} aria-hidden /></span>}
    />
  );
}

export function NetworkView({ recipients, drivers, dashboard, error, onRetry }: Props) {
  // Donors are not a separate endpoint; they are the distinct donors seen on the rescue board.
  const donors = new Map<string, number>();
  for (const rescue of dashboard?.rescues ?? []) donors.set(rescue.donor, (donors.get(rescue.donor) ?? 0) + 1);
  const loading = recipients === null || drivers === null;
  return (
    <div className="space-y-10">
      <PageTitle title="Network" description="Synthetic recipients, drivers, and donors loaded from Relay's deterministic services. Capacity and availability reflect persisted state." />
      {error && <ErrorCard message={error} onRetry={onRetry} />}

      <section>
        <CategoryHeading icon={Store} title="Donors" count={donors.size} description="Organizations that have opened rescues on this board." />
        {donors.size ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[...donors.entries()].map(([name, count]) => (
              <article key={name} className="rounded-card border border-line bg-surface p-5 shadow-card">
                <div className="flex items-start justify-between gap-3"><h3 className="text-md font-semibold text-ink">{name}</h3><Label>Donor</Label></div>
                <p className="mt-2 text-sm text-ink-2"><span className="font-mono text-ink tnum">{count}</span> rescue{count === 1 ? "" : "s"} on the board</p>
              </article>
            ))}
          </div>
        ) : <EmptyState icon={Store} title="No donors yet" body="Donors appear once a rescue has been opened." />}
      </section>

      <section>
        <CategoryHeading icon={Building2} title="Recipients" count={recipients?.length ?? 0} description="Kitchens, shelters, and pantries with declared capacity and handling capability." />
        {loading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CardSkeleton /><CardSkeleton /><CardSkeleton /></div> : recipients?.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {recipients.map((recipient) => {
              const used = recipient.total_capacity ? Math.round(((recipient.total_capacity - recipient.available_capacity) / recipient.total_capacity) * 100) : 0;
              return (
                <article key={recipient.id} className="rounded-card border border-line bg-surface p-5 shadow-card transition-shadow duration-base hover:shadow-card-hover">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0"><h3 className="truncate text-md font-semibold text-ink">{recipient.name}</h3><Label>Recipient</Label></div>
                    <StatusBadge status={recipient.active ? "active" : "inactive"} />
                  </div>
                  <p className="mt-3 text-sm text-ink-2">{recipient.accepted_food_categories.length ? recipient.accepted_food_categories.map(label).join(" · ") : "No declared categories"}</p>
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs"><Label>Capacity</Label><Mono className="tnum">{recipient.available_capacity}/{recipient.total_capacity} free</Mono></div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-elevated"><div className={cx("h-full rounded-full", used > 85 ? "bg-amber" : "bg-mint/70")} style={{ width: `${used}%` }} /></div>
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                    <div><dt><Label>Cold storage</Label></dt><dd className={cx("mt-1 flex items-center gap-1", recipient.cold_storage_available ? "text-mint" : "text-ink-2")}><Snowflake size={12} aria-hidden />{recipient.cold_storage_available ? "Available" : "Ambient only"}</dd></div>
                    <div><dt><Label>Reliability</Label></dt><dd className="mt-1 font-mono text-ink tnum">{Math.round(recipient.reliability * 100)}%</dd></div>
                    {recipient.address && <div className="col-span-2"><dt><Label>Service area</Label></dt><dd className="mt-1 flex items-center gap-1 text-ink-2"><MapPin size={12} aria-hidden />{recipient.address}{recipient.service_radius_km ? ` · ${recipient.service_radius_km} km` : ""}</dd></div>}
                  </dl>
                </article>
              );
            })}
          </div>
        ) : <EmptyState icon={Building2} title="No recipients loaded" body="Recipients are seeded when the hero scenario runs." />}
      </section>

      <section>
        <CategoryHeading icon={Truck} title="Drivers" count={drivers?.length ?? 0} description="Vehicle capability and current availability." />
        {loading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><CardSkeleton /><CardSkeleton /><CardSkeleton /></div> : drivers?.length ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {drivers.map((driver) => (
              <article key={driver.id} className="rounded-card border border-line bg-surface p-5 shadow-card transition-shadow duration-base hover:shadow-card-hover">
                <div className="flex items-start justify-between gap-3">
                  <div><h3 className="text-md font-semibold text-ink">{driver.name}</h3><Label>Driver</Label></div>
                  <StatusBadge status={driver.status} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div><dt><Label>Vehicle</Label></dt><dd className="mt-1 capitalize text-ink">{driver.vehicle_type}</dd></div>
                  <div><dt><Label>Capacity</Label></dt><dd className="mt-1 font-mono text-ink tnum">{driver.vehicle_capacity}</dd></div>
                  <div><dt><Label>Cold chain</Label></dt><dd className={cx("mt-1 flex items-center gap-1", driver.refrigerated_vehicle ? "text-mint" : "text-ink-2")}><Snowflake size={12} aria-hidden />{driver.refrigerated_vehicle ? "Refrigerated" : "Standard"}</dd></div>
                  <div><dt><Label>Reliability</Label></dt><dd className="mt-1 font-mono text-ink tnum">{Math.round(driver.reliability * 100)}%</dd></div>
                </dl>
              </article>
            ))}
          </div>
        ) : <EmptyState icon={Truck} title="No drivers loaded" body="Drivers are seeded when the hero scenario runs." />}
      </section>
    </div>
  );
}
