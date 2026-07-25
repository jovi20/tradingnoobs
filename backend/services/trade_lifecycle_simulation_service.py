"""Pure lifecycle simulation shared by import previews and canonical writes."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


CANONICAL_ACTIONS = frozenset({"OPEN", "ADD", "REDUCE", "CLOSE"})


class LifecycleSimulationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class LifecycleStep:
    action: str
    direction: str
    pre_quantity: Decimal
    quantity: Decimal
    post_quantity: Decimal

    @property
    def opens_lifecycle(self) -> bool:
        return self.action == "OPEN"

    @property
    def closes_lifecycle(self) -> bool:
        return self.action == "CLOSE"


def _decimal(value: object, *, field: str) -> Decimal:
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as exc:
        raise LifecycleSimulationError(
            "INVALID_QUANTITY",
            f"{field} must be a finite decimal",
        ) from exc
    if not result.is_finite():
        raise LifecycleSimulationError(
            "INVALID_QUANTITY",
            f"{field} must be a finite decimal",
        )
    return result


def _value(value: object) -> str:
    raw = value.value if hasattr(value, "value") else value
    return str(raw).strip().upper()


def simulate_canonical_lifecycle_step(
    *,
    current_quantity: object,
    action: object,
    quantity: object,
    direction: object = "LONG",
) -> LifecycleStep:
    """Apply one canonical action without reading or mutating persistence."""
    current = _decimal(current_quantity, field="current_quantity")
    delta = _decimal(quantity, field="quantity")
    action_value = _value(action)
    direction_value = _value(direction)

    if current < 0 or delta <= 0:
        raise LifecycleSimulationError(
            "INVALID_QUANTITY",
            "Lifecycle quantities must be positive and current quantity cannot be negative",
        )
    if direction_value not in {"LONG", "SHORT"}:
        raise LifecycleSimulationError(
            "UNSUPPORTED_DIRECTION",
            f"Unsupported lifecycle direction: {direction_value}",
        )
    if action_value not in CANONICAL_ACTIONS:
        raise LifecycleSimulationError(
            "UNSUPPORTED_ACTION",
            f"Unsupported lifecycle action: {action_value}",
        )

    if action_value == "OPEN":
        if current != 0:
            raise LifecycleSimulationError(
                "OPEN_CONFLICT",
                "OPEN requires an empty lifecycle",
            )
        post = delta
    elif action_value == "ADD":
        if current <= 0:
            raise LifecycleSimulationError(
                "ORPHAN_EVENT",
                "ADD requires an open lifecycle",
            )
        post = current + delta
    elif action_value == "REDUCE":
        if current <= 0:
            raise LifecycleSimulationError(
                "ORPHAN_EVENT",
                "REDUCE requires an open lifecycle",
            )
        if delta >= current:
            raise LifecycleSimulationError(
                "OVER_REDUCE",
                "REDUCE must leave positive quantity",
            )
        post = current - delta
    else:
        if current <= 0:
            raise LifecycleSimulationError(
                "ORPHAN_EVENT",
                "CLOSE requires an open lifecycle",
            )
        if delta != current:
            raise LifecycleSimulationError(
                "CLOSE_QUANTITY_MISMATCH",
                "CLOSE must consume the full quantity",
            )
        post = Decimal("0")

    return LifecycleStep(
        action=action_value,
        direction=direction_value,
        pre_quantity=current,
        quantity=delta,
        post_quantity=post,
    )


def derive_broker_lifecycle_step(
    *,
    current_quantity: object,
    side: object,
    open_close: object,
    quantity: object,
) -> LifecycleStep:
    """Map broker side/open-close facts to one canonical lifecycle action."""
    side_value = _value(side)
    open_close_value = _value(open_close)
    truth_table = {
        ("BUY", "OPEN"): ("LONG", "OPEN"),
        ("SELL", "CLOSE"): ("LONG", "CLOSE"),
        ("SELL", "OPEN"): ("SHORT", "OPEN"),
        ("BUY", "CLOSE"): ("SHORT", "CLOSE"),
    }
    mapped = truth_table.get((side_value, open_close_value))
    if mapped is None:
        raise LifecycleSimulationError(
            "UNSUPPORTED_BROKER_SEMANTICS",
            f"Unsupported broker side/open-close pair: {side_value}/{open_close_value}",
        )

    direction, intent = mapped
    current = _decimal(current_quantity, field="current_quantity")
    delta = _decimal(quantity, field="quantity")
    if intent == "OPEN":
        action = "OPEN" if current == 0 else "ADD"
    else:
        if current <= 0:
            action = "CLOSE"
        elif delta < current:
            action = "REDUCE"
        else:
            action = "CLOSE"
    return simulate_canonical_lifecycle_step(
        current_quantity=current,
        action=action,
        quantity=delta,
        direction=direction,
    )
