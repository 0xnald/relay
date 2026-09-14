export type Rescue = {
  id: string;
  short_code: string;
  status: string;
  donor: string;
  pickup_deadline: string;
  food_summary: string;
  food_quantity?: number;
  recipients: string[];
  drivers: string[];
  exception_count: number;
  progress: number;
  updated_at: string;
};

export type DecisionRequest = {
  id: string;
  created_at: string;
  updated_at?: string;
  rescue_id: string;
  exception_id?: string | null;
  issue: string;
  known_evidence: string[];
  missing_evidence: string[];
  actions_tried: string[];
  allowed_options: string[];
  status: string;
  requested_at?: string;
  resolved_at?: string | null;
  resolution?: string | null;
  trace_id?: string | null;
};

export type Dashboard = {
  demo: boolean;
  metrics: Record<string, number>;
  rescues: Rescue[];
  decisions: DecisionRequest[];
};

export type FoodItem = { name: string; quantity: string; unit: string; requires_refrigeration: boolean; handling_category: string };
export type Allocation = { id: string; recipient: string; quantity: string; unit: string; status: string };
export type Assignment = { id: string; driver: string; status: string; created_at: string };
export type OperationalException = {
  id: string;
  exception_type: string;
  status: string;
  severity: string;
  detected_at?: string;
  context?: Record<string, unknown>;
};
export type Recovery = { id?: string; exception_id?: string; strategy: string; succeeded: boolean; outcome_summary: string; created_at?: string };
export type TimelineEvent = { kind: string; at: string; actor: string; detail: Record<string, unknown>; trace_id: string };

export type RescueDetail = {
  rescue: Rescue;
  donor: string;
  trace_id: string | null;
  food_items: FoodItem[];
  allocations: Allocation[];
  assignments: Assignment[];
  exceptions: OperationalException[];
  recoveries: Recovery[];
  decisions: DecisionRequest[];
  timeline: TimelineEvent[];
  route: { source: string; pickup_feasible: boolean };
  receipt: { verified: boolean; completed_at: string | null };
};

export type NetworkRecipient = {
  id: string;
  name: string;
  active: boolean;
  address?: string | null;
  service_radius_km?: number | null;
  accepted_food_categories: string[];
  cold_storage_available: boolean;
  freezer_available?: boolean;
  total_capacity: number;
  available_capacity: number;
  reliability: number;
  synthetic: boolean;
};

export type NetworkDriver = {
  id: string;
  name: string;
  available: boolean;
  vehicle_type: string;
  vehicle_capacity: number;
  refrigerated_vehicle: boolean;
  reliability: number;
  status: string;
  synthetic: boolean;
};

export type AgentRuntimeStatus = { execution_mode: string; provider: string; runtime_configured: boolean; runtime_verified: boolean; region: string };

/** Response of POST /api/v1/demo/hero (HeroScenarioSummary). */
export type HeroSummary = {
  rescue_id: string;
  donation_id: string;
  final_rescue_status: string;
  allocations: Array<Record<string, string>>;
  recipient_changes: string[];
  driver_changes: string[];
  exceptions: string[];
  recoveries: string[];
  human_decisions: string[];
  autonomous_actions: string[];
  trace_ids: string[];
  delivery_verified: boolean;
};
