export type Rescue = {
  id: string;
  short_code: string;
  status: string;
  donor: string;
  pickup_deadline: string;
  food_summary: string;
  recipients: string[];
  drivers: string[];
  exception_count: number;
  progress: number;
  updated_at: string;
};

export type Dashboard = {
  demo: boolean;
  metrics: Record<string, number>;
  rescues: Rescue[];
  decisions: Array<Record<string, unknown>>;
};

export type RescueDetail = {
  rescue: Rescue;
  donor: string;
  trace_id: string | null;
  food_items: Array<{ name: string; quantity: string; unit: string; requires_refrigeration: boolean; handling_category: string }>;
  allocations: Array<{ id: string; recipient: string; quantity: string; unit: string; status: string }>;
  assignments: Array<{ id: string; driver: string; status: string; created_at: string }>;
  exceptions: Array<{ exception_type: string; status: string; severity: string }>;
  recoveries: Array<{ strategy: string; succeeded: boolean; outcome_summary: string }>;
  decisions: Array<{ id: string; issue: string; status: string; allowed_options: string[] }>;
  timeline: Array<{ kind: string; at: string; actor: string; detail: Record<string, unknown>; trace_id: string }>;
  route: { source: string; pickup_feasible: boolean };
  receipt: { verified: boolean; completed_at: string | null };
};
