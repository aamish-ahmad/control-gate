"""Frozen V1 contract objects for governed supplier-invoice execution."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from collections.abc import Iterator, Mapping
from types import MappingProxyType
from typing import Annotated, TypeAlias, cast

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PlainSerializer,
    model_validator,
)


NonEmptyString = Annotated[str, Field(min_length=1)]
PositiveVersion = Annotated[int, Field(ge=1)]


class FrozenMapping(Mapping[str, object]):
    """Recursively read-only mapping with stable equality and deepcopy."""

    __slots__ = ("_data",)

    def __init__(self, data: Mapping[str, object]) -> None:
        self._data = MappingProxyType(dict(data))

    def __getitem__(self, key: str) -> object:
        return self._data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __deepcopy__(self, memo: dict[int, object]) -> FrozenMapping:
        return self

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Mapping):
            return dict(self.items()) == dict(other.items())
        return NotImplemented

    def __repr__(self) -> str:
        return f"FrozenMapping({dict(self.items())!r})"


def _freeze_json(value: object) -> object:
    if isinstance(value, FrozenMapping):
        return value
    if isinstance(value, Mapping):
        return FrozenMapping(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _freeze_json_object(
    value: Mapping[str, JsonValue],
) -> Mapping[str, JsonValue]:
    return cast(Mapping[str, JsonValue], _freeze_json(value))


def _serialize_json_object(
    value: Mapping[str, JsonValue],
) -> dict[str, JsonValue]:
    return cast(dict[str, JsonValue], _thaw_json(value))


FrozenJsonObject: TypeAlias = Annotated[
    Mapping[str, JsonValue],
    AfterValidator(_freeze_json_object),
    PlainSerializer(_serialize_json_object, return_type=dict[str, JsonValue]),
]


class StrictModel(BaseModel):
    """Base for contracts that reject fields outside the frozen schema."""

    model_config = ConfigDict(extra="forbid")


class FrozenModel(StrictModel):
    """Base for immutable contract records."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class Decision(str, Enum):
    """The complete public pre-execution admissibility alphabet."""

    APPROVE = "APPROVE"
    CLARIFY = "CLARIFY"
    ESCALATE = "ESCALATE"
    REJECT = "REJECT"


class RunState(str, Enum):
    """States permitted by the frozen V1 runtime contract."""

    CREATED = "CREATED"
    COMPILING = "COMPILING"
    VALIDATING = "VALIDATING"
    AWAITING_DECISION = "AWAITING_DECISION"
    APPROVED = "APPROVED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    ESCALATION_REQUIRED = "ESCALATION_REQUIRED"
    PLANNED = "PLANNED"
    RUNNING = "RUNNING"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EventType(str, Enum):
    """Required event types for a V1 structured trajectory."""

    REQUEST_RECEIVED = "request_received"
    INTENT_COMPILED = "intent_compiled"
    VALIDATION_COMPLETED = "validation_completed"
    CONTROL_DECISION = "control_decision"
    PLAN_CREATED = "plan_created"
    RUN_STARTED = "run_started"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_FAILED = "tool_call_failed"
    RETRY_SCHEDULED = "retry_scheduled"
    RUNTIME_POLICY_CHECK = "runtime_policy_check"
    HUMAN_APPROVAL_REQUESTED = "human_approval_requested"
    HUMAN_INTERVENTION = "human_intervention"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class HumanAction(str, Enum):
    """Human actions supported by the frozen V1 approval path."""

    APPROVE = "APPROVE"
    DENY = "DENY"
    MODIFY_CONSTRAINT = "MODIFY_CONSTRAINT"
    CANCEL = "CANCEL"


class Goal(FrozenModel):
    """Typed goal within an IntentSpec."""

    type: NonEmptyString


class IntentActor(FrozenModel):
    """Actor requesting or operating under the intent."""

    id: NonEmptyString
    role: NonEmptyString


class Permissions(FrozenModel):
    """Business tools the intent permits the runtime to propose."""

    allowed_tools: tuple[NonEmptyString, ...]


class ApprovalRule(FrozenModel):
    """Condition under which a named approver is required."""

    when: NonEmptyString
    require: NonEmptyString


class IntentSpec(FrozenModel):
    """Versioned V1 execution contract compiled from a source request."""

    intent_id: NonEmptyString
    version: PositiveVersion
    source_request: NonEmptyString
    goal: Goal
    actor: IntentActor
    inputs: FrozenJsonObject
    assumptions: tuple[NonEmptyString, ...]
    requirements: tuple[NonEmptyString, ...]
    constraints: FrozenJsonObject
    permissions: Permissions
    prohibited_actions: tuple[NonEmptyString, ...]
    approval_rules: tuple[ApprovalRule, ...]
    risk_level: NonEmptyString
    success_conditions: tuple[NonEmptyString, ...]
    failure_conditions: tuple[NonEmptyString, ...]
    rollback_strategy: tuple[NonEmptyString, ...]


class ControlDecision(FrozenModel):
    """Structured and explainable pre-execution gate decision."""

    decision: Decision
    reason_codes: tuple[NonEmptyString, ...]
    blocking_fields: tuple[NonEmptyString, ...]
    questions: tuple[NonEmptyString, ...]
    required_approver: NonEmptyString | None = None
    policy_version: NonEmptyString
    intent_id: NonEmptyString
    intent_version: PositiveVersion


