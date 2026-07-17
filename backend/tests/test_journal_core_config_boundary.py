from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


class JournalCoreConfigBoundaryTests(unittest.TestCase):
    def _run_subprocess(self, script: str, env_updates: dict[str, str]) -> None:
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env.update(env_updates)
        env["PYTHONPATH"] = str(backend_dir)

        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(
            completed.returncode,
            0,
            completed.stderr or completed.stdout,
        )

    def test_empty_ceiling_does_not_parse_optional_provider_secrets(self):
        sentinel = "optional-provider-secret-must-stay-unparsed"
        script = "\n".join(
            (
                "import main",
                "from config import get_ai_provider_settings, get_broker_provider_settings, get_market_provider_settings",
                "core_dump = main.app_settings.model_dump()",
                "assert 'llm_api_key' not in core_dump",
                "assert 'finnhub_api_key' not in core_dump",
                "assert 'binance_api_secret' not in core_dump",
                f"assert {sentinel!r} not in repr(core_dump)",
                "assert get_ai_provider_settings.cache_info().currsize == 0",
                "assert get_market_provider_settings.cache_info().currsize == 0",
                "assert get_broker_provider_settings.cache_info().currsize == 0",
            )
        )
        self._run_subprocess(
            script,
            {
                "DEPLOYMENT_CAPABILITY_ALLOWLIST": "",
                "LLM_API_KEY": sentinel,
                "FINNHUB_API_KEY": sentinel,
                "BINANCE_API_KEY": sentinel,
                "BINANCE_API_SECRET": sentinel,
            },
        )

    def test_market_settings_do_not_parse_ai_or_broker_secrets(self):
        script = "\n".join(
            (
                "from config import get_ai_provider_settings, get_broker_provider_settings, get_market_provider_settings",
                "from services.market_data_orchestrator import _resolve_finnhub_api_key",
                "assert _resolve_finnhub_api_key(None) == 'market-only-secret'",
                "assert get_market_provider_settings.cache_info().currsize == 1",
                "assert get_ai_provider_settings.cache_info().currsize == 0",
                "assert get_broker_provider_settings.cache_info().currsize == 0",
            )
        )
        self._run_subprocess(
            script,
            {
                "FINNHUB_API_KEY": "market-only-secret",
                "LLM_API_KEY": "ai-must-not-be-parsed",
                "BINANCE_API_SECRET": "broker-must-not-be-parsed",
            },
        )

    def test_ai_settings_do_not_parse_market_or_broker_secrets(self):
        script = "\n".join(
            (
                "from config import get_ai_provider_settings, get_broker_provider_settings, get_market_provider_settings",
                "from services.platform_config_service import get_llm_runtime_config",
                "class Query:",
                "    def filter(self, *args): return self",
                "    def first(self): return None",
                "class DB:",
                "    def query(self, *args): return Query()",
                "runtime = get_llm_runtime_config(DB())",
                "assert runtime['api_key'] == 'ai-only-secret'",
                "assert get_ai_provider_settings.cache_info().currsize == 1",
                "assert get_market_provider_settings.cache_info().currsize == 0",
                "assert get_broker_provider_settings.cache_info().currsize == 0",
            )
        )
        self._run_subprocess(
            script,
            {
                "LLM_API_KEY": "ai-only-secret",
                "FINNHUB_API_KEY": "market-must-not-be-parsed",
                "BINANCE_API_SECRET": "broker-must-not-be-parsed",
            },
        )


if __name__ == "__main__":
    unittest.main()
