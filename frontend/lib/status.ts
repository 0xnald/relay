// One status language for the whole command center.
// green: completed / verified / recovered / ready / autonomous success
// amber: human review / needs clarification / awaiting judgment
// neutral: assigned / in progress / pending
// danger: only real failure, cancellation, or error

export type Tone = "green" | "amber" | "neutral" | "danger";

const GREEN = new Set(["completed", "verified", "recovered", "ready", "resolved", "delivered", "accepted", "available", "active"]);
const AMBER = new Set(["human_review", "needs_clarification", "requires_human_review", "pending", "open", "recovering", "exception_detected", "recovery_planning"]);
const DANGER = new Set(["cancelled", "failed", "expired", "unresolved", "declined", "offline", "error"]);

export function toneFor(status: string | null | undefined): Tone {
  const key = (status ?? "").toLowerCase();
  if (GREEN.has(key)) return "green";
  if (AMBER.has(key)) return "amber";
  if (DANGER.has(key)) return "danger";
  return "neutral";
}

export function label(value: string | null | undefined): string {
  if (!value) return "—";
  return value.replaceAll("_", " ").replace(/^\w/, (c) => c.toUpperCase());
}

/** Journey used in the rescue detail. Operational sub-states map onto these stages. */
export const JOURNEY = [
  { key: "received", title: "Received", statuses: ["received", "normalizing"] },
  { key: "policy_check", title: "Policy check", statuses: ["policy_check"] },
  { key: "matching", title: "Matching", statuses: ["matching", "awaiting_recipient"] },
  { key: "assigned", title: "Assigned", statuses: ["assigned", "awaiting_driver"] },
  { key: "dispatched", title: "Dispatched", statuses: ["dispatched", "pickup_pending", "exception_detected", "recovery_planning", "recovered", "human_review", "resolved"] },
  { key: "in_transit", title: "In transit", statuses: ["in_transit", "delivery_pending"] },
  { key: "verification", title: "Verification", statuses: ["verifying"] },
  { key: "completed", title: "Completed", statuses: ["completed"] }
] as const;

export function journeyIndex(status: string): number {
  const index = JOURNEY.findIndex((stage) => (stage.statuses as readonly string[]).includes(status));
  return index === -1 ? 0 : index;
}

export function isTerminalFailure(status: string): boolean {
  return ["cancelled", "expired", "unresolved"].includes(status);
}

/** Timeline event classification used by the Overview, Activity, and detail timelines. */
export type EventCategory = "autonomous" | "human" | "exception" | "verification" | "state";

const AUTONOMOUS = new Set(["substitute_recipient", "search_replacement_driver", "recovery_started", "recovery_completed", "process_recovery_started", "process_recovery_completed", "recipient_recovery_resumed", "driver_recovery_resumed", "process_recipient_recovery_resumed", "process_driver_recovery_resumed", "workflow_resumed", "process_workflow_resumed"]);
const HUMAN = new Set(["missing_information", "process_missing_information", "human_decision_received", "process_human_decision_received"]);
const EXCEPTION = new Set(["recipient_capability_lost", "process_recipient_capability_lost", "driver_cancelled", "process_driver_cancelled", "recipient_declined", "driver_delayed"]);
const VERIFICATION = new Set(["pickup_confirmed", "process_pickup_confirmed", "delivery_confirmed", "process_delivery_confirmed"]);

export function categorize(kind: string): EventCategory {
  if (HUMAN.has(kind)) return "human";
  if (AUTONOMOUS.has(kind)) return "autonomous";
  if (EXCEPTION.has(kind)) return "exception";
  if (VERIFICATION.has(kind)) return "verification";
  return "state";
}

export function describeEvent(kind: string, detail: Record<string, unknown>): string {
  if (typeof detail.summary === "string") return detail.summary;
  if (typeof detail.step === "string") return `Advanced to ${label(detail.step)}`;
  if (typeof detail.resolution === "string") return `Resolution: ${detail.resolution}`;
  if (typeof detail.capability === "string") return `Lost capability: ${label(detail.capability)}`;
  const entries = Object.entries(detail).filter(([key, value]) => typeof value !== "object" && !key.endsWith("_id") && key !== "outcome");
  if (!entries.length) return label(kind);
  return entries.map(([key, value]) => `${label(key)}: ${String(value)}`).join(" · ");
}

export function humanizeExceptionType(type: string): string {
  const map: Record<string, string> = {
    recipient_storage_loss: "Refrigerator failure",
    recipient_capacity_loss: "Recipient capacity lost",
    recipient_declined: "Recipient declined",
    recipient_timeout: "Recipient timed out",
    driver_cancelled: "Driver cancellation",
    driver_delayed: "Driver delayed",
    pickup_window_changed: "Pickup window changed",
    missing_required_information: "Missing required evidence",
    delivery_mismatch: "Delivery mismatch",
    no_eligible_recipient: "No eligible recipient",
    no_feasible_driver: "No feasible driver"
  };
  return map[type] ?? label(type);
}

export function humanizeStrategy(strategy: string): string {
  const map: Record<string, string> = {
    rematch_affected_allocation: "Re-matched the affected allocation",
    replace_driver: "Replaced the driver",
    try_next_recipient: "Tried the next eligible recipient",
    request_human_review: "Requested human review"
  };
  return map[strategy] ?? label(strategy);
}
