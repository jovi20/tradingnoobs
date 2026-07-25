import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from decimal import Decimal
import sys
import types

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=lambda *args, **kwargs: object()))
sys.modules.setdefault("pandas", types.SimpleNamespace(DataFrame=object))
sys.modules.setdefault("numpy", types.SimpleNamespace())
sys.modules.setdefault("binance", types.SimpleNamespace())
sys.modules.setdefault("binance.spot", types.SimpleNamespace(Spot=lambda *args, **kwargs: object()))

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    LedgerPostingKind,
    AssetMetadata,
    BatchType,
    IdempotencyKey,
    OutboxEvent,
    OutboxEventStatus,
    Position,
    PositionEvent,
    PositionEventType,
    PositionDirection,
    PositionStatus,
    TradeBatch,
    TradingAccount,
    TradingPosition,
    TradingPositionStatus,
    InsightArtifact,
    InsightRun,
    User,
)
from services.auth_service import get_current_user
from services.legacy_truth_sync_service import (
    sync_legacy_position_to_truth,
    validate_legacy_instrument_identity,
)
from services.trading_position_write_service import (
    ArchivedTradingPositionWriteError,
    append_truth_trade_event,
    reverse_latest_truth_trade_event,
)


class TradingPositionLifecycleRouterTests(unittest.TestCase):
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
            email="lifecycle@example.com",
            email_normalized="lifecycle@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _expected_identity(self, position: Position):
        metadata = position.asset_metadata
        return validate_legacy_instrument_identity(
            position_asset_type=position.asset_type,
            account_currency=position.trading_account.currency,
            symbol=position.symbol,
            exchange_code=position.exchange,
            metadata_core_type=metadata.core_type if metadata else None,
            metadata_market=metadata.market if metadata else None,
            metadata_currency=metadata.currency if metadata else None,
            metadata_instrument=metadata.instrument if metadata else None,
        )

    def _seed_synced_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="AAPL",
            name="Apple Inc.",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        legacy_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-position",
            symbol="AAPL",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=Decimal("0"),
            average_entry_price=Decimal("185"),
            realized_pnl=Decimal("180"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
            trade_review="Held plan well.",
            checklist_responses={"pre_market": True, "risk_check": False},
            asset_metadata_symbol="AAPL",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add_all([
            TradeBatch(
                public_id="batch-open",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial breakout entry",
                emotion="Confident",
                confidence=4,
            ),
            TradeBatch(
                public_id="batch-add",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("190"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
                reason="Added on continuation",
                emotion="Focused",
                confidence=4,
            ),
            TradeBatch(
                public_id="batch-close",
                position_id=legacy_position.id,
                type=BatchType.EXIT,
                price=Decimal("203"),
                quantity=Decimal("10"),
                time=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
                reason="Take profit",
                emotion="Calm",
                confidence=5,
                pnl=Decimal("180"),
            ),
        ])
        self.db.commit()

        return sync_legacy_position_to_truth(
            self.db,
            legacy_position.id,
            expected_identity=self._expected_identity(legacy_position),
        )

    def _seed_open_synced_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-open-public-id",
            name="IBKR Open",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="MSFT",
            name="Microsoft",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        legacy_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-open-position",
            symbol="MSFT",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("5"),
            average_entry_price=Decimal("180"),
            realized_pnl=Decimal("0"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            trade_review="",
            checklist_responses={"pre_market": True},
            asset_metadata_symbol="MSFT",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add(
            TradeBatch(
                public_id="batch-open-msft",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial trend entry",
                emotion="Prepared",
                confidence=4,
            )
        )
        self.db.commit()

        return sync_legacy_position_to_truth(
            self.db,
            legacy_position.id,
            expected_identity=self._expected_identity(legacy_position),
        )

    def test_lifecycle_route_returns_position_summary_and_thread(self):
        truth_position = self._seed_synced_position()

        response = self.client.get(f"/api/trading-positions/{truth_position.public_id}/lifecycle")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["position_summary"]["public_id"], truth_position.public_id)
        self.assertEqual(payload["data"]["position_summary"]["status"], "CLOSED")
        self.assertEqual(payload["data"]["position_summary"]["pnl_basis"]["cost_basis_method"], "FIFO")
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "ADD", "CLOSE"])
        self.assertEqual(payload["data"]["thesis_block"]["thesis"], "Initial breakout entry")
        cash_effects = payload["data"]["ledger_summary"]["cash_effects"]
        self.assertEqual(len(cash_effects), 1)
        self.assertEqual(cash_effects[0]["entry_type"], "REALIZED_PNL")
        self.assertEqual(float(cash_effects[0]["amount"]), 180.0)
        self.assertEqual(cash_effects[0]["currency"], "USD")

    def test_invalid_canonical_quantities_fail_closed_across_legacy_reads_lifecycle_and_writes(self):
        truth_position = self._seed_open_synced_position()
        legacy_position = self.db.query(Position).filter(
            Position.public_id == "legacy-open-position"
        ).one()
        legacy_snapshot = (
            legacy_position.status,
            legacy_position.total_quantity,
            legacy_position.average_entry_price,
            legacy_position.realized_pnl,
            legacy_position.closed_at,
        )
        baseline_counts = {
            model: self.db.query(model).count()
            for model in (PositionEvent, AccountLedgerEntry, IdempotencyKey, OutboxEvent)
        }
        invalid_accounting_cases = (
            ("null-opened", None, Decimal("0"), TradingPositionStatus.CLOSED),
            ("null-closed", Decimal("5"), None, TradingPositionStatus.OPEN),
            ("negative-opened", Decimal("-1"), Decimal("0"), TradingPositionStatus.OPEN),
            ("negative-closed", Decimal("5"), Decimal("-1"), TradingPositionStatus.OPEN),
            ("nonfinite-opened", Decimal("Infinity"), Decimal("0"), TradingPositionStatus.OPEN),
            ("nonfinite-closed", Decimal("5"), Decimal("Infinity"), TradingPositionStatus.CLOSED),
            ("closed-exceeds-opened", Decimal("5"), Decimal("6"), TradingPositionStatus.CLOSED),
            ("open-with-zero-remaining", Decimal("5"), Decimal("5"), TradingPositionStatus.OPEN),
            ("closed-with-remaining", Decimal("5"), Decimal("4"), TradingPositionStatus.CLOSED),
        )

        for case_name, quantity_opened, quantity_closed, position_status in invalid_accounting_cases:
            with self.subTest(case=case_name):
                truth_position.quantity_opened = quantity_opened
                truth_position.quantity_closed = quantity_closed
                truth_position.status = position_status
                self.db.commit()

                responses = (
                    self.client.get("/api/positions"),
                    self.client.get("/api/positions?status=OPEN"),
                    self.client.get("/api/positions?status=CLOSED"),
                    self.client.get("/api/positions/legacy-open-position"),
                    self.client.get(
                        f"/api/trading-positions/{truth_position.public_id}/lifecycle"
                    ),
                    self.client.get("/api/positions/legacy-open-position/truth-lifecycle"),
                    self.client.post(
                        f"/api/trading-positions/{truth_position.public_id}/events",
                        headers={"Idempotency-Key": f"invalid-canonical-{case_name}"},
                        json={
                            "event_type": "ADD",
                            "quantity": "1",
                            "price": "190",
                            "currency": "USD",
                            "occurred_at": "2026-04-03T15:30:00+00:00",
                        },
                    ),
                )

                for response in responses:
                    self.assertEqual(response.status_code, 409, response.text)
                    self.assertEqual(
                        response.json()["detail"]["code"],
                        "CANONICAL_ACCOUNTING_UNRESOLVED",
                    )
                    self.assertEqual(
                        response.json()["detail"]["position_public_id"],
                        truth_position.public_id,
                    )

                self.db.expire_all()
                for model, baseline_count in baseline_counts.items():
                    self.assertEqual(
                        self.db.query(model).count(),
                        baseline_count,
                        f"{case_name} changed {model.__tablename__}",
                    )
                persisted_legacy = self.db.query(Position).filter(
                    Position.public_id == "legacy-open-position"
                ).one()
                self.assertEqual(
                    (
                        persisted_legacy.status,
                        persisted_legacy.total_quantity,
                        persisted_legacy.average_entry_price,
                        persisted_legacy.realized_pnl,
                        persisted_legacy.closed_at,
                    ),
                    legacy_snapshot,
                )
                truth_position = self.db.query(TradingPosition).filter_by(
                    public_id=truth_position.public_id
                ).one()

    def test_archived_position_is_readable_but_all_financial_writes_fail_closed(self):
        truth_position = self._seed_synced_position()
        truth_position.status = TradingPositionStatus.ARCHIVED
        self.db.commit()

        canonical_lifecycle = self.client.get(
            f"/api/trading-positions/{truth_position.public_id}/lifecycle"
        )
        legacy_lifecycle = self.client.get("/api/positions/legacy-position/truth-lifecycle")
        legacy_detail = self.client.get("/api/positions/legacy-position")
        self.assertEqual(canonical_lifecycle.status_code, 200, canonical_lifecycle.text)
        self.assertEqual(
            canonical_lifecycle.json()["data"]["position_summary"]["status"],
            "ARCHIVED",
        )
        self.assertEqual(
            canonical_lifecycle.json()["data"]["review_status"],
            "CLOSED_PENDING_REVIEW",
        )
        self.assertEqual(legacy_lifecycle.status_code, 200, legacy_lifecycle.text)
        self.assertEqual(legacy_detail.status_code, 200, legacy_detail.text)
        self.assertEqual(legacy_detail.json()["status"], "CLOSED")
        self.assertEqual(Decimal(legacy_detail.json()["total_quantity"]), Decimal("0"))

        self.db.expire_all()
        truth_position = self.db.query(TradingPosition).filter_by(
            public_id=truth_position.public_id
        ).one()
        close_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.CLOSE,
        ).one()
        legacy_position = self.db.query(Position).filter(
            Position.public_id == "legacy-position"
        ).one()
        legacy_snapshot = (
            legacy_position.status,
            legacy_position.total_quantity,
            legacy_position.average_entry_price,
            legacy_position.realized_pnl,
            legacy_position.closed_at,
        )
        baseline_counts = {
            model: self.db.query(model).count()
            for model in (PositionEvent, AccountLedgerEntry, IdempotencyKey, OutboxEvent)
        }

        financial_write_responses = []
        for event_type in ("ADD", "REDUCE", "CLOSE"):
            financial_write_responses.append(
                self.client.post(
                    f"/api/trading-positions/{truth_position.public_id}/events",
                    headers={"Idempotency-Key": f"archived-{event_type.lower()}"},
                    json={
                        "event_type": event_type,
                        "quantity": "1",
                        "price": "205",
                        "currency": "USD",
                        "occurred_at": "2026-04-06T15:30:00+00:00",
                    },
                )
            )
        financial_write_responses.extend(
            (
                self.client.post(
                    f"/api/trading-positions/{truth_position.public_id}/events/{close_event.public_id}/reverse",
                    json={"occurred_at": "2026-04-06T16:00:00+00:00"},
                ),
                self.client.post(
                    f"/api/trading-positions/{truth_position.public_id}/dividends",
                    headers={"Idempotency-Key": "archived-dividend"},
                    json={
                        "amount": "25",
                        "currency": "USD",
                        "occurred_at": "2026-04-06T16:00:00+00:00",
                    },
                ),
            )
        )

        for response in financial_write_responses:
            self.assertEqual(response.status_code, 409, response.text)
            self.assertEqual(response.json()["detail"]["code"], "POSITION_ARCHIVED")
            self.assertEqual(
                response.json()["detail"]["position_public_id"],
                truth_position.public_id,
            )

        with self.assertRaises(ArchivedTradingPositionWriteError):
            append_truth_trade_event(
                self.db,
                position=truth_position,
                event_type=PositionEventType.ADD,
                quantity=Decimal("1"),
                price=Decimal("205"),
                currency="USD",
                occurred_at=datetime(2026, 4, 6, 17, 0, tzinfo=timezone.utc),
            )
        with self.assertRaises(ArchivedTradingPositionWriteError):
            reverse_latest_truth_trade_event(
                self.db,
                position=truth_position,
                event=close_event,
                occurred_at=datetime(2026, 4, 6, 17, 0, tzinfo=timezone.utc),
            )

        self.db.expire_all()
        for model, baseline_count in baseline_counts.items():
            self.assertEqual(self.db.query(model).count(), baseline_count)
        persisted_truth = self.db.query(TradingPosition).filter_by(
            public_id=truth_position.public_id
        ).one()
        self.assertEqual(persisted_truth.status, TradingPositionStatus.ARCHIVED)
        persisted_legacy = self.db.query(Position).filter(
            Position.public_id == "legacy-position"
        ).one()
        self.assertEqual(
            (
                persisted_legacy.status,
                persisted_legacy.total_quantity,
                persisted_legacy.average_entry_price,
                persisted_legacy.realized_pnl,
                persisted_legacy.closed_at,
            ),
            legacy_snapshot,
        )

    def test_lifecycle_route_only_loads_ai_sidecar_with_effective_capability(self):
        truth_position = self._seed_synced_position()
        run = InsightRun(
            user_id=self.user.id,
            run_type="analysis.position_review",
            status="COMPLETED",
            prompt_version="v1",
            input_refs=[truth_position.public_id],
            started_at=datetime(2026, 4, 6, 9, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 4, 6, 9, 1, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        artifact = InsightArtifact(
            insight_run_id=run.id,
            artifact_type="position_review",
            title="Position review artifact",
            summary="The add was disciplined but the final exit still violated pace.",
            content_markdown=None,
            payload={"linked_object_public_id": truth_position.public_id},
            evidence_refs=["analysis:position_review", "dataset:positions"],
            trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": [truth_position.public_id]},
        )
        self.db.add(artifact)
        self.db.commit()

        with patch(
            "services.trading_position_read_service._build_ai_sidecar_items"
        ) as build_ai_sidecar:
            disabled_response = self.client.get(
                f"/api/trading-positions/{truth_position.public_id}/lifecycle"
            )

        self.assertEqual(disabled_response.status_code, 200)
        self.assertEqual(disabled_response.json()["data"]["ai_sidecar"]["items"], [])
        build_ai_sidecar.assert_not_called()

        with patch(
            "routers.trading_positions.is_effective_capability_enabled",
            return_value=True,
        ):
            response = self.client.get(
                f"/api/trading-positions/{truth_position.public_id}/lifecycle"
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["ai_sidecar"]["items"][0]["insight_artifact_public_id"], artifact.public_id)
        self.assertEqual(payload["data"]["ai_sidecar"]["items"][0]["title"], "Position review artifact")
        self.assertEqual(payload["data"]["ai_sidecar"]["items"][0]["href"], f"/insights/{artifact.public_id}")
        self.assertEqual(len(payload["data"]["ai_sidecar"]["items"][0]["evidence_refs"]), 2)
        self.assertEqual(
            payload["data"]["ai_sidecar"]["items"][0]["evidence_refs"][0]["href"],
            f"/insights/{artifact.public_id}",
        )

    def test_lifecycle_route_rejects_internal_numeric_id(self):
        truth_position = self._seed_synced_position()

        response = self.client.get(f"/api/trading-positions/{truth_position.id}/lifecycle")

        self.assertEqual(response.status_code, 404)

    def test_event_narrative_patch_updates_truth_event_and_returns_lifecycle(self):
        truth_position = self._seed_synced_position()
        opening_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.patch(
            f"/api/trading-positions/{truth_position.public_id}/events/{opening_event.public_id}",
            json={
                "reason": "Updated breakout thesis",
                "emotion": "Focused",
                "confidence": 5,
                "thesis": "Breakout continuation after earnings reset",
                "invalidation_rule": "Lose prior day low",
                "planned_exit_rule": "Scale out above 2R",
                "sizing_rationale": "Half risk until confirmation",
                "checklist_snapshot": {"pre_market": True, "risk_check": True},
                "note": "Narrative-only truth event update.",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(payload["data"]["position_summary"]["public_id"], truth_position.public_id)
        self.assertEqual(payload["data"]["thesis_block"]["thesis"], "Breakout continuation after earnings reset")
        self.assertEqual(payload["data"]["thesis_block"]["invalidation_rule"], "Lose prior day low")
        self.assertEqual(payload["data"]["thesis_block"]["planned_exit_rule"], "Scale out above 2R")
        self.assertEqual(payload["data"]["thesis_block"]["sizing_rationale"], "Half risk until confirmation")
        checklist = payload["data"]["thesis_block"]["checklist_snapshot"]
        self.assertEqual(checklist, [
            {"label": "pre_market", "checked": True},
            {"label": "risk_check", "checked": True},
        ])
        first_node = payload["data"]["lifecycle_thread"]["nodes"][0]
        self.assertEqual(first_node["node_public_id"], opening_event.public_id)
        self.assertEqual(first_node["summary"], "Updated breakout thesis")
        self.assertEqual(first_node["emotion"], "Focused")
        self.assertEqual(first_node["confidence"], 5)

        self.db.expire_all()
        persisted = self.db.query(PositionEvent).filter(PositionEvent.id == opening_event.id).one()
        self.assertEqual(persisted.reason, "Updated breakout thesis")
        self.assertEqual(persisted.thesis, "Breakout continuation after earnings reset")
        self.assertEqual(persisted.checklist_snapshot, {"pre_market": True, "risk_check": True})

    def test_event_narrative_patch_rejects_internal_event_id(self):
        truth_position = self._seed_synced_position()
        opening_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.patch(
            f"/api/trading-positions/{truth_position.public_id}/events/{opening_event.id}",
            json={"reason": "Should not accept numeric ids"},
        )

        self.assertEqual(response.status_code, 404)

    def test_dividend_event_write_creates_truth_event_and_ledger_entry(self):
        truth_position = self._seed_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json={
                "amount": "12.50",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Quarterly dividend",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["ledger_summary"]["total_dividends"])), Decimal("12.5"))

        dividend_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.DIVIDEND,
        ).one()
        self.assertEqual(dividend_event.gross_amount, Decimal("12.50000000"))
        self.assertEqual(dividend_event.note, "Quarterly dividend")

        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == dividend_event.id,
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.DIVIDEND)
        self.assertEqual(ledger_entry.amount, Decimal("12.50000000"))
        self.assertEqual(ledger_entry.currency, "USD")

    def test_dividend_event_write_rejects_foreign_currency_without_side_effects(self):
        truth_position = self._seed_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json={
                "amount": "100",
                "currency": "HKD",
                "fx_rate_to_account_ccy": "0.128",
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "HKD dividend",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.DIVIDEND,
            ).count(),
            0,
        )

    def test_dividend_write_replays_completed_idempotency_key_without_duplicate_ledger(self):
        truth_position = self._seed_synced_position()
        request_body = {
            "amount": "12.50",
            "currency": "USD",
            "occurred_at": "2026-04-04T12:00:00+00:00",
            "note": "Quarterly dividend",
        }
        headers = {"Idempotency-Key": "dividend-retry-1"}

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json=request_body,
            headers=headers,
        )
        second_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json=request_body,
            headers=headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json(), first_response.json())

        self.db.expire_all()
        dividend_events = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.DIVIDEND,
        ).all()
        self.assertEqual(len(dividend_events), 1)
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(
                AccountLedgerEntry.position_id == truth_position.id,
                AccountLedgerEntry.entry_type == AccountLedgerEntryType.DIVIDEND,
            ).count(),
            1,
        )
        idempotency_record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "trading_position.dividend.create",
        ).one()
        self.assertEqual(idempotency_record.status, "COMPLETED")

    def test_dividend_write_rejects_idempotency_key_reuse_with_different_payload(self):
        truth_position = self._seed_synced_position()
        headers = {"Idempotency-Key": "dividend-conflict-1"}

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json={
                "amount": "12.50",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
            },
            headers=headers,
        )
        conflict_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json={
                "amount": "13.00",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
            },
            headers=headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(conflict_response.status_code, 409)
        self.assertEqual(conflict_response.json()["detail"], "Idempotency key reuse with a different request payload.")
        self.db.expire_all()
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.DIVIDEND,
            ).count(),
            1,
        )

    def test_manual_adjustment_endpoint_is_disabled_without_side_effects(self):
        truth_position = self._seed_open_synced_position()

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/adjustments",
            json={
                "amount": "-7.25",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Broker cash correction",
            },
            headers={"Idempotency-Key": "disabled-adjustment"},
        )
        second_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/adjustments",
            json={
                "amount": "100",
                "currency": "HKD",
                "fx_rate_to_account_ccy": "0.128",
                "occurred_at": "2026-04-04T12:00:00+00:00",
            },
        )

        self.assertEqual(first_response.status_code, 422)
        self.assertEqual(second_response.status_code, 422)
        self.assertEqual(
            first_response.json()["detail"]["code"],
            "UNSUPPORTED_EVENT_TYPE",
        )
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.MANUAL_ADJUSTMENT,
            ).count(),
            0,
        )
        self.assertEqual(self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_id == truth_position.id,
            AccountLedgerEntry.entry_type == AccountLedgerEntryType.CASH_ADJUSTMENT,
        ).count(), 0)
        self.assertEqual(self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "trading_position.manual_adjustment.create",
        ).count(), 0)

    def test_disabled_event_types_are_rejected_by_direct_api_without_side_effects(self):
        truth_position = self._seed_open_synced_position()
        disabled_event_types = (
            "TRANSFER_IN",
            "TRANSFER_OUT",
            "STOCK_SPLIT",
            "OPTION_EXERCISE",
            "OPTION_ASSIGNMENT",
            "OPTION_EXPIRY",
            "FEE",
            "MANUAL_ADJUSTMENT",
            "CASH_ADJUSTMENT",
            "SEPARATE_FEE_EVENT",
        )
        baseline_counts = {
            PositionEvent: self.db.query(PositionEvent).count(),
            AccountLedgerEntry: self.db.query(AccountLedgerEntry).count(),
            IdempotencyKey: self.db.query(IdempotencyKey).count(),
            OutboxEvent: self.db.query(OutboxEvent).count(),
        }

        for event_type in disabled_event_types:
            with self.subTest(event_type=event_type):
                response = self.client.post(
                    f"/api/trading-positions/{truth_position.public_id}/events",
                    json={
                        "event_type": event_type,
                        "quantity": "1",
                        "price": "210",
                        "currency": "USD",
                        "occurred_at": "2026-04-03T15:30:00+00:00",
                    },
                    headers={"Idempotency-Key": f"disabled-{event_type.lower()}"},
                )

                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "VALIDATION_REQUEST_INVALID",
                )
                for model, baseline_count in baseline_counts.items():
                    self.assertEqual(
                        self.db.query(model).count(),
                        baseline_count,
                        f"{event_type} changed {model.__tablename__}",
                    )

    def test_trade_event_rejects_foreign_currency_before_idempotency_or_outbox(self):
        truth_position = self._seed_open_synced_position()
        before_outbox = self.db.query(OutboxEvent).count()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "1",
                "price": "210",
                "currency": "USD",
                "fee_amount": "1",
                "fee_currency": "USDT",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
            headers={"Idempotency-Key": "foreign-fee"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.REDUCE,
            ).count(),
            0,
        )
        self.assertEqual(self.db.query(OutboxEvent).count(), before_outbox)
        self.assertEqual(
            self.db.query(IdempotencyKey).filter(
                IdempotencyKey.scope == "trading_position.trade_event.create",
            ).count(),
            0,
        )

    def test_trade_event_write_replays_fifo_and_creates_realized_pnl_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Scale out into strength",
                "emotion": "Calm",
                "confidence": 5,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("60"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("59"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["total_fees"])), Decimal("1"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "REDUCE"])

        self.db.expire_all()
        trade_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()
        self.assertEqual(trade_event.quantity, Decimal("2.00000000"))
        self.assertEqual(trade_event.price, Decimal("210.00000000"))
        self.assertEqual(trade_event.fee_amount, Decimal("1.00000000"))
        self.assertEqual(trade_event.realized_pnl_gross, Decimal("60.00000000"))
        self.assertEqual(trade_event.realized_pnl_net, Decimal("59.00000000"))

        ledger_entries = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == trade_event.id,
        ).order_by(AccountLedgerEntry.id.asc()).all()
        self.assertEqual(
            [(entry.posting_kind, entry.amount) for entry in ledger_entries],
            [
                (LedgerPostingKind.REALIZED_GROSS.value, Decimal("60.00000000")),
                (LedgerPostingKind.TRADE_FEE.value, Decimal("-1.00000000")),
            ],
        )
        self.assertTrue(all(entry.currency == "USD" for entry in ledger_entries))
        outbox_event = self.db.query(OutboxEvent).filter(
            OutboxEvent.aggregate_type == "TradingPosition",
            OutboxEvent.aggregate_public_id == truth_position.public_id,
            OutboxEvent.event_type == "truth.position_event.created",
        ).one()
        self.assertEqual(outbox_event.status, OutboxEventStatus.PENDING)
        self.assertEqual(outbox_event.queue_name, "derived")
        self.assertEqual(outbox_event.dedupe_key, f"truth.position_event.created:{trade_event.public_id}")
        self.assertEqual(outbox_event.payload["position_event_public_id"], trade_event.public_id)
        self.assertEqual(outbox_event.payload["position_event_type"], "REDUCE")

    def test_trade_event_write_add_replays_fifo_without_cash_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "3",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "reason": "Add on continuation",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("0"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("0"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "ADD"])

        self.db.expire_all()
        add_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.ADD,
        ).one()
        self.assertEqual(add_event.quantity, Decimal("3.00000000"))
        self.assertEqual(add_event.price, Decimal("190.00000000"))
        self.assertEqual(add_event.realized_pnl_gross, Decimal("0E-8"))
        self.assertEqual(add_event.realized_pnl_net, Decimal("0E-8"))
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(AccountLedgerEntry.position_event_id == add_event.id).count(),
            0,
        )

        legacy_projection = self.db.query(Position).filter(
            Position.public_id == "legacy-open-position"
        ).one()
        self.assertEqual(legacy_projection.total_quantity, Decimal("8.00000000"))
        self.assertEqual(
            legacy_projection.average_entry_price.quantize(Decimal("0.0001")),
            Decimal("183.7500"),
        )
        self.assertEqual(legacy_projection.status, PositionStatus.OPEN)

    def test_trade_event_write_replays_completed_idempotency_key_without_duplicate_event(self):
        truth_position = self._seed_open_synced_position()
        request_body = {
            "event_type": "ADD",
            "quantity": "3",
            "price": "190",
            "currency": "USD",
            "occurred_at": "2026-04-03T15:30:00+00:00",
            "reason": "Add on continuation",
        }
        headers = {"Idempotency-Key": "truth-add-retry-1"}

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json=request_body,
            headers=headers,
        )
        self.db.expire_all()
        idempotency_record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "trading_position.trade_event.create",
        ).one()
        historical_response = first_response.json()
        historical_response["data"]["ai_sidecar"]["items"] = [
            {"conclusion": "historical-ai-secret"}
        ]
        idempotency_record.response_json = historical_response
        self.db.commit()

        second_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json=request_body,
            headers=headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.json(), first_response.json())
        self.assertNotIn("historical-ai-secret", second_response.text)

        self.db.expire_all()
        add_events = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.ADD,
        ).all()
        self.assertEqual(len(add_events), 1)
        self.assertEqual(self.db.query(OutboxEvent).filter(OutboxEvent.aggregate_public_id == truth_position.public_id).count(), 1)
        idempotency_record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "trading_position.trade_event.create",
        ).one()
        self.assertEqual(idempotency_record.status, "COMPLETED")
        self.assertIsNotNone(idempotency_record.response_json)
        self.assertEqual(
            idempotency_record.response_json["data"]["ai_sidecar"]["items"][0]["conclusion"],
            "historical-ai-secret",
        )

    def test_trade_event_write_rejects_idempotency_key_reuse_with_different_payload(self):
        truth_position = self._seed_open_synced_position()
        headers = {"Idempotency-Key": "truth-add-conflict-1"}

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "3",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
            headers=headers,
        )
        conflict_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "4",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
            headers=headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(conflict_response.status_code, 409)
        self.assertEqual(conflict_response.json()["detail"], "Idempotency key reuse with a different request payload.")

        self.db.expire_all()
        add_events = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.ADD,
        ).all()
        self.assertEqual(len(add_events), 1)

    def test_trade_event_reverse_latest_event_preserves_audit_trail_and_replays_fifo(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Scale out into strength",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)

        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()

        reverse_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Broker correction: reduction did not fill",
            },
        )

        self.assertEqual(reverse_response.status_code, 201)
        payload = reverse_response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("0"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("0"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "REDUCE", "REVERSAL"])
        reversal_node = payload["data"]["lifecycle_thread"]["nodes"][-1]
        self.assertEqual(reversal_node["reverses_event_public_id"], reduce_event.public_id)
        cash_effects = payload["data"]["ledger_summary"]["cash_effects"]
        self.assertEqual(
            [entry["entry_type"] for entry in cash_effects],
            ["REALIZED_PNL", "FEE", "REALIZED_PNL", "FEE"],
        )
        self.assertEqual(
            [Decimal(str(entry["amount"])) for entry in cash_effects],
            [
                Decimal("60"),
                Decimal("-1"),
                Decimal("-60"),
                Decimal("1"),
            ],
        )

        self.db.expire_all()
        reversal_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
        ).one()
        self.assertTrue(reversal_event.is_adjustment)
        self.assertEqual(reversal_event.reverses_event_id, reduce_event.id)
        self.assertEqual(reversal_event.realized_pnl_net, Decimal("-59.00000000"))
        reversal_ledger = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == reversal_event.id,
        ).order_by(AccountLedgerEntry.id.asc()).all()
        self.assertEqual(
            [(entry.posting_kind, entry.amount) for entry in reversal_ledger],
            [
                (LedgerPostingKind.REALIZED_GROSS.value, Decimal("-60.00000000")),
                (LedgerPostingKind.TRADE_FEE.value, Decimal("1.00000000")),
            ],
        )

    def test_trade_event_reverse_rejects_open_event_until_void_semantics_exist(self):
        truth_position = self._seed_open_synced_position()
        open_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{open_event.public_id}/reverse",
            json={
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Attempt to void opening event",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("OPEN events cannot be reversed", response.json()["detail"])
        self.db.expire_all()
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.REVERSAL,
            ).count(),
            0,
        )

    def test_trade_event_reverse_rejects_non_latest_active_trade_event(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "1",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)
        add_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "200",
                "currency": "USD",
                "occurred_at": "2026-04-04T15:30:00+00:00",
            },
        )
        self.assertEqual(add_response.status_code, 201)

        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()
        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-05T12:00:00+00:00"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Only the latest active trade event can be reversed", response.json()["detail"])

    def test_trade_event_reverse_rejects_duplicate_reversal(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)
        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-04T12:00:00+00:00"},
        )
        self.assertEqual(first_response.status_code, 201)
        second_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-05T12:00:00+00:00"},
        )

        self.assertEqual(second_response.status_code, 422)
        self.assertIn("already been reversed", second_response.json()["detail"])

    def test_trade_event_write_close_marks_position_closed_and_writes_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "CLOSE",
                "quantity": "5",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Exit full position",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["data"]["position_summary"]["status"], "CLOSED")
        self.assertEqual(payload["data"]["review_status"], "CLOSED_PENDING_REVIEW")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("150"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("149"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "CLOSE"])

        self.db.expire_all()
        close_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.CLOSE,
        ).one()
        ledger_entries = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == close_event.id,
        ).order_by(AccountLedgerEntry.id.asc()).all()
        self.assertEqual(
            [(entry.posting_kind, entry.amount) for entry in ledger_entries],
            [
                (LedgerPostingKind.REALIZED_GROSS.value, Decimal("150.00000000")),
                (LedgerPostingKind.TRADE_FEE.value, Decimal("-1.00000000")),
            ],
        )

        legacy_projection = self.db.query(Position).filter(
            Position.public_id == "legacy-open-position"
        ).one()
        self.assertEqual(legacy_projection.total_quantity, Decimal("0E-8"))
        self.assertEqual(legacy_projection.realized_pnl, Decimal("149.00000000"))
        self.assertEqual(legacy_projection.status, PositionStatus.CLOSED)
        self.assertIsNotNone(legacy_projection.closed_at)

    def test_trade_event_write_rejects_partial_close_without_mutating_events(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "CLOSE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("CLOSE event quantity must equal remaining open quantity", response.json()["detail"])

        self.db.expire_all()
        events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).all()
        self.assertEqual([event.event_type for event in events], [PositionEventType.OPEN])

    def test_trade_event_write_rejects_add_on_closed_position_without_mutating_events(self):
        truth_position = self._seed_synced_position()
        original_events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).count()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "205",
                "currency": "USD",
                "occurred_at": "2026-04-06T15:30:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Cannot append trade events to a closed trading position", response.json()["detail"])

        self.db.expire_all()
        events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).all()
        self.assertEqual(len(events), original_events)
        self.assertEqual([event.event_type for event in events], [
            PositionEventType.OPEN,
            PositionEventType.ADD,
            PositionEventType.CLOSE,
        ])


if __name__ == "__main__":
    unittest.main()
