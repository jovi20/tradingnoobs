// Generated from backend/app_config/journal_beta_v1.json. Do not edit.
export const JOURNAL_BETA_RELEASE_CONTRACT = {
    "metadata": {
        "schema_version": 1,
        "contract_id": "TRADING_JOURNAL_BETA_V1",
        "status": "FROZEN",
        "scope": "INVITE_ONLY_TRADING_JOURNAL_BETA"
    },
    "currency": {
        "deployment_base_currency": "USD",
        "account_base_currencies": [
            "USD"
        ],
        "display_currencies": [
            "USD"
        ],
        "financial_fact_currencies": [
            "USD"
        ],
        "stablecoin_aliases": {},
        "legacy_nonconforming_policy": "READ_EXPORT_ARCHIVE_ONLY",
        "release_gate_max_nonconforming_accounts": 0
    },
    "numeric": {
        "storage_precision": 20,
        "storage_scale": 8,
        "rounding": "ROUND_HALF_EVEN",
        "intermediate_rounding": false
    },
    "instruments": {
        "asset_types": [
            "STOCK",
            "FUND",
            "CRYPTO"
        ],
        "instrument_types": [
            "SPOT"
        ],
        "markets": [
            "US",
            "CRYPTO"
        ],
        "asset_type_aliases": {
            "EQUITY": "STOCK",
            "ETF": "FUND",
            "SPOT_CRYPTO": "CRYPTO"
        },
        "allowed_combinations": [
            {
                "asset_type": "STOCK",
                "instrument_type": "SPOT",
                "market": "US"
            },
            {
                "asset_type": "FUND",
                "instrument_type": "SPOT",
                "market": "US"
            },
            {
                "asset_type": "CRYPTO",
                "instrument_type": "SPOT",
                "market": "CRYPTO"
            }
        ],
        "identity_fields": [
            "asset_type",
            "market",
            "exchange_code",
            "normalized_symbol",
            "instrument_type",
            "quote_currency"
        ],
        "exchange_code_required": true,
        "identity_token_normalization": "ASCII_TRIM_UPPER",
        "exchange_code_pattern": "^[A-Z0-9][A-Z0-9._-]{0,31}$",
        "normalized_symbol_pattern": "^[A-Z0-9][A-Z0-9._/-]{0,63}$",
        "quote_currency_must_equal_account_currency": true,
        "disabled_asset_types": [
            "BOND",
            "COMMODITY",
            "FX",
            "DERIVATIVE"
        ],
        "disabled_instrument_types": [
            "EQUITY_OPTION",
            "FUTURE",
            "OPTION"
        ]
    },
    "lifecycle": {
        "position_mode": "HEDGE_BY_DIRECTION",
        "cost_basis_method": "FIFO",
        "sides": [
            "LONG",
            "SHORT"
        ],
        "financially_open_unique_key": [
            "account_id",
            "instrument_id",
            "side"
        ],
        "automatic_netting": false,
        "cross_zero_execution": false,
        "ordinary_backdate": false
    },
    "events": {
        "trade": [
            "OPEN",
            "ADD",
            "REDUCE",
            "CLOSE"
        ],
        "cash": [
            "OPENING_BALANCE",
            "DEPOSIT",
            "WITHDRAWAL",
            "INTEREST",
            "ACCOUNT_FEE"
        ],
        "corporate_action": [
            "CASH_DIVIDEND"
        ],
        "correction": [
            "REVERSAL",
            "VOID"
        ],
        "transaction_input_map": {
            "DEPOSIT": "DEPOSIT",
            "WITHDRAWAL": "WITHDRAWAL",
            "INTEREST": "INTEREST",
            "FEE": "ACCOUNT_FEE"
        },
        "disabled": [
            "TRANSFER_IN",
            "TRANSFER_OUT",
            "STOCK_SPLIT",
            "OPTION_EXERCISE",
            "OPTION_ASSIGNMENT",
            "OPTION_EXPIRY",
            "MANUAL_ADJUSTMENT",
            "CASH_ADJUSTMENT",
            "SEPARATE_FEE_EVENT"
        ]
    },
    "fees": {
        "model": "ONE_AGGREGATED_FEE_PER_TRADE_EVENT",
        "max_aggregated_fees_per_trade_event": 1,
        "component_breakdown_enabled": false,
        "input_sign": "NON_NEGATIVE",
        "currency_must_equal_account_currency": true,
        "posting_kind": "TRADE_FEE",
        "posting_sign": "NEGATIVE",
        "realized_pnl_posting_kind": "REALIZED_GROSS",
        "opening_fee_allocation": "FIFO_QUANTITY_PRO_RATA_LAST_CONSUMPTION_REMAINDER",
        "realized_pnl_net_definition": "REALIZED_GROSS_MINUS_CLOSE_FEE_MINUS_CONSUMED_OPEN_FEE",
        "posting_unique_key": [
            "source_fact_public_id",
            "posting_kind"
        ]
    },
    "time": {
        "user_iana_timezone_required": true,
        "default_timezone": null,
        "persistence": "UTC_AWARE",
        "offset_input_interpretation": "USE_INPUT_OFFSET",
        "naive_input_interpretation": "USER_IANA_TIMEZONE",
        "dst_ambiguous_status": 422,
        "dst_nonexistent_status": 422,
        "day_boundary": "USER_IANA_TIMEZONE"
    },
    "idempotency": {
        "identity_fields": [
            "owner_id",
            "operation_scope",
            "key_hash"
        ],
        "key_hash_algorithm": "SHA256",
        "request_hash_algorithm": "SHA256",
        "request_serialization": "CANONICAL_JSON_V1",
        "persist_raw_key": false,
        "operation_scope_versioned": true,
        "operation_scope_format": "STABLE_VERSIONED_COMMAND_NAME",
        "same_request_behavior": "REPLAY_ORIGINAL_RESPONSE",
        "different_request_status": 409,
        "financial_retention": "PERMANENT",
        "import_audit_retention": "PERMANENT",
        "response_schema_version_required": true
    },
    "imports": {
        "adapter_allowlist": [
            "GENERIC_BOOTSTRAP",
            "IBKR_FLEX_XML_V1"
        ],
        "generic_bootstrap": {
            "formats": [
                "CSV_UTF8",
                "XLSX"
            ],
            "mode": "ONE_TIME_BOOTSTRAP",
            "trusted_external_trade_ids": false,
            "implementation_gate": "JRN_011_AND_JRN_012"
        },
        "ibkr_flex_xml_v1": {
            "formats": [
                "XML"
            ],
            "transport": "LOCAL_UPLOAD_ONLY",
            "network_access": false,
            "credential_access": false,
            "repeat_overlap_incremental": true,
            "execution_identity_field": "ibExecID",
            "provider_contract_gate_required": true,
            "implementation_gate": "JRN_013_THROUGH_JRN_015",
            "owner_upload_limits": {
                "max_nonterminal_sessions": 2,
                "max_uploads_per_window": 10,
                "window_seconds": 600
            }
        },
        "common_limits": {
            "max_file_bytes": 10485760,
            "max_rows_or_executions": 5000,
            "preview_ttl_seconds": 86400,
            "terminal_normalized_row_retention_days": 30
        }
    },
    "source_states": {
        "trade_source_state": [
            "CLEAN",
            "MANUAL",
            "SOURCE_BOUND"
        ],
        "source_health": [
            "NOT_APPLICABLE",
            "HEALTHY",
            "RECONCILIATION_REQUIRED",
            "SOURCE_DIVERGED"
        ],
        "source_completeness": [
            "CURRENT",
            "PENDING_IMPORT"
        ],
        "source_health_truth": "IMPORT_SOURCE_BINDING",
        "non_source_bound_health_projection": "NOT_APPLICABLE",
        "import_session_states": [
            "UPLOADING",
            "PREVIEW_READY",
            "CONFIRMING",
            "COMPLETED",
            "COMPLETED_NOOP",
            "CONFLICTED",
            "FAILED",
            "EXPIRED"
        ],
        "terminal_import_session_states": [
            "COMPLETED",
            "COMPLETED_NOOP",
            "CONFLICTED",
            "FAILED",
            "EXPIRED"
        ],
        "import_session_transitions": [
            {
                "from_state": "UPLOADING",
                "to_states": [
                    "PREVIEW_READY",
                    "CONFLICTED",
                    "FAILED",
                    "EXPIRED"
                ]
            },
            {
                "from_state": "PREVIEW_READY",
                "to_states": [
                    "CONFIRMING",
                    "EXPIRED"
                ]
            },
            {
                "from_state": "CONFIRMING",
                "to_states": [
                    "COMPLETED",
                    "COMPLETED_NOOP",
                    "CONFLICTED",
                    "FAILED"
                ]
            }
        ],
        "trade_source_transitions": [
            {
                "from_state": "CLEAN",
                "to_state": "MANUAL",
                "trigger": "FIRST_MANUAL_TRADE_OR_GENERIC_NON_NOOP_CONFIRM"
            },
            {
                "from_state": "CLEAN",
                "to_state": "SOURCE_BOUND",
                "trigger": "FIRST_IBKR_FLEX_NON_NOOP_CONFIRM"
            }
        ]
    },
    "capabilities": {
        "deployment_allowlist_env": "DEPLOYMENT_CAPABILITY_ALLOWLIST",
        "effective_formula": "DEPLOYMENT_ALLOWLIST_AND_RUNTIME_ROLLOUT",
        "unknown_deployment_token_policy": "STARTUP_FAILURE",
        "missing_deployment_config_policy": "EMPTY_ALLOWLIST",
        "runtime_flag_missing_policy": "DISABLED",
        "runtime_flag_read_failure_policy": "DISABLED",
        "runtime_flag_expired_policy": "DISABLED",
        "runtime_flag_malformed_policy": "DISABLED",
        "ceiling_storage": "DEPLOYMENT_CONFIGURATION_ONLY",
        "admin_outside_ceiling_policy": "FEATURE_DISABLED_NO_SIDE_EFFECT",
        "default_disabled": [
            "BROKER_SYNC",
            "MARKET",
            "AI_INSIGHTS",
            "PDF_EXPORT",
            "RISK_CARDS",
            "OPEN_REGISTRATION"
        ],
        "runtime_flag_keys": {
            "BROKER_SYNC": "capability.broker_sync.v1",
            "MARKET": "capability.market.v1",
            "AI_INSIGHTS": "capability.ai_insights.v1",
            "PDF_EXPORT": "capability.pdf_export.v1",
            "RISK_CARDS": "capability.risk_cards.v1",
            "OPEN_REGISTRATION": "capability.open_registration.v1"
        }
    }
} as const
export const RELEASE_CONTRACT_ID = "TRADING_JOURNAL_BETA_V1" as const
export const RELEASE_BASE_CURRENCY = "USD" as const
export const RELEASE_POSITION_MODE = "HEDGE_BY_DIRECTION" as const
export const RELEASE_ASSET_TYPES = ["STOCK","FUND","CRYPTO"] as const
export const RELEASE_INSTRUMENT_TYPES = ["SPOT"] as const
export const RELEASE_IMPORT_ADAPTERS = ["GENERIC_BOOTSTRAP","IBKR_FLEX_XML_V1"] as const
export const OPTIONAL_CAPABILITY_IDS = ["BROKER_SYNC","MARKET","AI_INSIGHTS","PDF_EXPORT","RISK_CARDS","OPEN_REGISTRATION"] as const
export const BROKER_SYNC_RUNTIME_ENABLED = false as const
export const MARKET_RUNTIME_ENABLED = false as const
export const AI_INSIGHTS_RUNTIME_ENABLED = false as const
export const PDF_EXPORT_RUNTIME_ENABLED = false as const
export const RISK_CARDS_RUNTIME_ENABLED = false as const
export const OPEN_REGISTRATION_RUNTIME_ENABLED = false as const
