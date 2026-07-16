import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from routers.dashboard import _sankey_asset_type_label
from services import import_service as import_service_module
from services.import_service import ImportService


class _Upload:
    def __init__(self, filename: str, content: bytes = b""):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


class LocalizedUserCopyTests(unittest.TestCase):
    def setUp(self):
        self.service = ImportService(db=None)

    def test_import_rejects_unsupported_files_with_chinese_message(self):
        with self.assertRaises(HTTPException) as context:
            asyncio.run(self.service.parse_file(_Upload("trades.txt")))

        self.assertEqual(context.exception.detail, "不支持此文件格式，请上传 CSV 或 Excel 文件。")

    def test_import_row_validation_returns_chinese_messages(self):
        pandas_stub = SimpleNamespace(
            isna=lambda value: value is None,
            notna=lambda value: value is not None,
            to_datetime=lambda _value: (_ for _ in ()).throw(ValueError("invalid date")),
        )
        with patch.object(import_service_module, "pd", pandas_stub):
            is_valid, errors, _ = self.service._validate_row({
                "symbol": None,
                "date": "not-a-date",
                "price": 0,
                "quantity": 0,
                "direction": "unknown",
                "action": "unknown",
            })

        self.assertFalse(is_valid)
        self.assertEqual(errors, [
            "标的代码不能为空",
            "日期格式无效",
            "价格必须大于 0",
            "数量必须大于 0",
            "方向无效（仅支持 LONG / SHORT）",
            "操作无效（仅支持 OPEN / CLOSE）",
        ])

    def test_import_expiry_and_sankey_categories_are_localized(self):
        with self.assertRaises(HTTPException) as context:
            self.service.process_import("missing", account_id=1, user_id=1)

        self.assertEqual(context.exception.detail, "导入会话已过期，请重新上传文件。")
        self.assertEqual(_sankey_asset_type_label("STOCK"), "股票")
        self.assertEqual(_sankey_asset_type_label("CRYPTO"), "加密资产")
        self.assertEqual(_sankey_asset_type_label("UNKNOWN"), "其他资产")


if __name__ == "__main__":
    unittest.main()
