import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import IntegrationCredential, PlatformSetting, SystemSetting
from services.credential_service import encrypt_secret
from services.llm_service import classify_asset
from services.market_data_service import MarketDataService
from services.platform_config_service import (
    get_finnhub_api_key,
    get_llm_runtime_config,
)


class FakeLLMResponse:
    status_code = 200
    text = "ok"

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"type":"EQUITY","name":"Apple Inc."}'
                    }
                }
            ]
        }


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return FakeLLMResponse()


class PlatformConfigResolutionTests(unittest.TestCase):
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

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_llm_runtime_config_prefers_new_platform_tables_over_system_settings(self):
        self.db.add(PlatformSetting(key="llm_api_url", value="https://new.example/v1"))
        self.db.add(PlatformSetting(key="llm_model", value="gpt-5"))
        self.db.add(
            IntegrationCredential(
                provider_key="openai",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("new-secret"),
            )
        )
        self.db.add(SystemSetting(key="llm_api_url", value="https://old.example/v1"))
        self.db.add(SystemSetting(key="llm_api_key", value="old-secret"))
        self.db.add(SystemSetting(key="llm_model", value="gpt-old"))
        self.db.commit()

        config = get_llm_runtime_config(self.db)

        self.assertEqual(config["api_url"], "https://new.example/v1")
        self.assertEqual(config["api_key"], "new-secret")
        self.assertEqual(config["model"], "gpt-5")

    def test_market_data_service_prefers_new_integration_credential_for_finnhub(self):
        self.db.add(
            IntegrationCredential(
                provider_key="finnhub",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("new-finnhub-key"),
            )
        )
        self.db.add(SystemSetting(key="finnhub_api_key", value="old-finnhub-key"))
        self.db.commit()

        self.assertEqual(get_finnhub_api_key(self.db), "new-finnhub-key")

        service = MarketDataService(self.db)
        with patch("services.market_data_service.finnhub.Client") as client_cls:
            service._get_finnhub_client()
            client_cls.assert_called_once_with(api_key="new-finnhub-key")

    def test_classify_asset_uses_new_llm_tables_without_system_settings(self):
        self.db.add(PlatformSetting(key="llm_api_url", value="https://new.example/v1"))
        self.db.add(PlatformSetting(key="llm_model", value="gpt-5"))
        self.db.add(
            IntegrationCredential(
                provider_key="openai",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("new-secret"),
            )
        )
        self.db.commit()

        with patch("services.llm_service.httpx.AsyncClient", FakeAsyncClient):
            result = asyncio.run(classify_asset(self.db, "AAPL", "NASDAQ"))

        self.assertEqual(result, {"type": "EQUITY", "name": "Apple Inc."})


if __name__ == "__main__":
    unittest.main()
