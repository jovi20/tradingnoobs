from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest


class JournalCoreConfigBoundaryTests(unittest.TestCase):
    def test_empty_ceiling_does_not_parse_optional_provider_secrets(self):
        backend_dir = Path(__file__).resolve().parents[1]
        sentinel = "optional-provider-secret-must-stay-unparsed"
        script = "\n".join(
            (
                "import main",
                "from config import get_optional_provider_settings",
                "core_dump = main.app_settings.model_dump()",
                "assert 'llm_api_key' not in core_dump",
                "assert 'finnhub_api_key' not in core_dump",
                "assert 'binance_api_secret' not in core_dump",
                f"assert {sentinel!r} not in repr(core_dump)",
                "assert get_optional_provider_settings.cache_info().currsize == 0",
            )
        )
        env = os.environ.copy()
        env.update(
            {
                "DEPLOYMENT_CAPABILITY_ALLOWLIST": "",
                "LLM_API_KEY": sentinel,
                "FINNHUB_API_KEY": sentinel,
                "BINANCE_API_KEY": sentinel,
                "BINANCE_API_SECRET": sentinel,
                "PYTHONPATH": str(backend_dir),
            }
        )

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


if __name__ == "__main__":
    unittest.main()
