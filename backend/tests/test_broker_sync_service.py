import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import BrokerExecution, IntegrationCredential, User, UserSettings
from services.credential_service import encrypt_secret
from services.broker_sync.service import (
    _normalize_binance_trades,
    _parse_ibkr_flex_executions,
    sync_binance_executions,
)


class BrokerSyncServiceTests(unittest.TestCase):
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
        self.user = User(
            email="sync@example.com",
            email_normalized="sync@example.com",
            hashed_password="hashed",
            public_id="sync-user",
            status="ACTIVE",
            is_active=True,
        )
        self.db.add(self.user)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_parse_ibkr_flex_trade_xml(self):
        xml = """
        <FlexQueryResponse>
          <FlexStatements>
            <FlexStatement accountId="U123">
              <Trades>
                <Trade accountId="U123" symbol="AAPL" buySell="BUY" quantity="10" tradePrice="150.25" dateTime="20260707;09:31:02" ibExecID="0001" orderID="42" currency="USD" ibCommission="1.25" ibCommissionCurrency="USD" />
              </Trades>
            </FlexStatement>
          </FlexStatements>
        </FlexQueryResponse>
        """
        executions = _parse_ibkr_flex_executions(xml, user_id=self.user.id)

        self.assertEqual(len(executions), 1)
        execution = executions[0]
        self.assertEqual(execution.provider, "IBKR")
        self.assertEqual(execution.symbol, "AAPL")
        self.assertEqual(execution.side, "BUY")
        self.assertEqual(str(execution.quantity), "10")
        self.assertEqual(execution.external_trade_id, "0001")

    def test_normalize_binance_spot_trade(self):
        executions = _normalize_binance_trades(
            [
                {
                    "id": 99,
                    "orderId": 1001,
                    "price": "65000.10",
                    "qty": "0.01",
                    "commission": "0.00001",
                    "commissionAsset": "BTC",
                    "time": 1783440000000,
                    "isBuyer": True,
                }
            ],
            user_id=self.user.id,
            market_type="SPOT",
            symbol="btcusdt",
        )

        self.assertEqual(len(executions), 1)
        execution = executions[0]
        self.assertEqual(execution.provider, "BINANCE")
        self.assertEqual(execution.symbol, "BTCUSDT")
        self.assertEqual(execution.side, "BUY")
        self.assertEqual(execution.idempotency_key, f"BINANCE:{self.user.id}:SPOT:BTCUSDT:99")

    def test_binance_sync_persists_new_executions_idempotently(self):
        self.db.add_all(
            [
            UserSettings(
                user_id=self.user.id,
                binance_market_type="SPOT",
                binance_symbols=["BTCUSDT"],
            ),
            IntegrationCredential(
                provider_key="binance",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("api-key"),
            ),
            IntegrationCredential(
                provider_key="binance",
                credential_key="api_secret",
                secret_ciphertext=encrypt_secret("api-secret"),
            ),
            ]
        )
        self.db.commit()

        async def fake_fetch(**kwargs):
            return [
                {
                    "id": 99,
                    "orderId": 1001,
                    "price": "65000.10",
                    "qty": "0.01",
                    "commission": "0.00001",
                    "commissionAsset": "BTC",
                    "time": 1783440000000,
                    "isBuyer": True,
                }
            ]

        with patch("services.broker_sync.service._fetch_binance_account_trades", fake_fetch):
            first_run = __import__("asyncio").run(
                sync_binance_executions(self.db, self.user, start_date=date(2026, 7, 1))
            )
            second_run = __import__("asyncio").run(
                sync_binance_executions(self.db, self.user, start_date=date(2026, 7, 1))
            )

        self.assertEqual(first_run.records_inserted, 1)
        self.assertEqual(first_run.records_skipped, 0)
        self.assertEqual(second_run.records_inserted, 0)
        self.assertEqual(second_run.records_skipped, 1)
        self.assertEqual(self.db.query(BrokerExecution).count(), 1)


if __name__ == "__main__":
    unittest.main()
