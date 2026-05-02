import unittest
from datetime import datetime, timezone
from decimal import Decimal

from models import BatchType, Position, PositionDirection, PositionStatus, TradeBatch
from routers.positions import recalculate_position


class PositionAccountingRecalculationTests(unittest.TestCase):
    def test_recalculate_position_uses_fifo_for_exit_pnl_and_remaining_cost_basis(self):
        position = Position(
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("0"),
            average_entry_price=Decimal("0"),
            realized_pnl=Decimal("0"),
        )
        position.batches = [
            TradeBatch(
                type=BatchType.ENTRY,
                price=Decimal("100"),
                quantity=Decimal("10"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            ),
            TradeBatch(
                type=BatchType.ENTRY,
                price=Decimal("200"),
                quantity=Decimal("10"),
                time=datetime(2026, 4, 2, 9, 30, tzinfo=timezone.utc),
            ),
            TradeBatch(
                type=BatchType.EXIT,
                price=Decimal("150"),
                quantity=Decimal("10"),
                time=datetime(2026, 4, 3, 9, 30, tzinfo=timezone.utc),
            ),
        ]

        recalculate_position(position, db=None)

        self.assertEqual(position.total_quantity, Decimal("10"))
        self.assertEqual(position.average_entry_price, Decimal("200"))
        self.assertEqual(position.realized_pnl, Decimal("500"))
        self.assertEqual(position.batches[2].pnl, Decimal("500"))
        self.assertEqual(position.status, PositionStatus.OPEN)


if __name__ == "__main__":
    unittest.main()
