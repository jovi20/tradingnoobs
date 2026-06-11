import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AssetMaster,
    DailySnapshot,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    User,
)

try:
    from services.risk_alert_service import build_portfolio_risk_summary
except Exception as exc:  # pragma: no cover - exercised as the expected RED state.
    build_portfolio_risk_summary = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class RiskAlertServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.account_counter = 0
        self.user = self._create_user("risk@example.com")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _require_service(self):
        if IMPORT_ERROR:
            self.fail(f"risk alert service is unavailable: {IMPORT_ERROR}")

    def _create_user(self, email: str) -> User:
        user = User(
            email=email,
            email_normalized=email,
            hashed_password="hashed",
            public_id=f"user-{email}",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_account(self) -> TradingAccount:
        self.account_counter += 1
        account = TradingAccount(
            user_id=self.user.id,
            public_id=f"risk-account-public-id-{self.account_counter}",
            name="Risk Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def _create_instrument(self, symbol: str) -> TradeInstrument:
        asset = AssetMaster(
            canonical_code=symbol,
            display_symbol=symbol,
            name=f"{symbol} Inc.",
            asset_type="STOCK",
            quote_currency="USD",
            status="ACTIVE",
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.SPOT,
            display_name=f"{symbol} Spot",
            contract_symbol=symbol,
            status="ACTIVE",
        )
        self.db.add(instrument)
        self.db.commit()
        self.db.refresh(instrument)
        return instrument

    def _create_open_position(self, symbol: str, quantity: str, avg_price: str) -> TradingPosition:
        account = self._create_account()
        instrument = self._create_instrument(symbol)
        position = TradingPosition(
            user_id=self.user.id,
            account_id=account.id,
            instrument_id=instrument.id,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 6, 1, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            quantity_opened=Decimal(quantity),
            quantity_closed=Decimal("0"),
            avg_open_price=Decimal(avg_price),
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        return position

    def _add_snapshot(self, snapshot_date: date, total_equity: str, total_assets: str | None = None) -> None:
        self.db.add(
            DailySnapshot(
                user_id=self.user.id,
                date=snapshot_date,
                total_equity=Decimal(total_equity),
                total_assets=Decimal(total_assets or total_equity),
                total_liabilities=Decimal("0"),
                net_transfers=Decimal("0"),
            )
        )
        self.db.commit()

    def test_daily_loss_warning_crosses_three_percent_threshold(self):
        self._require_service()
        self._add_snapshot(date(2026, 6, 10), "100000")
        self._add_snapshot(date(2026, 6, 11), "96500")

        summary = build_portfolio_risk_summary(
            self.db,
            self.user.id,
            as_of=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        )

        daily_alerts = [alert for alert in summary["alerts"] if alert["kind"] == "DAILY_LOSS_LIMIT"]
        self.assertEqual(len(daily_alerts), 1)
        self.assertEqual(daily_alerts[0]["severity"], "WARNING")
        self.assertEqual(summary["portfolio"]["daily_pnl"], -3500.0)
        self.assertEqual(summary["portfolio"]["daily_pnl_percent"], -3.5)

    def test_daily_loss_critical_crosses_five_percent_threshold(self):
        self._require_service()
        self._add_snapshot(date(2026, 6, 10), "100000")
        self._add_snapshot(date(2026, 6, 11), "94000")

        summary = build_portfolio_risk_summary(
            self.db,
            self.user.id,
            as_of=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        )

        daily_alert = next(alert for alert in summary["alerts"] if alert["kind"] == "DAILY_LOSS_LIMIT")
        self.assertEqual(daily_alert["severity"], "CRITICAL")
        self.assertIn("Daily equity change crossed the -5% critical threshold.", daily_alert["reason"])

    def test_symbol_concentration_alert_uses_gross_exposure(self):
        self._require_service()
        self._create_open_position("MSFT", "400", "100")
        self._create_open_position("AAPL", "600", "100")

        summary = build_portfolio_risk_summary(
            self.db,
            self.user.id,
            as_of=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        )

        concentration_alert = next(alert for alert in summary["alerts"] if alert["kind"] == "CONCENTRATION")
        self.assertEqual(concentration_alert["severity"], "CRITICAL")
        self.assertIn("AAPL", concentration_alert["summary"])
        self.assertEqual(summary["portfolio"]["gross_exposure"], 100000.0)

    def test_no_alerts_for_empty_portfolio_returns_fresh_empty_summary(self):
        self._require_service()

        summary = build_portfolio_risk_summary(
            self.db,
            self.user.id,
            as_of=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(summary["alerts"], [])
        self.assertEqual(summary["portfolio"]["gross_exposure"], 0.0)
        self.assertEqual(summary["portfolio"]["net_liquidation_value"], 0.0)
        self.assertEqual(summary["trust"]["freshness"], "FRESH")
        self.assertIn("TradingPosition", summary["trust"]["source_refs"])


if __name__ == "__main__":
    unittest.main()
