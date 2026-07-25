from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "backend/app_config/journal_accounting_v1.json"
VECTORS_PATH = ROOT / "backend/tests/fixtures/jrn005_accounting_golden_vectors_v1.json"
Q = Decimal("0.00000001")


def q(value: Decimal | str) -> Decimal:
    return Decimal(value).quantize(Q, rounding=ROUND_HALF_EVEN)


def fmt(value: Decimal | str) -> str:
    return format(q(value), "f")


def test_machine_contract_is_exact_and_points_to_vectors():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert contract["contract_id"] == "JOURNAL_ACCOUNTING_V1"
    assert contract["status"] == "IMPLEMENTED"
    assert contract["implementation_task"] == "JRN-006"
    assert contract["implementation_migration"] == "c3d4e5f6a7b8"
    assert contract["authoritative_balance"] == "LEDGER_REPLAY"
    assert contract["append_only_guards"] == [
        "SQLALCHEMY_BEFORE_FLUSH",
        "SQLITE_TRIGGER",
        "POSTGRESQL_TRIGGER",
    ]
    assert ROOT / contract["golden_vectors"] == VECTORS_PATH
    assert contract["precision"] == {
        "numeric": "DECIMAL_ONLY",
        "posting_storage": "NUMERIC(20,8)",
        "posting_quantum": "0.00000001",
        "rounding": "ROUND_HALF_EVEN",
        "intermediate_quantization": False,
    }
    assert contract["postings"]["unique_key"] == [
        "source_fact_public_id",
        "posting_kind",
    ]
    assert contract["postings"]["realized_net_is_ledger_posting"] is False
    assert contract["fees"]["max_components_per_trade_event"] == 1
    assert contract["fees"]["ibkr_commission_normalization"] == (
        "ABS_NONZERO_COMMISSION_AS_COST"
    )
    assert contract["position_attribution"]["cross_side_netting"] is False


def test_golden_trade_vectors_reconcile_postings_fifo_fees_and_balance():
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))

    for vector in vectors["trade_vectors"]:
        lots = []
        postings = []
        event_results = []
        opened = Decimal("0")
        closed = Decimal("0")
        gross_total = Decimal("0")
        net_total = Decimal("0")
        fee_total = Decimal("0")

        for event in vector["events"]:
            event_type = event["type"]
            quantity = Decimal(event["quantity"])
            price = Decimal(event["price"])
            fee = q(event["fee"])
            fee_total += fee

            if event_type in {"OPEN", "ADD"}:
                if fee:
                    postings.append(
                        {
                            "source": event["id"],
                            "kind": "TRADE_FEE",
                            "amount": fmt(-fee),
                        }
                    )
                lots.append({"quantity": quantity, "price": price, "fee": fee})
                opened += quantity
                gross = Decimal("0")
                gross_raw = Decimal("0")
                consumed_fee = Decimal("0")
            else:
                remaining = quantity
                gross_raw = Decimal("0")
                consumed_fee = Decimal("0")
                while remaining:
                    lot = lots[0]
                    matched = min(lot["quantity"], remaining)
                    direction = Decimal("-1") if vector["side"] == "SHORT" else Decimal("1")
                    gross_raw += (price - lot["price"]) * matched * direction
                    if matched == lot["quantity"]:
                        allocation = lot["fee"]
                    else:
                        allocation = q(lot["fee"] * matched / lot["quantity"])
                    lot["quantity"] -= matched
                    lot["fee"] -= allocation
                    consumed_fee += allocation
                    remaining -= matched
                    if lot["quantity"] == 0:
                        lots.pop(0)
                closed += quantity
                gross = q(gross_raw)
                postings.append(
                    {"source": event["id"], "kind": "REALIZED_GROSS", "amount": fmt(gross)}
                )
                if fee:
                    postings.append(
                        {
                            "source": event["id"],
                            "kind": "TRADE_FEE",
                            "amount": fmt(-fee),
                        }
                    )

            net = (
                q(gross_raw - fee - consumed_fee)
                if event_type in {"REDUCE", "CLOSE"}
                else q(0)
            )
            gross_total += gross
            net_total += net
            event_results.append(
                    {
                        "id": event["id"],
                        "realized_gross": fmt(gross),
                        "consumed_open_fee": fmt(consumed_fee),
                        "realized_net": fmt(net),
                }
            )

        expected_postings = [
            {**item, "amount": fmt(item["amount"])}
            for item in vector["expected_postings"]
        ]
        assert postings == expected_postings, vector["id"]
        assert event_results == vector["expected_events"], vector["id"]

        summary = vector["expected_summary"]
        assert q(opened) == Decimal(summary["quantity_opened"])
        assert q(closed) == Decimal(summary["quantity_closed"])
        assert q(opened - closed) == Decimal(summary["open_quantity"])
        assert q(gross_total) == Decimal(summary["realized_gross"])
        assert q(net_total) == Decimal(summary["realized_net"])
        assert q(fee_total) == Decimal(summary["total_fees"])
        balance = q(Decimal(vector["opening_balance"]) + sum(
            (Decimal(item["amount"]) for item in postings),
            Decimal("0"),
        ))
        assert balance == Decimal(summary["journal_balance"])


def test_cash_reversal_hedge_commission_ordering_and_error_vectors():
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    cash = vectors["cash_vector"]
    assert q(
        Decimal(cash["opening_balance"])
        + sum((Decimal(item["posting"]) for item in cash["facts"]), Decimal("0"))
    ) == Decimal(cash["expected_journal_balance"])

    reversal = vectors["reversal_vector"]
    assert q(sum(
        (Decimal(item["amount"]) for item in reversal["original_postings"]),
        Decimal("0"),
    ) + sum(
        (Decimal(item["amount"]) for item in reversal["reversal_postings"]),
        Decimal("0"),
    )) == Decimal(reversal["expected_net_effect"])

    hedge = vectors["hedge_vector"]
    assert hedge["expected_position_count"] == 2
    assert hedge["cross_side_netting"] is False
    assert q(sum(
        (Decimal(item["net"]) for item in hedge["positions"]),
        Decimal("0"),
    )) == Decimal(hedge["expected_journal_balance_effect"])

    for item in vectors["ibkr_commission_vectors"]:
        assert q(abs(Decimal(item["raw"]))) == Decimal(item["expected_fee"])

    ordering = vectors["ordering_vector"]
    assert [
        item["id"] for item in sorted(ordering["input"], key=lambda item: item["sequence_no"])
    ] == ordering["expected"]

    for rejection in vectors["rejections"]:
        assert contract["errors"][rejection["code"]] == rejection["status"]


def test_posting_keys_are_unique_within_every_vector():
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))

    for vector in vectors["trade_vectors"]:
        keys = [
            (posting["source"], posting["kind"])
            for posting in vector["expected_postings"]
        ]
        assert len(keys) == len(set(keys)), vector["id"]
