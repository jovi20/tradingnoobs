from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import FeatureFlag, PlatformSetting, SystemSetting
from release_profile import (
    DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV,
    DeploymentCapabilityConfigurationError,
    DeploymentCapabilityPolicy,
    OPTIONAL_RUNTIME_CAPABILITIES,
    ReleaseProfile,
    RuntimeCapability,
    get_deployment_capability_allowlist,
    is_capability_enabled,
    load_deployment_capability_policy,
    parse_deployment_capability_allowlist,
)
from services.capability_service import (
    CAPABILITY_ROLLOUT_FLAG_KEYS,
    capability_rollout_flag_key,
    is_effective_capability_enabled,
)


def _policy(*capabilities: RuntimeCapability) -> DeploymentCapabilityPolicy:
    return DeploymentCapabilityPolicy(frozenset(capabilities))


class DeploymentCapabilityPolicyTests(unittest.TestCase):
    def test_six_optional_capabilities_are_frozen(self):
        self.assertEqual(
            {capability.value for capability in OPTIONAL_RUNTIME_CAPABILITIES},
            {
                "MARKET",
                "BROKER_SYNC",
                "AI_INSIGHTS",
                "PDF_EXPORT",
                "RISK_CARDS",
                "OPEN_REGISTRATION",
            },
        )

    def test_missing_and_blank_allowlist_are_empty(self):
        self.assertEqual(load_deployment_capability_policy({}), _policy())
        self.assertEqual(
            load_deployment_capability_policy(
                {DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV: "  "}
            ),
            _policy(),
        )

    def test_allowlist_is_normalized_deduplicated_and_immutable(self):
        policy = load_deployment_capability_policy(
            {
                DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV: (
                    " market,MARKET,broker-sync, ai_insights "
                )
            }
        )
        self.assertEqual(
            policy.allowed_capabilities,
            frozenset(
                {
                    RuntimeCapability.MARKET,
                    RuntimeCapability.BROKER_SYNC,
                    RuntimeCapability.AI_INSIGHTS,
                }
            ),
        )
        self.assertIsInstance(policy.allowed_capabilities, frozenset)
        with self.assertRaises(AttributeError):
            policy.allowed_capabilities.add(RuntimeCapability.PDF_EXPORT)

    def test_unknown_allowlist_entry_is_a_configuration_error(self):
        with self.assertRaises(DeploymentCapabilityConfigurationError):
            parse_deployment_capability_allowlist("MARKET,NOT_A_CAPABILITY")

    def test_unknown_environment_entry_prevents_process_import(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env[DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV] = "MARKET,NOT_A_CAPABILITY"
        env["PYTHONPATH"] = str(backend_dir)

        completed = subprocess.run(
            [sys.executable, "-c", "import release_profile"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Unknown deployment capability", completed.stderr)

    def test_missing_environment_entry_starts_with_empty_ceiling(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env.pop(DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV, None)
        env["PYTHONPATH"] = str(backend_dir)
        script = "\n".join(
            (
                "from release_profile import (",
                "    RuntimeCapability,",
                "    get_deployment_capability_allowlist,",
                "    is_capability_enabled,",
                ")",
                "assert get_deployment_capability_allowlist() == frozenset()",
                "assert not is_capability_enabled(RuntimeCapability.MARKET)",
            )
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

    def test_imported_policy_matches_the_test_process_environment(self):
        self.assertEqual(
            get_deployment_capability_allowlist(),
            load_deployment_capability_policy().allowed_capabilities,
        )

    def test_development_full_cannot_expand_an_empty_ceiling(self):
        with patch("release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY", _policy()):
            self.assertFalse(
                is_capability_enabled(
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.DEVELOPMENT_FULL,
                )
            )

    def test_both_profiles_obey_the_same_deployment_ceiling(self):
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            for profile in ReleaseProfile:
                with self.subTest(profile=profile):
                    self.assertTrue(
                        is_capability_enabled(
                            RuntimeCapability.MARKET,
                            profile=profile,
                        )
                    )
                    self.assertFalse(
                        is_capability_enabled(
                            RuntimeCapability.BROKER_SYNC,
                            profile=profile,
                        )
                    )

    def test_runtime_flag_keys_match_the_versioned_machine_contract(self):
        self.assertEqual(
            CAPABILITY_ROLLOUT_FLAG_KEYS,
            {
                RuntimeCapability.MARKET: "capability.market.v1",
                RuntimeCapability.BROKER_SYNC: "capability.broker_sync.v1",
                RuntimeCapability.AI_INSIGHTS: "capability.ai_insights.v1",
                RuntimeCapability.PDF_EXPORT: "capability.pdf_export.v1",
                RuntimeCapability.RISK_CARDS: "capability.risk_cards.v1",
                RuntimeCapability.OPEN_REGISTRATION: (
                    "capability.open_registration.v1"
                ),
            },
        )


class RuntimeCapabilityResolverTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "capability.db")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _add_flag(
        self,
        capability: RuntimeCapability,
        *,
        enabled: bool = True,
        actor_targets=None,
        rollout_percentage=None,
        expires_at=None,
    ) -> None:
        self.db.add(
            FeatureFlag(
                key=capability_rollout_flag_key(capability),
                enabled=enabled,
                actor_targets=[] if actor_targets is None else actor_targets,
                rollout_percentage=rollout_percentage,
                expires_at=expires_at,
            )
        )
        self.db.commit()

    def _enabled(self, capability=RuntimeCapability.MARKET, *, actor_key=None):
        return is_effective_capability_enabled(
            self.db,
            capability,
            actor_key=actor_key,
            profile=ReleaseProfile.DEVELOPMENT_FULL,
        )

    def test_ceiling_denial_short_circuits_before_database_read(self):
        class ExplodingSession:
            def query(self, *_args, **_kwargs):
                raise AssertionError("database must not be read outside the ceiling")

        with patch("release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY", _policy()):
            self.assertFalse(
                is_effective_capability_enabled(
                    ExplodingSession(),
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.DEVELOPMENT_FULL,
                )
            )

    def test_allowlisted_capability_requires_present_enabled_runtime_flag(self):
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertFalse(self._enabled())
            self._add_flag(RuntimeCapability.MARKET)
            self.assertTrue(self._enabled())

    def test_allowlisted_capability_works_under_journal_baseline(self):
        self._add_flag(RuntimeCapability.MARKET)
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertTrue(
                is_effective_capability_enabled(
                    self.db,
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.JOURNAL_BASELINE,
                )
            )

    def test_expired_runtime_flag_fails_closed(self):
        self._add_flag(
            RuntimeCapability.MARKET,
            expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertFalse(self._enabled())

    def test_database_flag_failure_fails_closed(self):
        class BrokenSession:
            def query(self, *_args, **_kwargs):
                raise RuntimeError("database unavailable")

        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertFalse(
                is_effective_capability_enabled(
                    BrokenSession(),
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.DEVELOPMENT_FULL,
                )
            )

    def test_database_rows_cannot_forge_the_deployment_allowlist(self):
        self.db.add_all(
            [
                FeatureFlag(
                    key="deployment_capability_allowlist",
                    enabled=True,
                    actor_targets=["MARKET"],
                ),
                PlatformSetting(
                    key="deployment_capability_allowlist",
                    value="MARKET",
                ),
                SystemSetting(
                    key="deployment_capability_allowlist",
                    value="MARKET",
                ),
            ]
        )
        self.db.commit()

        with patch("release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY", _policy()):
            self.assertFalse(self._enabled())

    def test_actor_target_and_percentage_use_existing_rollout_semantics(self):
        self._add_flag(
            RuntimeCapability.AI_INSIGHTS,
            actor_targets=["selected-user"],
            rollout_percentage=0,
        )
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.AI_INSIGHTS),
        ):
            self.assertTrue(
                self._enabled(
                    RuntimeCapability.AI_INSIGHTS,
                    actor_key="selected-user",
                )
            )
            self.assertFalse(
                self._enabled(
                    RuntimeCapability.AI_INSIGHTS,
                    actor_key="other-user",
                )
            )

    def test_malformed_rollout_data_fails_closed(self):
        self._add_flag(
            RuntimeCapability.RISK_CARDS,
            actor_targets={"unexpected": "mapping"},
            rollout_percentage=101,
        )
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.RISK_CARDS),
        ):
            self.assertFalse(self._enabled(RuntimeCapability.RISK_CARDS))

    def test_empty_malformed_actor_mapping_does_not_enable_capability(self):
        self._add_flag(RuntimeCapability.PDF_EXPORT, actor_targets={})
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.PDF_EXPORT),
        ):
            self.assertFalse(self._enabled(RuntimeCapability.PDF_EXPORT))

    def test_malformed_enabled_field_access_fails_closed(self):
        class MalformedFlag:
            @property
            def enabled(self):
                raise TypeError("malformed enabled field")

        class Query:
            def filter(self, *_args, **_kwargs):
                return self

            def first(self):
                return MalformedFlag()

        class MalformedSession:
            def query(self, *_args, **_kwargs):
                return Query()

        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertFalse(
                is_effective_capability_enabled(
                    MalformedSession(),
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.DEVELOPMENT_FULL,
                )
            )

    def test_malformed_empty_expiry_field_fails_closed(self):
        class MalformedFlag:
            enabled = True
            expires_at = ""
            actor_targets = []
            rollout_percentage = None

        class Query:
            def filter(self, *_args, **_kwargs):
                return self

            def first(self):
                return MalformedFlag()

        class MalformedSession:
            def query(self, *_args, **_kwargs):
                return Query()

        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(RuntimeCapability.MARKET),
        ):
            self.assertFalse(
                is_effective_capability_enabled(
                    MalformedSession(),
                    RuntimeCapability.MARKET,
                    profile=ReleaseProfile.JOURNAL_BASELINE,
                )
            )

    def test_unknown_capability_fails_closed(self):
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            _policy(*OPTIONAL_RUNTIME_CAPABILITIES),
        ):
            self.assertFalse(self._enabled("NOT_A_CAPABILITY"))


if __name__ == "__main__":
    unittest.main()
