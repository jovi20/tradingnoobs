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

    def test_generic_import_document_is_only_an_unregistered_historical_reference(self):
        import_reference = (
            self.repository_root / "docs" / "import-template.md"
        ).read_text(encoding="utf-8")

        for required_boundary in (
            "`GENERIC_BOOTSTRAP` 尚未实现",
            "Historical unregistered legacy parser reference",
            "`POST /api/positions/import/upload`",
            "`POST /api/positions/import/confirm`",
            "`GET /api/positions/import/template`",
            "`404 FEATURE_DISABLED`",
            "不进入 OpenAPI",
            "当前不提供通用导入模板下载、文件上传、preview 或 confirm",
            "直达 `/positions/import` 进入 framework not-found 视图",
            "不是当前主要页面",
        ):
            with self.subTest(required_boundary=required_boundary):
                self.assertIn(required_boundary, import_reference)

        misleading_patterns = {
            "zh_current_support_or_output": r"(?:当前|目前)(?:已经)?(?:支持|输出|提供)(?:[^。\n]{0,40})(?:CSV|Excel|模板|导入|列)",
            "zh_upload_or_confirm_behavior": r"(?:上传时|上传后|确认导入时|confirm 时)(?:[^。\n]{0,20})(?:会|将)(?:解析|返回|写入|导入|持久化)",
            "zh_financial_write_claim": r"(?:校验通过|已选择|有效)(?:[^。\n]{0,25})(?:会|将)(?:写入|导入|入账)",
            "en_current_support_or_output": r"(?i)\bcurrently (?:supports?|outputs?|returns?|provides?)\b",
            "en_upload_or_confirm_behavior": r"(?i)\b(?:on upload|on confirm(?:ation)?)\b[^.\n]{0,40}\b(?:will|writes?|persists?|imports?)\b",
            "en_financial_write_claim": r"(?i)\b(?:valid|selected) rows?\b[^.\n]{0,40}\b(?:will be )?(?:written|imported|persisted)\b",
        }
        for claim, pattern in misleading_patterns.items():
            with self.subTest(claim=claim):
                self.assertIsNone(re.search(pattern, import_reference))

        for misleading_phrase in (
            "## 支持文件类型",
            "## 当前模板列",
            "当前输出以下列名",
            "当前后端模板",
            "上传时系统会",
            "确认导入时写入",
            "currently supported",
            "currently returns",
            "will be written",
        ):
            with self.subTest(misleading_phrase=misleading_phrase):
                self.assertNotIn(misleading_phrase, import_reference)

        historical_field_table = import_reference.split("## 历史字段表", 1)[1].split(
            "## 历史样例行", 1
        )[0]
        historical_field_rows = [
            line for line in historical_field_table.splitlines() if line.startswith("| `")
        ]
        self.assertEqual(14, len(historical_field_rows))
        for field_row in historical_field_rows:
            with self.subTest(field_row=field_row):
                self.assertIn("旧 parser 曾", field_row)

    def test_developer_guide_excludes_disabled_import_ui_and_freezes_legacy_mutations(self):
        developer_guide = (
            self.repository_root / "docs" / "DEVELOPER_GUIDE.md"
        ).read_text(encoding="utf-8")
        current_pages = developer_guide.split("前端当前主要页面：", 1)[1].split(
            "前端 legacy DTO 边界：", 1
        )[0]

        self.assertNotIn("- `/positions/import`", current_pages)
        self.assertIn("`GENERIC_BOOTSTRAP` 同样尚未实现", developer_guide)
        self.assertIn("当前仅由 deny-only stub 返回 `404 FEATURE_DISABLED`", developer_guide)
        self.assertIn("不进入 OpenAPI，也不提供模板、上传、preview 或 confirm", developer_guide)
        self.assertIn("`/positions/import` 只是调用 `notFound()` 的禁用壳", developer_guide)

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

    def test_active_metrics_do_not_treat_legacy_commission_parser_as_live_import(self):
        metrics = (
            self.repository_root / "docs" / "trading-metrics.md"
        ).read_text(encoding="utf-8")

        self.assertIn("状态：`部分实现 / Import fee 未实现`", metrics)
        self.assertIn("`GENERIC_BOOTSTRAP` 尚未实现", metrics)
        self.assertIn("三条 legacy Import API 当前仅返回 `404 FEATURE_DISABLED`", metrics)
        self.assertIn("未注册 legacy parser 代码中保留的 `commission` 解析分支", metrics)
        self.assertIn("只是一项 historical reference", metrics)
        self.assertIn("不是当前 Import 路径，也不会产生 canonical fee 写入", metrics)
        self.assertIn("`JRN-011`/`JRN-012` 必须按单 event 聚合 fee", metrics)
        self.assertNotIn("导入流程支持解析 `commission`", metrics)
        self.assertIsNone(
            re.search(
                r"(?:当前|现有)?导入流程[^。\n]{0,30}(?:支持|已经|会)[^。\n]{0,20}`?commission`?",
                metrics,
            )
        )

    def test_active_roadmap_does_not_describe_legacy_import_as_reachable(self):
        roadmap = (
            self.repository_root / "docs" / "project-summary-and-roadmap.md"
        ).read_text(encoding="utf-8")
        legacy_risk_row = next(
            line for line in roadmap.splitlines() if "| legacy 路径仍存在 |" in line
        )

        self.assertIn("未注册 historical Import parser", legacy_risk_row)
        self.assertIn("不存在可达 Import 路径", legacy_risk_row)
        self.assertNotRegex(legacy_risk_row, r"仍支撑[^|]*导入")


if __name__ == "__main__":
    unittest.main()
