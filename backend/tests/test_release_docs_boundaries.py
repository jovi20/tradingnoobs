from __future__ import annotations

from pathlib import Path
import unittest


class ReleaseDocumentationBoundaryTests(unittest.TestCase):
    def test_ibkr_binding_effective_confirm_includes_proven_flat_empty_coverage(self):
        plan = (
            self.repository_root
            / "docs"
            / "superpowers"
            / "plans"
            / "2026-07-16-dev-trading-journal-development-plan.md"
        ).read_text(encoding="utf-8")
        adr = (
            self.repository_root
            / "docs"
            / "adr"
            / "0001-trading-journal-beta-release-contract.md"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(plan.count("binding-effective confirm"), 2)
        self.assertIn("The first binding-effective confirm establishes that binding", adr)
        self.assertIn("zero-execution statement with proven flat-boundary evidence and valid coverage", adr)
        self.assertIn("永久失去 hard-delete 资格", plan)
        self.assertNotIn("即令账户变为 archive-only", plan)
        self.assertNotIn("只有首次成功 confirm 才创建 binding", plan)

    @classmethod
    def setUpClass(cls):
        cls.repository_root = Path(__file__).resolve().parents[2]

    def test_baseline_compose_does_not_inject_optional_provider_secrets(self):
        compose = (self.repository_root / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        for variable in (
            "LLM_API_KEY",
            "LLM_API_URL",
            "LLM_MODEL",
            "FINNHUB_API_KEY",
            "BINANCE_API_KEY",
            "BINANCE_API_SECRET",
        ):
            self.assertNotIn(variable, compose)
        self.assertIn("DEPLOYMENT_CAPABILITY_ALLOWLIST=", compose)

    def test_active_deployment_guide_keeps_optional_capabilities_closed(self):
        guide = (
            self.repository_root / "docs" / "vps-dev-parallel-deployment.md"
        ).read_text(encoding="utf-8")
        for variable in (
            "LLM_API_KEY=",
            "LLM_API_URL=",
            "FINNHUB_API_KEY=",
            "BINANCE_API_KEY=",
            "BINANCE_API_SECRET=",
        ):
            self.assertNotIn(variable, guide)
        self.assertIn("DEPLOYMENT_CAPABILITY_ALLOWLIST=", guide)
        self.assertNotIn("/insights", guide)

    def test_optional_implementation_docs_disclaim_beta_availability(self):
        market_prefix = (
            self.repository_root / "docs" / "market_data_sources.md"
        ).read_text(encoding="utf-8")[:1200]
        readiness_prefix = (
            self.repository_root / "docs" / "release-readiness-checklist.md"
        ).read_text(encoding="utf-8")[:1200]
        rollback_prefix = (
            self.repository_root / "docs" / "release-rollback-playbook.md"
        ).read_text(encoding="utf-8")[:1200]

        self.assertIn("404 FEATURE_DISABLED", market_prefix)
        self.assertIn("SUPERSEDED", readiness_prefix)
        self.assertIn("SUPERSEDED", rollback_prefix)

    def test_registration_docs_do_not_claim_the_shared_code_route_is_available(self):
        backend_readme = (self.repository_root / "backend" / "README.md").read_text(
            encoding="utf-8"
        )
        frontend_readme = (self.repository_root / "frontend" / "README.md").read_text(
            encoding="utf-8"
        )
        developer_guide = (self.repository_root / "docs" / "DEVELOPER_GUIDE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("/api/auth/register` 当前也属于 hard-off", backend_readme)
        self.assertIn("`/register` 路由模块已删除", frontend_readme)
        self.assertIn("`/register` 路由模块已删除", developer_guide)
        self.assertIn("`/api/auth/register` 也未注册", developer_guide)
        self.assertNotIn("invite-only `/api/auth/register` 仍是核心 onboarding 路径", backend_readme)
        self.assertNotIn("`/register` 保留给 invite-only onboarding", frontend_readme)
        self.assertNotIn("`/register` 是例外", developer_guide)

    def test_active_docs_do_not_offer_public_migration_fallback_headers(self):
        developer_guide = (self.repository_root / "docs" / "DEVELOPER_GUIDE.md").read_text(
            encoding="utf-8"
        )
        rollback_addendum = (
            self.repository_root / "docs" / "release-rollback-playbook.md"
        ).read_text(encoding="utf-8").split("## Historical P11-P18 Playbook", 1)[0]

        self.assertIn("`X-Migration-Fallback` 不在 OpenAPI 中且不能授予迁移权限", developer_guide)
        self.assertNotIn("只有显式 `X-Migration-Fallback", developer_guide)
        self.assertIn("不得恢复普通 `/api/positions` 路由上的 `X-Migration-Fallback`", rollback_addendum)


if __name__ == "__main__":
    unittest.main()
