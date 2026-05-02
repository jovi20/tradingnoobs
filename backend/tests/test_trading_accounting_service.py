import unittest
from decimal import Decimal


try:
    from services.trading_accounting_service import (
        AccountingEvent,
        calculate_fifo_position_accounting,
        calculate_mark_to_market_position,
    )
except Exception as exc:  # pragma: no cover - exercised as a TDD red state before the service exists.
    AccountingEvent = None
    calculate_fifo_position_accounting = None
    calculate_mark_to_market_position = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class TradingAccountingServiceTests(unittest.TestCase):
    def test_fifo_long_position_calculates_realized_pnl_and_fees(self):
        if IMPORT_ERROR:
            self.fail(f"trading accounting service is unavailable: {IMPORT_ERROR}")

        summary = calculate_fifo_position_accounting(
            [
                AccountingEvent(
                    public_id="open-1",
                    event_type="OPEN",
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                    fee_amount=Decimal("1"),
                ),
                AccountingEvent(
                    public_id="add-1",
                    event_type="ADD",
                    quantity=Decimal("5"),
                    price=Decimal("120"),
                    fee_amount=Decimal("1"),
                ),
                AccountingEvent(
                    public_id="reduce-1",
                    event_type="REDUCE",
                    quantity=Decimal("12"),
                    price=Decimal("130"),
                    fee_amount=Decimal("2"),
                ),
                AccountingEvent(
                    public_id="close-1",
                    event_type="CLOSE",
                    quantity=Decimal("3"),
                    price=Decimal("90"),
                    fee_amount=Decimal("1"),
                ),
            ],
            side="LONG",
        )

        self.assertEqual(summary.quantity_opened, Decimal("15"))
        self.assertEqual(summary.quantity_closed, Decimal("15"))
        self.assertEqual(summary.open_quantity, Decimal("0"))
        self.assertEqual(summary.avg_open_price.quantize(Decimal("0.0001")), Decimal("106.6667"))
        self.assertEqual(summary.avg_close_price, Decimal("122"))
        self.assertEqual(summary.realized_pnl_gross, Decimal("230"))
        self.assertEqual(summary.total_fees, Decimal("5"))
        self.assertEqual(summary.realized_pnl_net, Decimal("225"))
        self.assertEqual(summary.event_results["reduce-1"].realized_pnl_gross, Decimal("320"))
        self.assertEqual(summary.event_results["close-1"].realized_pnl_gross, Decimal("-90"))

    def test_fifo_short_position_reverses_pnl_direction(self):
        if IMPORT_ERROR:
            self.fail(f"trading accounting service is unavailable: {IMPORT_ERROR}")

        summary = calculate_fifo_position_accounting(
            [
                AccountingEvent(
                    public_id="open-short",
                    event_type="OPEN",
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                ),
                AccountingEvent(
                    public_id="close-short",
                    event_type="CLOSE",
                    quantity=Decimal("10"),
                    price=Decimal("80"),
                ),
            ],
            side="SHORT",
        )

        self.assertEqual(summary.realized_pnl_gross, Decimal("200"))
        self.assertEqual(summary.realized_pnl_net, Decimal("200"))

    def test_mark_to_market_position_calculates_long_unrealized_value_with_fx(self):
        if IMPORT_ERROR:
            self.fail(f"trading accounting service is unavailable: {IMPORT_ERROR}")

        result = calculate_mark_to_market_position(
            open_quantity=Decimal("10"),
            avg_open_price=Decimal("100"),
            current_price=Decimal("120"),
            side="LONG",
            fx_rate_to_display_ccy=Decimal("1.5"),
        )

        self.assertEqual(result.market_value, Decimal("1800.0"))
        self.assertEqual(result.signed_market_value, Decimal("1800.0"))
        self.assertEqual(result.unrealized_pnl, Decimal("300.0"))
        self.assertEqual(result.change_percent, Decimal("20.0"))

    def test_mark_to_market_position_reverses_short_unrealized_direction(self):
        if IMPORT_ERROR:
            self.fail(f"trading accounting service is unavailable: {IMPORT_ERROR}")

        result = calculate_mark_to_market_position(
            open_quantity=Decimal("10"),
            avg_open_price=Decimal("100"),
            current_price=Decimal("80"),
            side="SHORT",
        )

        self.assertEqual(result.market_value, Decimal("800"))
        self.assertEqual(result.signed_market_value, Decimal("-800"))
        self.assertEqual(result.unrealized_pnl, Decimal("200"))
        self.assertEqual(result.change_percent, Decimal("20.0"))


if __name__ == "__main__":
    unittest.main()
