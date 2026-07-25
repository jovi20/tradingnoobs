from __future__ import annotations

import re
import unittest
from pathlib import Path


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

    def test_registration_docs_distinguish_invite_onboarding_from_open_registration(self):
        backend_readme = (self.repository_root / "backend" / "README.md").read_text(
            encoding="utf-8"
        )
        frontend_readme = (self.repository_root / "frontend" / "README.md").read_text(
            encoding="utf-8"
        )
        developer_guide = (self.repository_root / "docs" / "DEVELOPER_GUIDE.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("invite-only onboarding 是独立的基线能力", backend_readme)
        self.assertIn("`/register` 仅提供一次性、限时邀请码", frontend_readme)
        self.assertIn("`OPEN_REGISTRATION` 继续关闭", developer_guide)
        self.assertIn("有效 IANA 时区", developer_guide)
        self.assertNotIn("`/register` 路由模块已删除", frontend_readme)
        self.assertNotIn("`/api/auth/register` 也未注册", developer_guide)

    def test_active_docs_do_not_offer_public_migration_fallback_headers(self):
        developer_guide = (self.repository_root / "docs" / "DEVELOPER_GUIDE.md").read_text(
            encoding="utf-8"
        )
        rollback_playbook = (
            self.repository_root / "docs" / "release-rollback-playbook.md"
        ).read_text(encoding="utf-8")

        self.assertIn("`X-Migration-Fallback` 不在 OpenAPI 中且不能授予迁移权限", developer_guide)
        self.assertNotIn("只有显式 `X-Migration-Fallback", developer_guide)
        self.assertIn("不得恢复普通 `/api/positions` 路由上的 `X-Migration-Fallback`", rollback_playbook)
        self.assertIn("不得在读取中触发 backfill、flush 或 commit", developer_guide)
        self.assertIn("不得恢复 `GET /api/positions/{id}/truth-lifecycle` 的惰性 legacy backfill", rollback_playbook)
        self.assertIn("`X-Migration-Fallback` 的任何客户端值都无效", rollback_playbook)
        self.assertIn("受审计的 admin/CLI migration namespace 尚未实现", rollback_playbook)
        self.assertIn("均稳定返回 `409`，不因 truth lifecycle 是否存在而改变", rollback_playbook)
        self.assertIn("非 owner 目标继续返回 `404`", rollback_playbook)

        for removed_public_token in (
            "legacy-batch-write",
            "legacy-review-write",
            "legacy-position-delete",
            "legacy-batch-edit",
        ):
            with self.subTest(removed_public_token=removed_public_token):
                self.assertNotIn(removed_public_token, rollback_playbook)
        for obsolete_instruction in (
            "缺少正确 header",
            "才在受控调用里使用对应 `X-Migration-Fallback` 值",
            "迁移/support 操作入口",
            "导入模板说明是用户可见操作说明",
        ):
            with self.subTest(obsolete_instruction=obsolete_instruction):
                self.assertNotIn(obsolete_instruction, rollback_playbook)

    def test_generic_import_document_matches_jrn011_preview_boundary(self):
        import_reference = (
            self.repository_root / "docs" / "import-template.md"
        ).read_text(encoding="utf-8")

        for required_boundary in (
            "`JRN-011` 已实现",
            "Historical unregistered legacy parser reference",
            "`POST /api/positions/import/upload`",
            "`POST /api/positions/import/confirm`",
            "`GET /api/positions/import/template`",
            "`GET /api/positions/import/sessions/{session_public_id}`",
            "`404 FEATURE_DISABLED`",
            "不写入 position、event 或 ledger",
            "10 MiB、5,000 行",
            "`410 IMPORT_SESSION_EXPIRED`",
            "永久失去 hard-delete 资格",
            "`CREATE_ON_CONFIRM`",
            "不删除 audit shell",
        ):
            with self.subTest(required_boundary=required_boundary):
                self.assertIn(required_boundary, import_reference)

        for misleading_phrase in (
            "确认导入时写入",
            "will be written",
        ):
            with self.subTest(misleading_phrase=misleading_phrase):
                self.assertNotIn(misleading_phrase, import_reference)

        canonical_table = import_reference.split("## Canonical 模板列", 1)[1].split(
            "## 临时文件与维护",
            1,
        )[0]
        canonical_rows = [
            line for line in canonical_table.splitlines() if line.startswith("| `")
        ]
        self.assertEqual(15, len(canonical_rows))

    def test_developer_guide_excludes_disabled_import_ui_and_freezes_legacy_mutations(self):
        developer_guide = (
            self.repository_root / "docs" / "DEVELOPER_GUIDE.md"
        ).read_text(encoding="utf-8")
        current_pages = developer_guide.split("前端当前主要页面：", 1)[1].split(
            "前端 legacy DTO 边界：", 1
        )[0]

        self.assertIn("- `/positions/import`", current_pages)
        self.assertIn(
            "`GENERIC_BOOTSTRAP` 已完成 JRN-011 upload/preview",
            developer_guide,
        )
        self.assertIn(
            "`POST /api/positions/import/confirm` 仍由 deny-only stub 返回 `404 FEATURE_DISABLED`",
            developer_guide,
        )
        self.assertIn("preview 不写 position/event/ledger", developer_guide)
        self.assertNotIn("只是调用 `notFound()` 的禁用壳", developer_guide)

        for mutation in (
            "legacy review `PATCH /api/positions/{position_id}`",
            "position hard delete `DELETE /api/positions/{position_id}`",
            "batch create `POST /api/positions/{position_id}/batches`",
            "batch edit/delete `PATCH|DELETE /api/positions/batches/{batch_id}`",
        ):
            with self.subTest(mutation=mutation):
                self.assertIn(mutation, developer_guide)
        self.assertIn("对 owner 已验证且资源存在的请求稳定返回 `409`", developer_guide)
        self.assertIn("任何 `X-Migration-Fallback` header 或历史 token 都不能绕过", developer_guide)
        self.assertIn("不因 truth lifecycle 是否存在而改变", developer_guide)

        for stale_claim in (
            "都需要显式 migration fallback header",
            "只允许显式迁移修正",
            "requires X-Migration-Fallback",
            "can be unlocked by X-Migration-Fallback",
        ):
            with self.subTest(stale_claim=stale_claim):
                self.assertNotIn(stale_claim, developer_guide)

    def test_active_metrics_distinguish_preview_fee_from_canonical_posting(self):
        metrics = (
            self.repository_root / "docs" / "trading-metrics.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "状态：`部分实现 / Import preview fee 已规范化、confirm 未实现`",
            metrics,
        )
        self.assertIn("JRN-011 upload/preview 已实现", metrics)
        self.assertIn("不会写入 canonical ledger", metrics)
        self.assertIn("legacy parser 的 `commission` 分支仍只是一项 historical reference", metrics)
        self.assertIn("`JRN-012` 必须把 preview fee", metrics)
        self.assertNotIn("导入流程支持解析 `commission`", metrics)

    def test_active_roadmap_keeps_legacy_parser_unreachable(self):
        roadmap = (
            self.repository_root / "docs" / "project-summary-and-roadmap.md"
        ).read_text(encoding="utf-8")
        legacy_risk_row = next(
            line for line in roadmap.splitlines() if "| legacy 路径仍存在 |" in line
        )

        self.assertIn("未注册 historical Import parser", legacy_risk_row)
        self.assertIn("JRN-011 preview 不调用", legacy_risk_row)
        self.assertIn("JRN-012 confirm 仍关闭", legacy_risk_row)
        self.assertNotRegex(legacy_risk_row, r"仍支撑[^|]*导入")


if __name__ == "__main__":
    unittest.main()