class RetryRule(FrozenModel):
    """Per-step automatic retry boundary."""

    max_retries: Annotated[int, Field(ge=0)]
    retryable_conditions: tuple[NonEmptyString, ...] = ()


class PlanStep(FrozenModel):
    """One governed step in the fixed invoice execution plan."""

    step_id: NonEmptyString
    dependencies: tuple[NonEmptyString, ...] = ()
    tool_requirements: tuple[NonEmptyString, ...] = ()
    policy_checkpoints: tuple[NonEmptyString, ...] = ()
    approval_checkpoints: tuple[NonEmptyString, ...] = ()
    retry_rule: RetryRule | None = None
    terminal_state: RunState | None = None


class ExecutionPlan(FrozenModel):
    """Fixed, governed plan bound to an exact IntentSpec version."""

    plan_id: NonEmptyString
    intent_id: NonEmptyString
    intent_version: PositiveVersion
    steps: tuple[PlanStep, ...]
    terminal_success_state: RunState
    terminal_failure_states: tuple[RunState, ...]


class ExecutionRun(StrictModel):
    """Mutable runtime state with an immutable authorizing contract link."""

    run_id: Annotated[str, Field(min_length=1, frozen=True)]
    intent_id: Annotated[str, Field(min_length=1, frozen=True)]
    intent_version: Annotated[int, Field(ge=1, frozen=True)]
    plan_id: Annotated[str, Field(min_length=1, frozen=True)]
    state: RunState


class TrajectoryEvent(FrozenModel):
    """Observable, intent-linked execution evidence; never chain-of-thought."""

    event_id: NonEmptyString
    run_id: NonEmptyString
    intent_id: NonEmptyString
    intent_version: PositiveVersion
    timestamp: datetime
    sequence_number: Annotated[int, Field(ge=0)]
    step_id: NonEmptyString | None = None
    actor: NonEmptyString | None = None
    event_type: EventType
    state_before: NonEmptyString | None = None
    state_after: NonEmptyString | None = None
    tool: NonEmptyString | None = None
    tool_input_digest: NonEmptyString | None = None
    tool_output_digest: NonEmptyString | None = None
    policy_checks: tuple[NonEmptyString, ...] = ()
    decision: NonEmptyString | None = None
    retry_count: Annotated[int, Field(ge=0)] = 0
    latency_ms: Annotated[int, Field(ge=0)] | None = None
    status: NonEmptyString
    metadata: FrozenJsonObject = Field(default_factory=dict)


class HumanIntervention(FrozenModel):
    """A structured human decision linked to the authorized intent."""

    intervention_id: NonEmptyString
    run_id: NonEmptyString
    intent_id: NonEmptyString
    intent_version: PositiveVersion
    timestamp: datetime
    actor_id: NonEmptyString
    actor_role: NonEmptyString
    action: HumanAction
    reason: NonEmptyString
    constraint_changes: FrozenJsonObject = Field(default_factory=dict)


TERMINAL_RUN_STATES = frozenset(
    {RunState.COMPLETED, RunState.REJECTED, RunState.FAILED, RunState.CANCELLED}
)


class RunOutcome(FrozenModel):
    """Terminal result evaluated against the authorizing IntentSpec."""

    outcome_id: NonEmptyString
    run_id: NonEmptyString
    intent_id: NonEmptyString
    intent_version: PositiveVersion
    status: RunState
    success_conditions_satisfied: tuple[NonEmptyString, ...]
    failure_conditions_triggered: tuple[NonEmptyString, ...]
    completed_at: datetime
    summary: NonEmptyString

    @model_validator(mode="after")
    def require_terminal_status(self) -> RunOutcome:
        if self.status not in TERMINAL_RUN_STATES:
            raise ValueError("RunOutcome status must be terminal")
        return self


class PolicySet(FrozenModel):
    """Machine-readable form of the ten deterministic finance-v1 rules."""

    policy_version: NonEmptyString
    rule_ids: tuple[NonEmptyString, ...]
    vendor_must_exist: bool
    agent_may_modify_vendor_bank_details: bool
    valid_purchase_order_required: bool
    duplicate_invoice_decision: Decision
    max_autonomous_payment_usd: Annotated[Decimal, Field(ge=0)]
    required_approver_above_limit: NonEmptyString
    bypass_approval_decision: Decision
    payment_requires_all_validations: bool
    transient_read_max_retries: Annotated[int, Field(ge=0)]
    uncertain_payment_auto_retry: bool


FINANCE_V1_POLICY = PolicySet(
    policy_version="finance-v1",
    rule_ids=("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"),
    vendor_must_exist=True,
    agent_may_modify_vendor_bank_details=False,
    valid_purchase_order_required=True,
    duplicate_invoice_decision=Decision.REJECT,
    max_autonomous_payment_usd=Decimal("10000"),
    required_approver_above_limit="finance_manager",
    bypass_approval_decision=Decision.REJECT,
    payment_requires_all_validations=True,
    transient_read_max_retries=2,
    uncertain_payment_auto_retry=False,
)


REQUEST_ADMISSIBILITY_LABELS = tuple(Decision)
RUNTIME_BENCHMARK_BUCKETS = (
    "allowed",
    "require escalation",
    "prohibited",
    "retry/fail-safe",
)
