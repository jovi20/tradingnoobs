from __future__ import annotations

import json
import unittest

from pydantic import ValidationError

from app_config.release_contract import (
    ALLOWED_ASSET_TYPES,
    ALLOWED_TRANSACTION_TYPES,
    CONTRACT_PATH,
    JOURNAL_BETA_CONTRACT,
    JournalBetaReleaseContract,
    ReleaseContractViolation,
    load_release_contract,
    require_allowed_asset_type,
    require_allowed_instrument_type,
    require_allowed_market,
    require_allowed_transaction_type,
    require_exchange_code,
    require_normalized_symbol,
    require_release_currency,
)


class JournalBetaReleaseContractTests(unittest.TestCase):
    def test_contract_round_trips_through_strict_typed_loader(self):
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        loaded = load_release_contract()

        self.assertEqual(loaded.metadata.contract_id, "TRADING_JOURNAL_BETA_V1")
        self.assertEqual(loaded.model_dump(mode="json"), raw)
        self.assertEqual(loaded.currency.account_base_currencies, ("USD",))
        self.assertEqual(loaded.lifecycle.position_mode, "HEDGE_BY_DIRECTION")
        self.assertEqual(ALLOWED_ASSET_TYPES, {"STOCK", "FUND", "CRYPTO"})
        self.assertEqual(ALLOWED_TRANSACTION_TYPES, {"DEPOSIT", "WITHDRAWAL", "INTEREST", "FEE"})

    def test_contract_rejects_enum_drift_and_unknown_fields(self):
        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        raw["instruments"]["asset_types"] = ["STOCK", "FUND", "CRYPTO", "BOND"]
        with self.assertRaises(ValidationError):
            JournalBetaReleaseContract.model_validate(raw)

        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        raw["instruments"]["shared_asset_metadata_user_write"] = "ALLOWED"
        with self.assertRaises(ValidationError):
            JournalBetaReleaseContract.model_validate(raw)

        raw = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        raw["currency"]["silent_fx_conversion"] = True
        with self.assertRaises(ValidationError):
            JournalBetaReleaseContract.model_validate(raw)

    def test_currency_is_exact_usd_and_never_aliases_usdt(self):
        self.assertEqual(require_release_currency(" usd "), "USD")
        for rejected in (None, "", "USDT", "HKD", "CNY"):
            with self.subTest(value=rejected):
                with self.assertRaises(ReleaseContractViolation) as raised:
                    require_release_currency(rejected)
                self.assertEqual(raised.exception.code, "UNSUPPORTED_RELEASE_CURRENCY")

    def test_public_write_allowlists_reject_deferred_types(self):
        self.assertEqual(require_allowed_asset_type("ETF"), "FUND")
        self.assertEqual(require_allowed_asset_type("spot_crypto"), "CRYPTO")
        self.assertEqual(require_allowed_transaction_type("FEE"), "FEE")

        for asset_type in ("BOND", "FX", "DERIVATIVE", "OPTION"):
            with self.subTest(asset_type=asset_type):
                with self.assertRaises(ReleaseContractViolation):
                    require_allowed_asset_type(asset_type)

        for transaction_type in ("TRANSFER_IN", "TRANSFER_OUT", "CASH_ADJUSTMENT"):
            with self.subTest(transaction_type=transaction_type):
                with self.assertRaises(ReleaseContractViolation):
                    require_allowed_transaction_type(transaction_type)

    def test_instrument_tokens_require_raw_ascii_and_match_storage_widths(self):
        instrument_contract = JOURNAL_BETA_CONTRACT.instruments
        self.assertEqual(
            instrument_contract.raw_identity_token_policy,
            "REJECT_NON_ASCII_THEN_TRIM_UPPER",
        )
        self.assertEqual(
            instrument_contract.legacy_identity_evidence,
            ("REQUEST_VALIDATED", "EXACT_JOURNAL_IDENTITY_V1"),
        )
        self.assertEqual(
            instrument_contract.legacy_unproven_error,
            "LEGACY_INSTRUMENT_IDENTITY_UNPROVEN",
        )
        self.assertEqual(
            instrument_contract.preupgrade_truth_read_policy,
            "READ_ONLY_NO_IDENTITY_REWRITE",
        )
        self.assertEqual(instrument_contract.shared_asset_metadata_owner, "SYSTEM")
        self.assertEqual(instrument_contract.shared_asset_metadata_user_write, "FORBIDDEN")
        self.assertEqual(instrument_contract.canonical_identity_schema_task, "JRN-007")
        self.assertEqual(require_exchange_code(" nasdaq "), "NASDAQ")
        self.assertEqual(require_normalized_symbol(" btc/usd "), "BTC/USD")
        self.assertEqual(require_normalized_symbol("a" * 50), "A" * 50)

        for value in ("ß", "naſdaq", "ı", "ﬀ", "A" * 33):
            with self.subTest(exchange_code=value):
                with self.assertRaises(ReleaseContractViolation) as raised:
                    require_exchange_code(value)
                self.assertEqual(raised.exception.code, "INVALID_EXCHANGE_CODE")

        for value in ("ſpy", "ıbm", "ﬀ", "A" * 51):
            with self.subTest(symbol=value):
                with self.assertRaises(ReleaseContractViolation) as raised:
                    require_normalized_symbol(value)
                self.assertEqual(raised.exception.code, "INVALID_NORMALIZED_SYMBOL")

    def test_all_identity_tokens_reject_unicode_whitespace_before_normalization(self):
        cases = (
            (lambda value: require_allowed_asset_type(value), "\u00a0stock\u00a0", "UNSUPPORTED_ASSET_TYPE"),
            (lambda value: require_allowed_market(value), "\u2003us\u2003", "UNSUPPORTED_MARKET"),
            (
                lambda value: require_allowed_instrument_type(value),
                "\u00a0spot\u00a0",
                "UNSUPPORTED_INSTRUMENT_TYPE",
            ),
            (lambda value: require_release_currency(value), "\u2003usd\u2003", "UNSUPPORTED_RELEASE_CURRENCY"),
            (lambda value: require_exchange_code(value), "\u00a0nasdaq\u00a0", "INVALID_EXCHANGE_CODE"),
            (lambda value: require_normalized_symbol(value), "\u2003aapl\u2003", "INVALID_NORMALIZED_SYMBOL"),
        )
        for validator, value, expected_code in cases:
            with self.subTest(value=value, expected_code=expected_code):
                with self.assertRaises(ReleaseContractViolation) as raised:
                    validator(value)
                self.assertEqual(raised.exception.code, expected_code)

    def test_import_and_source_names_are_frozen_without_claiming_implementation(self):
        contract = JOURNAL_BETA_CONTRACT
        self.assertEqual(
            contract.imports.adapter_allowlist,
            ("GENERIC_BOOTSTRAP", "IBKR_FLEX_XML_V1"),
        )
        self.assertFalse(contract.imports.ibkr_flex_xml_v1.network_access)
        self.assertFalse(contract.imports.ibkr_flex_xml_v1.credential_access)
        self.assertTrue(contract.imports.ibkr_flex_xml_v1.repeat_overlap_incremental)
        self.assertEqual(
            contract.imports.ibkr_flex_xml_v1.first_binding_effect,
            "EFFECTIVE_EXECUTION_OR_PROVEN_FLAT_COVERAGE",
        )
        self.assertTrue(contract.imports.ibkr_flex_xml_v1.proven_flat_empty_statement_can_bind)
        self.assertEqual(
            contract.imports.ibkr_flex_xml_v1.proven_flat_empty_binding_session_state,
            "COMPLETED",
        )
        self.assertTrue(contract.imports.ibkr_flex_xml_v1.provider_contract_gate_required)
        self.assertEqual(contract.imports.common_limits.max_file_bytes, 10 * 1024 * 1024)
        self.assertEqual(contract.imports.common_limits.max_rows_or_executions, 5000)
        self.assertEqual(contract.imports.common_limits.preview_ttl_seconds, 24 * 60 * 60)
        self.assertEqual(
            contract.imports.ibkr_flex_xml_v1.owner_upload_limits.max_nonterminal_sessions,
            2,
        )
        self.assertEqual(
            contract.source_states.trade_source_state,
            ("CLEAN", "MANUAL", "SOURCE_BOUND"),
        )
        self.assertEqual(
            contract.source_states.source_health,
            ("NOT_APPLICABLE", "HEALTHY", "RECONCILIATION_REQUIRED", "SOURCE_DIVERGED"),
        )
        self.assertEqual(contract.source_states.source_health_truth, "IMPORT_SOURCE_BINDING")
        self.assertEqual(
            tuple(item.from_state for item in contract.source_states.import_session_transitions),
            ("UPLOADING", "PREVIEW_READY", "CONFIRMING"),
        )
        self.assertEqual(
            tuple(
                (item.from_state, item.to_state, item.trigger)
                for item in contract.source_states.trade_source_transitions
            ),
            (
                ("CLEAN", "MANUAL", "FIRST_MANUAL_TRADE_OR_GENERIC_NON_NOOP_CONFIRM"),
                ("CLEAN", "SOURCE_BOUND", "FIRST_IBKR_FLEX_BINDING_EFFECTIVE_CONFIRM"),
                ("SOURCE_BOUND", "SOURCE_BOUND", "SAME_BINDING_REPEAT_OVERLAP_OR_INCREMENTAL_CONFIRM"),
            ),
        )

    def test_fee_time_idempotency_and_capability_contracts_are_exact(self):
        contract = JOURNAL_BETA_CONTRACT
        self.assertEqual(contract.fees.max_aggregated_fees_per_trade_event, 1)
        self.assertFalse(contract.fees.component_breakdown_enabled)
        self.assertEqual(contract.time.offset_input_interpretation, "USE_INPUT_OFFSET")
        self.assertIsNone(contract.time.default_timezone)
        self.assertEqual(contract.idempotency.identity_fields, ("owner_id", "operation_scope", "key_hash"))
        self.assertFalse(contract.idempotency.persist_raw_key)
        self.assertEqual(contract.idempotency.financial_retention, "PERMANENT")
        self.assertEqual(contract.capabilities.ceiling_storage, "DEPLOYMENT_CONFIGURATION_ONLY")
        self.assertEqual(
            contract.capabilities.admin_outside_ceiling_policy,
            "FEATURE_DISABLED_NO_SIDE_EFFECT",
        )


if __name__ == "__main__":
    unittest.main()
