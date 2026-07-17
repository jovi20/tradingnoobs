"""Typed loader and write-boundary helpers for the frozen journal Beta contract."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MetadataContract(_FrozenModel):
    schema_version: Literal[1]
    contract_id: Literal["TRADING_JOURNAL_BETA_V1"]
    status: Literal["FROZEN"]
    scope: Literal["INVITE_ONLY_TRADING_JOURNAL_BETA"]


class CurrencyContract(_FrozenModel):
    deployment_base_currency: Literal["USD"]
    account_base_currencies: tuple[Literal["USD"], ...]
    display_currencies: tuple[Literal["USD"], ...]
    financial_fact_currencies: tuple[Literal["USD"], ...]
    stablecoin_aliases: dict[str, str]
    legacy_nonconforming_policy: Literal["READ_EXPORT_ARCHIVE_ONLY"]
    release_gate_max_nonconforming_accounts: Literal[0]


class NumericContract(_FrozenModel):
    storage_precision: Literal[20]
    storage_scale: Literal[8]
    rounding: Literal["ROUND_HALF_EVEN"]
    intermediate_rounding: Literal[False]


class InstrumentCombinationContract(_FrozenModel):
    asset_type: str
    instrument_type: str
    market: str


class InstrumentContract(_FrozenModel):
    asset_types: tuple[str, ...]
    instrument_types: tuple[str, ...]
    markets: tuple[str, ...]
    asset_type_aliases: dict[str, str]
    allowed_combinations: tuple[InstrumentCombinationContract, ...]
    identity_fields: tuple[str, ...]
    exchange_code_required: Literal[True]
    identity_token_normalization: Literal["ASCII_TRIM_UPPER"]
    exchange_code_pattern: str
    normalized_symbol_pattern: str
    quote_currency_must_equal_account_currency: Literal[True]
    disabled_asset_types: tuple[str, ...]
    disabled_instrument_types: tuple[str, ...]


class LifecycleContract(_FrozenModel):
    position_mode: Literal["HEDGE_BY_DIRECTION"]
    cost_basis_method: Literal["FIFO"]
    sides: tuple[Literal["LONG", "SHORT"], ...]
    financially_open_unique_key: tuple[str, ...]
    automatic_netting: Literal[False]
    cross_zero_execution: Literal[False]
    ordinary_backdate: Literal[False]


class EventContract(_FrozenModel):
    trade: tuple[str, ...]
    cash: tuple[str, ...]
    corporate_action: tuple[str, ...]
    correction: tuple[str, ...]
    transaction_input_map: dict[str, str]
    disabled: tuple[str, ...]


class FeeContract(_FrozenModel):
    model: Literal["ONE_AGGREGATED_FEE_PER_TRADE_EVENT"]
    max_aggregated_fees_per_trade_event: Literal[1]
    component_breakdown_enabled: Literal[False]
    input_sign: Literal["NON_NEGATIVE"]
    currency_must_equal_account_currency: Literal[True]
    posting_kind: Literal["TRADE_FEE"]
    posting_sign: Literal["NEGATIVE"]
    realized_pnl_posting_kind: Literal["REALIZED_GROSS"]
    opening_fee_allocation: Literal["FIFO_QUANTITY_PRO_RATA_LAST_CONSUMPTION_REMAINDER"]
    realized_pnl_net_definition: Literal["REALIZED_GROSS_MINUS_CLOSE_FEE_MINUS_CONSUMED_OPEN_FEE"]
    posting_unique_key: tuple[str, ...]


class TimeContract(_FrozenModel):
    user_iana_timezone_required: Literal[True]
    default_timezone: None
    persistence: Literal["UTC_AWARE"]
    offset_input_interpretation: Literal["USE_INPUT_OFFSET"]
    naive_input_interpretation: Literal["USER_IANA_TIMEZONE"]
    dst_ambiguous_status: Literal[422]
    dst_nonexistent_status: Literal[422]
    day_boundary: Literal["USER_IANA_TIMEZONE"]


class IdempotencyContract(_FrozenModel):
    identity_fields: tuple[str, ...]
    key_hash_algorithm: Literal["SHA256"]
    request_hash_algorithm: Literal["SHA256"]
    request_serialization: Literal["CANONICAL_JSON_V1"]
    persist_raw_key: Literal[False]
    operation_scope_versioned: Literal[True]
    operation_scope_format: Literal["STABLE_VERSIONED_COMMAND_NAME"]
    same_request_behavior: Literal["REPLAY_ORIGINAL_RESPONSE"]
    different_request_status: Literal[409]
    financial_retention: Literal["PERMANENT"]
    import_audit_retention: Literal["PERMANENT"]
    response_schema_version_required: Literal[True]


class GenericBootstrapContract(_FrozenModel):
    formats: tuple[str, ...]
    mode: Literal["ONE_TIME_BOOTSTRAP"]
    trusted_external_trade_ids: Literal[False]
    implementation_gate: Literal["JRN_011_AND_JRN_012"]


class OwnerUploadLimitsContract(_FrozenModel):
    max_nonterminal_sessions: Literal[2]
    max_uploads_per_window: Literal[10]
    window_seconds: Literal[600]


class IbkrFlexContract(_FrozenModel):
    formats: tuple[Literal["XML"], ...]
    transport: Literal["LOCAL_UPLOAD_ONLY"]
    network_access: Literal[False]
    credential_access: Literal[False]
    repeat_overlap_incremental: Literal[True]
    first_binding_effect: Literal["EFFECTIVE_EXECUTION_OR_PROVEN_FLAT_COVERAGE"]
    proven_flat_empty_statement_can_bind: Literal[True]
    proven_flat_empty_binding_session_state: Literal["COMPLETED"]
    execution_identity_field: Literal["ibExecID"]
    provider_contract_gate_required: Literal[True]
    implementation_gate: Literal["JRN_013_THROUGH_JRN_015"]
    owner_upload_limits: OwnerUploadLimitsContract


class ImportLimitsContract(_FrozenModel):
    max_file_bytes: Literal[10485760]
    max_rows_or_executions: Literal[5000]
    preview_ttl_seconds: Literal[86400]
    terminal_normalized_row_retention_days: Literal[30]


class ImportContract(_FrozenModel):
    adapter_allowlist: tuple[str, ...]
    generic_bootstrap: GenericBootstrapContract
    ibkr_flex_xml_v1: IbkrFlexContract
    common_limits: ImportLimitsContract


class ImportSessionTransitionContract(_FrozenModel):
    from_state: str
    to_states: tuple[str, ...]


class TradeSourceTransitionContract(_FrozenModel):
    from_state: str
    to_state: str
    trigger: str


class SourceStateContract(_FrozenModel):
    trade_source_state: tuple[str, ...]
    source_health: tuple[str, ...]
    source_completeness: tuple[str, ...]
    source_health_truth: Literal["IMPORT_SOURCE_BINDING"]
    non_source_bound_health_projection: Literal["NOT_APPLICABLE"]
    import_session_states: tuple[str, ...]
    terminal_import_session_states: tuple[str, ...]
    import_session_transitions: tuple[ImportSessionTransitionContract, ...]
    trade_source_transitions: tuple[TradeSourceTransitionContract, ...]


class CapabilityContract(_FrozenModel):
    deployment_allowlist_env: Literal["DEPLOYMENT_CAPABILITY_ALLOWLIST"]
    effective_formula: Literal["DEPLOYMENT_ALLOWLIST_AND_RUNTIME_ROLLOUT"]
    unknown_deployment_token_policy: Literal["STARTUP_FAILURE"]
    missing_deployment_config_policy: Literal["EMPTY_ALLOWLIST"]
    runtime_flag_missing_policy: Literal["DISABLED"]
    runtime_flag_read_failure_policy: Literal["DISABLED"]
    runtime_flag_expired_policy: Literal["DISABLED"]
    runtime_flag_malformed_policy: Literal["DISABLED"]
    ceiling_storage: Literal["DEPLOYMENT_CONFIGURATION_ONLY"]
    admin_outside_ceiling_policy: Literal["FEATURE_DISABLED_NO_SIDE_EFFECT"]
    default_disabled: tuple[str, ...]
    runtime_flag_keys: dict[str, str]


class JournalBetaReleaseContract(_FrozenModel):
    metadata: MetadataContract
    currency: CurrencyContract
    numeric: NumericContract
    instruments: InstrumentContract
    lifecycle: LifecycleContract
    events: EventContract
    fees: FeeContract
    time: TimeContract
    idempotency: IdempotencyContract
    imports: ImportContract
    source_states: SourceStateContract
    capabilities: CapabilityContract

    @model_validator(mode="after")
    def validate_internal_parity(self):
        def require_exact(actual, expected, label: str) -> None:
            if actual != expected:
                raise ValueError(f"{label} must equal {expected!r}")

        require_exact(self.currency.account_base_currencies, ("USD",), "account currencies")
        require_exact(self.currency.display_currencies, ("USD",), "display currencies")
        require_exact(self.currency.financial_fact_currencies, ("USD",), "fact currencies")
        require_exact(self.instruments.asset_types, ("STOCK", "FUND", "CRYPTO"), "asset types")
        require_exact(self.instruments.instrument_types, ("SPOT",), "instrument types")
        require_exact(self.instruments.markets, ("US", "CRYPTO"), "markets")
        require_exact(
            self.instruments.asset_type_aliases,
            {"EQUITY": "STOCK", "ETF": "FUND", "SPOT_CRYPTO": "CRYPTO"},
            "asset type aliases",
        )
        require_exact(
            self.instruments.identity_fields,
            ("asset_type", "market", "exchange_code", "normalized_symbol", "instrument_type", "quote_currency"),
            "instrument identity fields",
        )
        expected_combinations = (
            ("STOCK", "SPOT", "US"),
            ("FUND", "SPOT", "US"),
            ("CRYPTO", "SPOT", "CRYPTO"),
        )
        actual_combinations = tuple(
            (item.asset_type, item.instrument_type, item.market)
            for item in self.instruments.allowed_combinations
        )
        require_exact(actual_combinations, expected_combinations, "instrument combinations")
        require_exact(
            self.instruments.exchange_code_pattern,
            r"^[A-Z0-9][A-Z0-9._-]{0,31}$",
            "exchange code pattern",
        )
        require_exact(
            self.instruments.normalized_symbol_pattern,
            r"^[A-Z0-9][A-Z0-9._/-]{0,63}$",
            "symbol pattern",
        )
        require_exact(
            self.instruments.disabled_asset_types,
            ("BOND", "COMMODITY", "FX", "DERIVATIVE"),
            "disabled asset types",
        )
        require_exact(
            self.instruments.disabled_instrument_types,
            ("EQUITY_OPTION", "FUTURE", "OPTION"),
            "disabled instrument types",
        )
        for pattern_name in ("exchange_code_pattern", "normalized_symbol_pattern"):
            re.compile(getattr(self.instruments, pattern_name), flags=re.ASCII)

        require_exact(self.lifecycle.sides, ("LONG", "SHORT"), "position sides")
        require_exact(
            self.lifecycle.financially_open_unique_key,
            ("account_id", "instrument_id", "side"),
            "financially-open key",
        )
        require_exact(self.events.trade, ("OPEN", "ADD", "REDUCE", "CLOSE"), "trade events")
        require_exact(
            self.events.cash,
            ("OPENING_BALANCE", "DEPOSIT", "WITHDRAWAL", "INTEREST", "ACCOUNT_FEE"),
            "cash events",
        )
        require_exact(self.events.corporate_action, ("CASH_DIVIDEND",), "corporate actions")
        require_exact(self.events.correction, ("REVERSAL", "VOID"), "correction events")
        require_exact(
            self.events.transaction_input_map,
            {
                "DEPOSIT": "DEPOSIT",
                "WITHDRAWAL": "WITHDRAWAL",
                "INTEREST": "INTEREST",
                "FEE": "ACCOUNT_FEE",
            },
            "transaction input map",
        )
        require_exact(
            self.events.disabled,
            (
                "TRANSFER_IN",
                "TRANSFER_OUT",
                "STOCK_SPLIT",
                "OPTION_EXERCISE",
                "OPTION_ASSIGNMENT",
                "OPTION_EXPIRY",
                "MANUAL_ADJUSTMENT",
                "CASH_ADJUSTMENT",
                "SEPARATE_FEE_EVENT",
            ),
            "disabled events",
        )
        require_exact(
            self.fees.posting_unique_key,
            ("source_fact_public_id", "posting_kind"),
            "posting unique key",
        )
        require_exact(
            self.idempotency.identity_fields,
            ("owner_id", "operation_scope", "key_hash"),
            "idempotency identity",
        )
        require_exact(
            self.imports.adapter_allowlist,
            ("GENERIC_BOOTSTRAP", "IBKR_FLEX_XML_V1"),
            "import adapter allowlist",
        )
        require_exact(self.imports.generic_bootstrap.formats, ("CSV_UTF8", "XLSX"), "generic formats")
        require_exact(self.imports.ibkr_flex_xml_v1.formats, ("XML",), "IBKR formats")
        require_exact(
            self.source_states.trade_source_state,
            ("CLEAN", "MANUAL", "SOURCE_BOUND"),
            "trade source states",
        )
        require_exact(
            self.source_states.source_health,
            ("NOT_APPLICABLE", "HEALTHY", "RECONCILIATION_REQUIRED", "SOURCE_DIVERGED"),
            "source health states",
        )
        require_exact(
            self.source_states.source_completeness,
            ("CURRENT", "PENDING_IMPORT"),
            "source completeness states",
        )
        require_exact(
            self.source_states.import_session_states,
            (
                "UPLOADING",
                "PREVIEW_READY",
                "CONFIRMING",
                "COMPLETED",
                "COMPLETED_NOOP",
                "CONFLICTED",
                "FAILED",
                "EXPIRED",
            ),
            "ImportSession states",
        )
        require_exact(
            self.source_states.terminal_import_session_states,
            ("COMPLETED", "COMPLETED_NOOP", "CONFLICTED", "FAILED", "EXPIRED"),
            "terminal ImportSession states",
        )
        require_exact(
            tuple(
                (transition.from_state, transition.to_states)
                for transition in self.source_states.import_session_transitions
            ),
            (
                ("UPLOADING", ("PREVIEW_READY", "CONFLICTED", "FAILED", "EXPIRED")),
                ("PREVIEW_READY", ("CONFIRMING", "EXPIRED")),
                ("CONFIRMING", ("COMPLETED", "COMPLETED_NOOP", "CONFLICTED", "FAILED")),
            ),
            "ImportSession transitions",
        )
        require_exact(
            tuple(
                (transition.from_state, transition.to_state, transition.trigger)
                for transition in self.source_states.trade_source_transitions
            ),
            (
                ("CLEAN", "MANUAL", "FIRST_MANUAL_TRADE_OR_GENERIC_NON_NOOP_CONFIRM"),
                ("CLEAN", "SOURCE_BOUND", "FIRST_IBKR_FLEX_BINDING_EFFECTIVE_CONFIRM"),
                ("SOURCE_BOUND", "SOURCE_BOUND", "SAME_BINDING_REPEAT_OVERLAP_OR_INCREMENTAL_CONFIRM"),
            ),
            "trade source transitions",
        )
        expected_capabilities = (
            "BROKER_SYNC",
            "MARKET",
            "AI_INSIGHTS",
            "PDF_EXPORT",
            "RISK_CARDS",
            "OPEN_REGISTRATION",
        )
        require_exact(self.capabilities.default_disabled, expected_capabilities, "disabled capabilities")
        require_exact(
            self.capabilities.runtime_flag_keys,
            {
                "BROKER_SYNC": "capability.broker_sync.v1",
                "MARKET": "capability.market.v1",
                "AI_INSIGHTS": "capability.ai_insights.v1",
                "PDF_EXPORT": "capability.pdf_export.v1",
                "RISK_CARDS": "capability.risk_cards.v1",
                "OPEN_REGISTRATION": "capability.open_registration.v1",
            },
            "runtime flag keys",
        )
        capability_ids = set(self.capabilities.default_disabled)
        if capability_ids != set(self.capabilities.runtime_flag_keys):
            raise ValueError("capability IDs and runtime flag keys must match")
        enabled_events = {
            *self.events.trade,
            *self.events.cash,
            *self.events.corporate_action,
            *self.events.correction,
        }
        overlap = enabled_events.intersection(self.events.disabled)
        if overlap:
            raise ValueError(f"events cannot be enabled and disabled: {sorted(overlap)}")
        if self.currency.stablecoin_aliases:
            raise ValueError("the Beta contract must not alias stablecoins to fiat")
        if set(self.instruments.asset_type_aliases.values()) - set(self.instruments.asset_types):
            raise ValueError("asset aliases must resolve to allowed asset types")
        if set(self.events.transaction_input_map.values()) - set(self.events.cash):
            raise ValueError("transaction inputs must resolve to enabled cash events")
        transition_sources = {item.from_state for item in self.source_states.import_session_transitions}
        if transition_sources != {"UPLOADING", "PREVIEW_READY", "CONFIRMING"}:
            raise ValueError("ImportSession transition sources do not match nonterminal states")
        all_session_states = set(self.source_states.import_session_states)
        for transition in self.source_states.import_session_transitions:
            if transition.from_state not in all_session_states or not set(transition.to_states) <= all_session_states:
                raise ValueError("ImportSession transition references an unknown state")
        return self


CONTRACT_PATH = Path(__file__).with_name("journal_beta_v1.json")


def load_release_contract(path: Path = CONTRACT_PATH) -> JournalBetaReleaseContract:
    with path.open("r", encoding="utf-8") as contract_file:
        return JournalBetaReleaseContract.model_validate(json.load(contract_file))


JOURNAL_BETA_CONTRACT = load_release_contract()
RELEASE_BASE_CURRENCY = JOURNAL_BETA_CONTRACT.currency.deployment_base_currency
ALLOWED_ASSET_TYPES = frozenset(JOURNAL_BETA_CONTRACT.instruments.asset_types)
ALLOWED_INSTRUMENT_TYPES = frozenset(JOURNAL_BETA_CONTRACT.instruments.instrument_types)
ALLOWED_MARKETS = frozenset(JOURNAL_BETA_CONTRACT.instruments.markets)
ASSET_TYPE_ALIASES = MappingProxyType(dict(JOURNAL_BETA_CONTRACT.instruments.asset_type_aliases))
TRANSACTION_INPUT_MAP = MappingProxyType(dict(JOURNAL_BETA_CONTRACT.events.transaction_input_map))
ALLOWED_TRANSACTION_TYPES = frozenset(TRANSACTION_INPUT_MAP)


class ReleaseContractViolation(ValueError):
    def __init__(self, code: str, field: str, value: object):
        self.code = code
        self.field = field
        self.value = value
        super().__init__(f"{code}: {field} is outside the journal Beta contract")


def normalize_contract_token(value: object) -> str:
    return str(value or "").strip().upper()


def require_release_currency(value: object, *, field: str = "currency") -> str:
    normalized = normalize_contract_token(value)
    if normalized != RELEASE_BASE_CURRENCY:
        raise ReleaseContractViolation("UNSUPPORTED_RELEASE_CURRENCY", field, value)
    return normalized


def require_allowed_transaction_type(value: object) -> str:
    normalized = normalize_contract_token(getattr(value, "value", value))
    canonical_event = TRANSACTION_INPUT_MAP.get(normalized)
    if canonical_event not in JOURNAL_BETA_CONTRACT.events.cash:
        raise ReleaseContractViolation("UNSUPPORTED_TRANSACTION_TYPE", "type", value)
    return normalized


def require_allowed_asset_type(value: object) -> str:
    normalized = normalize_contract_token(getattr(value, "value", value))
    normalized = ASSET_TYPE_ALIASES.get(normalized, normalized)
    if normalized not in ALLOWED_ASSET_TYPES:
        raise ReleaseContractViolation("UNSUPPORTED_ASSET_TYPE", "asset_type", value)
    return normalized


def release_violation_detail(violation: ReleaseContractViolation) -> dict[str, object]:
    return {
        "code": violation.code,
        "message": "Input is outside the frozen trading-journal Beta contract",
        "field": violation.field,
    }
