from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from services.trade_lifecycle_simulation_service import (
    LifecycleSimulationError,
    derive_broker_lifecycle_step,
    simulate_canonical_lifecycle_step,
)


ROOT = Path(__file__).resolve().parents[2]
VECTORS = (
    ROOT / "backend/tests/fixtures/jrn005_accounting_golden_vectors_v1.json"
)


def test_canonical_simulation_matches_jrn005_golden_vector_quantities():
    contract = json.loads(VECTORS.read_text(encoding="utf-8"))
    for vector in contract["trade_vectors"]:
        current = Decimal("0")
        for event in vector["events"]:
            step = simulate_canonical_lifecycle_step(
                current_quantity=current,
                action=event["type"],
                quantity=event["quantity"],
                direction=vector["side"],
            )
            assert step.pre_quantity == current
            current = step.post_quantity
        assert current == Decimal(vector["expected_summary"]["open_quantity"])


@pytest.mark.parametrize(
    ("side", "open_close", "current", "quantity", "direction", "action", "post"),
    [
        ("BUY", "OPEN", "0", "2", "LONG", "OPEN", "2"),
        ("BUY", "OPEN", "2", "1", "LONG", "ADD", "3"),
        ("SELL", "CLOSE", "3", "1", "LONG", "REDUCE", "2"),
        ("SELL", "CLOSE", "2", "2", "LONG", "CLOSE", "0"),
        ("SELL", "OPEN", "0", "2", "SHORT", "OPEN", "2"),
        ("SELL", "OPEN", "2", "1", "SHORT", "ADD", "3"),
        ("BUY", "CLOSE", "3", "1", "SHORT", "REDUCE", "2"),
        ("BUY", "CLOSE", "2", "2", "SHORT", "CLOSE", "0"),
    ],
)
def test_ibkr_side_open_close_truth_table(
    side,
    open_close,
    current,
    quantity,
    direction,
    action,
    post,
):
    step = derive_broker_lifecycle_step(
        current_quantity=current,
        side=side,
        open_close=open_close,
        quantity=quantity,
    )
    assert step.direction == direction
    assert step.action == action
    assert step.post_quantity == Decimal(post)


@pytest.mark.parametrize(
    ("side", "open_close", "current", "quantity", "code"),
    [
        ("SELL", "CLOSE", "2", "3", "CLOSE_QUANTITY_MISMATCH"),
        ("BUY", "CLOSE", "0", "1", "ORPHAN_EVENT"),
        ("BUY", "UNKNOWN", "2", "1", "UNSUPPORTED_BROKER_SEMANTICS"),
    ],
)
def test_broker_simulation_rejects_cross_zero_and_unsupported_semantics(
    side,
    open_close,
    current,
    quantity,
    code,
):
    with pytest.raises(LifecycleSimulationError) as caught:
        derive_broker_lifecycle_step(
            current_quantity=current,
            side=side,
            open_close=open_close,
            quantity=quantity,
        )
    assert caught.value.code == code


def test_order_that_closes_before_open_is_rejected():
    with pytest.raises(LifecycleSimulationError) as caught:
        derive_broker_lifecycle_step(
            current_quantity="0",
            side="SELL",
            open_close="CLOSE",
            quantity="1",
        )
    assert caught.value.code == "ORPHAN_EVENT"
