from enum import StrEnum


class RescueStatus(StrEnum):
    RECEIVED = "received"
    NORMALIZING = "normalizing"
    POLICY_CHECK = "policy_check"
    MATCHING = "matching"
    AWAITING_RECIPIENT = "awaiting_recipient"
    ASSIGNED = "assigned"
    AWAITING_DRIVER = "awaiting_driver"
    DISPATCHED = "dispatched"
    PICKUP_PENDING = "pickup_pending"
    IN_TRANSIT = "in_transit"
    DELIVERY_PENDING = "delivery_pending"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    EXCEPTION_DETECTED = "exception_detected"
    RECOVERY_PLANNING = "recovery_planning"
    RECOVERED = "recovered"
    HUMAN_REVIEW = "human_review"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNRESOLVED = "unresolved"


class EventType(StrEnum):
    DONATION_CREATED = "donation_created"
    DONATION_UPDATED = "donation_updated"
    RECIPIENT_ACCEPTED = "recipient_accepted"
    RECIPIENT_DECLINED = "recipient_declined"
    RECIPIENT_CAPACITY_CHANGED = "recipient_capacity_changed"
    RECIPIENT_TIMEOUT = "recipient_timeout"
    DRIVER_ACCEPTED = "driver_accepted"
    DRIVER_DECLINED = "driver_declined"
    DRIVER_CANCELLED = "driver_cancelled"
    DRIVER_DELAYED = "driver_delayed"
    PICKUP_CONFIRMED = "pickup_confirmed"
    PICKUP_WINDOW_CHANGED = "pickup_window_changed"
    DELIVERY_CONFIRMED = "delivery_confirmed"
    DELIVERY_MISMATCH = "delivery_mismatch"
    EVIDENCE_RECEIVED = "evidence_received"
    POLICY_VIOLATION = "policy_violation"
    MISSING_INFORMATION = "missing_information"
    HUMAN_DECISION_RECEIVED = "human_decision_received"


class DecisionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DecisionSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionAuthority(StrEnum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class EvidenceType(StrEnum):
    PHOTO = "photo"
    SIGNATURE = "signature"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"
    LOCATION = "location"
    DOCUMENT = "document"
    ATTESTATION = "attestation"


class ActorRole(StrEnum):
    SYSTEM = "system"
    AGENT = "agent"
    ADMIN = "admin"
    DONOR = "donor"
    RECIPIENT = "recipient"
    DRIVER = "driver"


class OrganizationType(StrEnum):
    DONOR = "donor"
    RECIPIENT = "recipient"
    LOGISTICS = "logistics"
    COORDINATOR = "coordinator"


class ActionType(StrEnum):
    SEARCH_ALTERNATE_RECIPIENT = "search_alternate_recipient"
    SEARCH_REPLACEMENT_DRIVER = "search_replacement_driver"
    SEND_STATUS_UPDATE = "send_status_update"
    REQUEST_OPERATIONAL_INFORMATION = "request_operational_information"
    SUBSTITUTE_RECIPIENT = "substitute_recipient"
    SPLIT_RESCUE = "split_rescue"
    EXTEND_PICKUP_WINDOW = "extend_pickup_window"
    CHANGE_ASSIGNED_DRIVER = "change_assigned_driver"
    REQUEST_CLARIFICATION = "request_clarification"
    OVERRIDE_HANDLING_REQUIREMENT = "override_handling_requirement"
    CONTINUE_WITH_MISSING_EVIDENCE = "continue_with_missing_evidence"
    RESOLVE_POLICY_CONFLICT = "resolve_policy_conflict"
    OVERRIDE_ELIGIBILITY = "override_eligibility"
    CONTINUE_POTENTIALLY_UNSAFE = "continue_potentially_unsafe"
    HIGH_IMPACT_MANUAL_OVERRIDE = "high_impact_manual_override"


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBHOOK = "webhook"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
