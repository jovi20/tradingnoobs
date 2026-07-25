from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    PositionEvent,
    TradingAccount,
    TradingPosition,
    User,
)
from services.auth_service import get_current_user
from services.generic_import_service import (
    GenericImportError,
    IMPORT_FILE_PREFIX,
    MAX_FILE_BYTES,
    cleanup_terminal_import_rows,
    expire_due_import_sessions,
    expire_session_if_due,
    remove_staged_import_file,
    scavenge_orphan_import_files,
    stage_import_upload,
)


HEADER = (
    "asset_type,market,exchange_code,symbol,instrument_type,direction,"
    "action,timestamp,price,quantity,currency,commission,fee_currency,"
    "reason,note,external_trade_id\n"
)


def csv_row(
    *,
    symbol: str = "AAPL",
    direction: str = "LONG",
    action: str = "OPEN",
    timestamp: str = "2026-07-25T10:00:00+00:00",
    price: str = "200",
    quantity: str = "2",
    external_trade_id: str = "",
) -> str:
    return (
        f"STOCK,US,NASDAQ,{symbol},SPOT,{direction},{action},{timestamp},"
        f"{price},{quantity},USD,1.25,USD,planned entry,note,"
        f"{external_trade_id}\n"
    )


class JRN011ImportPreviewTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_temp_root = os.environ.get("TRADINGNOOBS_IMPORT_TMP_DIR")
        os.environ["TRADINGNOOBS_IMPORT_TMP_DIR"] = self.temp_dir.name
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.user = User(
            email="jrn011@example.com",
            email_normalized="jrn011@example.com",
            hashed_password="hashed",
            public_id="jrn011-user",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.other_user = User(
            email="jrn011-other@example.com",
            email_normalized="jrn011-other@example.com",
            hashed_password="hashed",
            public_id="jrn011-other-user",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.account = TradingAccount(
            user=self.user,
            public_id="jrn011-account",
            name="Import account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.other_account = TradingAccount(
            user=self.other_user,
            public_id="jrn011-other-account",
            name="Other import account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add_all(
            [self.user, self.other_user, self.account, self.other_account]
        )
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.other_user)
        self.db.refresh(self.account)
        self.db.refresh(self.other_account)
        self.current_user = self.user

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.current_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if self.previous_temp_root is None:
            os.environ.pop("TRADINGNOOBS_IMPORT_TMP_DIR", None)
        else:
            os.environ["TRADINGNOOBS_IMPORT_TMP_DIR"] = self.previous_temp_root
        self.temp_dir.cleanup()

    def upload(
        self,
        content: bytes,
        *,
        key: str = "upload-1",
        filename: str = "trades.csv",
        account_public_id: str | None = None,
    ):
        return self.client.post(
            "/api/positions/import/upload",
            headers={"Idempotency-Key": key},
            data={
                "account_id": account_public_id or self.account.public_id,
                "adapter_kind": "GENERIC_BOOTSTRAP",
            },
            files={"file": (filename, content)},
        )

    def test_csv_preview_is_persistent_owner_bound_and_financially_side_effect_free(self):
        content = (
            HEADER
            + csv_row(external_trade_id="untrusted-1")
            + csv_row(external_trade_id="untrusted-1")
        ).encode()
        first = self.upload(content)
        replay = self.upload(content)
        conflict = self.upload(
            (HEADER + csv_row(symbol="MSFT")).encode(),
        )

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(
            conflict.json()["detail"]["code"],
            "IDEMPOTENCY_KEY_REUSED",
        )
        payload = first.json()
        self.assertEqual(payload["status"], "PREVIEW_READY")
        self.assertEqual(payload["total_rows"], 2)
        self.assertEqual(payload["valid_rows"], 2)
        self.assertTrue(payload["confirm_available"])
        self.assertEqual(
            payload["rows"][0]["normalized_values"]["instrument_resolution"],
            "CREATE_ON_CONFIRM",
        )
        self.assertNotIn(
            "external_trade_id",
            payload["rows"][0]["normalized_values"],
        )
        first_warning_codes = {
            issue["code"] for issue in payload["rows"][0]["warnings"]
        }
        second_warning_codes = {
            issue["code"] for issue in payload["rows"][1]["warnings"]
        }
        self.assertIn("UNTRUSTED_SOURCE_ID_IGNORED", first_warning_codes)
        self.assertIn("DUPLICATE_ROW", second_warning_codes)

        session_id = payload["session_public_id"]
        reloaded = self.client.get(
            f"/api/positions/import/sessions/{session_id}"
        )
        self.assertEqual(reloaded.status_code, 200, reloaded.text)
        self.assertEqual(reloaded.json(), payload)

        self.db.expire_all()
        session = self.db.query(ImportSession).one()
        record = self.db.query(IdempotencyKey).one()
        self.assertEqual(session.user_id, self.user.id)
        self.assertEqual(session.account_id, self.account.id)
        self.assertEqual(self.db.query(ImportRow).count(), 2)
        self.assertIsNone(record.expires_at)
        self.assertNotEqual(record.key, "upload-1")
        self.assertTrue(record.key.startswith("sha256:"))
        self.assertFalse(self.db.get(TradingAccount, self.account.id).hard_delete_eligible)
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(self.db.query(PositionEvent).count(), 0)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 0)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

        self.current_user = self.other_user
        hidden = self.client.get(
            f"/api/positions/import/sessions/{session_id}"
        )
        self.assertEqual(hidden.status_code, 404)
        independent = self.upload(
            content,
            key="upload-1",
            account_public_id=self.other_account.public_id,
        )
        self.assertEqual(independent.status_code, 201, independent.text)

    def test_alias_normalization_and_stable_original_row_order(self):
        content = (
            "asset,venue,exchange,ticker,instrument,side,operation,date,"
            "trade_price,qty,quote_currency\n"
            "equity,us,nasdaq,AAPL,spot,buy,entry,"
            "2026-07-25T10:00:00+00:00,200,2,usd\n"
            "equity,us,nasdaq,MSFT,spot,long,open,"
            "2026-07-25T10:00:00+00:00,400,1,usd\n"
        ).encode()
        response = self.upload(content, key="aliases")
        self.assertEqual(response.status_code, 201, response.text)
        rows = response.json()["rows"]
        self.assertEqual([row["row_number"] for row in rows], [2, 3])
        self.assertEqual(rows[0]["normalized_values"]["asset_type"], "STOCK")
        self.assertEqual(rows[0]["normalized_values"]["direction"], "LONG")
        self.assertEqual(rows[0]["normalized_values"]["action"], "OPEN")

    def test_dst_gap_and_fold_return_422_with_persistent_error_preview(self):
        self.user.timezone = "America/New_York"
        self.db.commit()
        for index, (value, expected_code) in enumerate(
            (
                ("2026-03-08T02:30:00", "NONEXISTENT_LOCAL_TIME"),
                ("2026-11-01T01:30:00", "AMBIGUOUS_LOCAL_TIME"),
            )
        ):
            with self.subTest(value=value):
                response = self.upload(
                    (HEADER + csv_row(timestamp=value)).encode(),
                    key=f"dst-{index}",
                )
                self.assertEqual(response.status_code, 422, response.text)
                payload = response.json()
                self.assertEqual(payload["status"], "PREVIEW_READY")
                self.assertEqual(payload["error_rows"], 1)
                self.assertEqual(
                    payload["rows"][0]["errors"][0]["code"],
                    expected_code,
                )
        self.assertEqual(self.db.query(TradingPosition).count(), 0)

    def test_structural_failure_is_persisted_and_replayed(self):
        content = b"symbol,timestamp\nAAPL,2026-07-25T10:00:00Z\n"
        first = self.upload(content, key="bad-headers")
        replay = self.upload(content, key="bad-headers")
        self.assertEqual(first.status_code, 422, first.text)
        self.assertEqual(replay.status_code, 422, replay.text)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(first.json()["status"], "FAILED")
        self.assertEqual(
            first.json()["error"]["code"],
            "MISSING_IMPORT_COLUMNS",
        )
        self.assertEqual(self.db.query(ImportSession).count(), 1)
        self.assertEqual(self.db.query(ImportRow).count(), 0)
        deleted = self.client.delete(f"/api/accounts/{self.account.public_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        self.db.expire_all()
        self.assertFalse(self.db.get(TradingAccount, self.account.id).is_active)

    def test_invalid_utf8_header_is_persisted_and_replayed(self):
        content = b"\xff\xfe\xfa,not-utf8\n"
        first = self.upload(content, key="invalid-utf8")
        replay = self.upload(content, key="invalid-utf8")
        self.assertEqual(first.status_code, 422, first.text)
        self.assertEqual(replay.status_code, 422, replay.text)
        self.assertEqual(first.json(), replay.json())
        self.assertEqual(first.json()["status"], "FAILED")
        self.assertEqual(
            first.json()["error"]["code"],
            "INVALID_CSV_ENCODING",
        )
        self.assertEqual(self.db.query(ImportSession).count(), 1)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_non_usd_account_rejects_upload_without_persistent_partial_state(self):
        self.account.currency = "CNY"
        self.db.commit()
        response = self.upload(HEADER.encode(), key="non-usd")
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(self.db.query(ImportSession).count(), 0)
        self.assertEqual(self.db.query(IdempotencyKey).count(), 0)
        self.db.expire_all()
        self.assertTrue(
            self.db.get(TradingAccount, self.account.id).hard_delete_eligible
        )

    def test_header_only_csv_and_xlsx_are_valid_zero_row_previews(self):
        csv_response = self.upload(HEADER.encode(), key="empty-csv")
        self.assertEqual(csv_response.status_code, 201, csv_response.text)
        self.assertEqual(csv_response.json()["total_rows"], 0)

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(HEADER.strip().split(","))
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        xlsx_response = self.upload(
            output.getvalue(),
            key="empty-xlsx",
            filename="trades.xlsx",
        )
        self.assertEqual(xlsx_response.status_code, 201, xlsx_response.text)
        self.assertEqual(xlsx_response.json()["file_format"], "XLSX")
        self.assertEqual(xlsx_response.json()["total_rows"], 0)

    def test_xlsx_iteration_failure_is_persisted_instead_of_returning_500(self):
        class WorkbookWithoutSheets:
            worksheets = []

            def close(self):
                pass

        with patch(
            "services.generic_import_service.load_workbook",
            return_value=WorkbookWithoutSheets(),
        ):
            response = self.upload(
                b"not-used-by-mocked-loader",
                key="xlsx-no-sheets",
                filename="trades.xlsx",
            )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["status"], "FAILED")
        self.assertEqual(
            response.json()["error"]["code"],
            "INVALID_XLSX_FILE",
        )
        self.assertEqual(self.db.query(ImportSession).count(), 1)
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_row_limit_accepts_5000_and_rejects_5001_without_partial_rows(self):
        accepted = (
            HEADER
            + "".join(
                csv_row(symbol=f"AAPL{i % 10}", quantity=str(i + 1))
                for i in range(5000)
            )
        ).encode()
        accepted_response = self.upload(accepted, key="rows-5000")
        self.assertEqual(
            accepted_response.status_code,
            201,
            accepted_response.text[:500],
        )
        self.assertEqual(accepted_response.json()["total_rows"], 5000)

        rejected = accepted + csv_row(symbol="MSFT").encode()
        rejected_response = self.upload(rejected, key="rows-5001")
        self.assertEqual(rejected_response.status_code, 422)
        self.assertEqual(rejected_response.json()["status"], "FAILED")
        self.assertEqual(
            rejected_response.json()["error"]["code"],
            "IMPORT_ROW_LIMIT_EXCEEDED",
        )
        rejected_session = self.db.query(ImportSession).filter(
            ImportSession.public_id
            == rejected_response.json()["session_public_id"]
        ).one()
        self.assertEqual(
            self.db.query(ImportRow).filter(
                ImportRow.session_id == rejected_session.id
            ).count(),
            0,
        )

    def test_file_size_boundary_and_temp_cleanup(self):
        exact_upload = UploadFile(
            filename="boundary.csv",
            file=BytesIO(b"x" * MAX_FILE_BYTES),
        )
        staged = asyncio.run(
            stage_import_upload(
                exact_upload,
                temp_root=Path(self.temp_dir.name),
            )
        )
        self.assertEqual(staged.size_bytes, MAX_FILE_BYTES)
        self.assertEqual(staged.path.stat().st_mode & 0o777, 0o600)
        remove_staged_import_file(staged)
        asyncio.run(exact_upload.close())

        oversized_upload = UploadFile(
            filename="oversized.csv",
            file=BytesIO(b"x" * (MAX_FILE_BYTES + 1)),
        )
        with self.assertRaises(GenericImportError) as raised:
            asyncio.run(
                stage_import_upload(
                    oversized_upload,
                    temp_root=Path(self.temp_dir.name),
                )
            )
        self.assertEqual(raised.exception.code, "IMPORT_FILE_TOO_LARGE")
        asyncio.run(oversized_upload.close())
        self.assertEqual(list(Path(self.temp_dir.name).iterdir()), [])

    def test_orphan_scavenger_only_removes_expired_import_files(self):
        root = Path(self.temp_dir.name)
        old_import = root / f"{IMPORT_FILE_PREFIX}old.csv"
        fresh_import = root / f"{IMPORT_FILE_PREFIX}fresh.csv"
        unrelated = root / "keep.txt"
        for path in (old_import, fresh_import, unrelated):
            path.touch()
        boundary = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
        os.utime(
            old_import,
            (boundary.timestamp() - 3600, boundary.timestamp() - 3600),
        )
        os.utime(
            fresh_import,
            (boundary.timestamp() - 3599, boundary.timestamp() - 3599),
        )

        removed = scavenge_orphan_import_files(
            now=boundary,
            older_than_seconds=3600,
            temp_root=root,
        )

        self.assertEqual(removed, 1)
        self.assertFalse(old_import.exists())
        self.assertTrue(fresh_import.exists())
        self.assertTrue(unrelated.exists())

    def test_expiry_is_enforced_at_exact_boundary_without_cleanup_worker(self):
        content = (HEADER + csv_row()).encode()
        response = self.upload(
            content,
            key="expiry",
        )
        session = self.db.query(ImportSession).filter(
            ImportSession.public_id == response.json()["session_public_id"]
        ).one()
        boundary = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
        session.expires_at = boundary
        self.db.commit()
        self.assertTrue(
            expire_session_if_due(
                self.db,
                session=session,
                now=boundary,
            )
        )
        self.db.expire_all()
        self.assertEqual(
            self.db.get(ImportSession, session.id).status,
            "EXPIRED",
        )
        expired = self.client.get(
            f"/api/positions/import/sessions/{session.public_id}"
        )
        self.assertEqual(expired.status_code, 410)
        self.assertEqual(
            expired.json()["detail"]["code"],
            "IMPORT_SESSION_EXPIRED",
        )
        replay = self.upload(content, key="expiry")
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), response.json())

    def test_due_session_maintenance_is_bounded_and_repeatable(self):
        for index in range(2):
            response = self.upload(
                HEADER.encode(),
                key=f"expire-maintenance-{index}",
            )
            session = self.db.query(ImportSession).filter(
                ImportSession.public_id == response.json()["session_public_id"]
            ).one()
            session.expires_at = datetime(
                2026,
                7,
                26,
                12,
                0,
                tzinfo=timezone.utc,
            )
        self.db.commit()
        boundary = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)

        results = []
        for _ in range(3):
            results.append(
                expire_due_import_sessions(
                    self.db,
                    now=boundary,
                    batch_size=1,
                )
            )
            self.db.commit()

        self.assertEqual(results, [1, 1, 0])
        self.assertEqual(
            self.db.query(ImportSession).filter(
                ImportSession.status == "EXPIRED"
            ).count(),
            2,
        )

    def test_terminal_row_cleanup_is_bounded_and_preserves_audit_shell(self):
        response = self.upload(
            (HEADER + csv_row() + csv_row(symbol="MSFT")).encode(),
            key="cleanup",
        )
        session = self.db.query(ImportSession).filter(
            ImportSession.public_id == response.json()["session_public_id"]
        ).one()
        boundary = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)
        session.status = "EXPIRED"
        session.terminal_at = boundary - timedelta(days=30)
        self.db.commit()

        first = cleanup_terminal_import_rows(
            self.db,
            now=boundary,
            batch_size=1,
        )
        self.db.commit()
        second = cleanup_terminal_import_rows(
            self.db,
            now=boundary,
            batch_size=10,
        )
        self.db.commit()
        third = cleanup_terminal_import_rows(
            self.db,
            now=boundary,
            batch_size=10,
        )
        self.db.commit()
        self.assertEqual((first, second, third), (1, 1, 0))
        self.assertEqual(self.db.query(ImportRow).count(), 0)
        self.db.expire_all()
        audit_shell = self.db.get(ImportSession, session.id)
        self.assertIsNotNone(audit_shell)
        self.assertEqual(audit_shell.status, "EXPIRED")
        self.assertIsNotNone(audit_shell.rows_cleaned_at)

    def test_any_import_session_permanently_changes_delete_to_archive(self):
        content = HEADER.encode()
        response = self.upload(content, key="account-delete")
        self.assertEqual(response.status_code, 201)
        deleted = self.client.delete(f"/api/accounts/{self.account.public_id}")
        self.assertEqual(deleted.status_code, 204, deleted.text)
        replay = self.upload(content, key="account-delete")
        blocked_new_upload = self.upload(content, key="archived-new-upload")
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), response.json())
        self.assertEqual(blocked_new_upload.status_code, 409)
        self.assertEqual(
            blocked_new_upload.json()["detail"]["code"],
            "ACCOUNT_ARCHIVED",
        )
        self.db.expire_all()
        account = self.db.get(TradingAccount, self.account.id)
        self.assertIsNotNone(account)
        self.assertFalse(account.is_active)
        self.assertEqual(self.db.query(ImportSession).count(), 1)

    def test_template_is_public_contract_and_confirm_is_owner_first(self):
        template = self.client.get("/api/positions/import/template")
        self.assertEqual(template.status_code, 200)
        self.assertIn("asset_type,market,exchange_code", template.text)
        confirm = self.client.post(
            "/api/positions/import/confirm",
            json={"session_public_id": "untrusted"},
        )
        self.assertEqual(confirm.status_code, 404)
        self.assertEqual(
            confirm.json()["detail"]["code"],
            "IMPORT_SESSION_NOT_FOUND",
        )
