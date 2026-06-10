# Release And Rollback Playbook

更新时间：2026-06-10
当前执行分支：`dev`

本 playbook 记录 P11/P12 后的可操作发布与回滚边界。目标不是替代测试，而是在发布窗口里快速判断“正常路径是什么、先切哪个开关、最后才回滚哪段提交”。

---

## Truth Writes

正常路径：
- 新建仓位仍经过 `POST /api/positions` 的 create-and-sync 过渡合同，并返回 `truth_position_public_id`。
- 已有仓位的加仓、减仓、平仓走 `POST /api/trading-positions/{position_public_id}/events`。
- 复盘与叙事写入走 `PATCH /api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`。
- 前端普通操作不应调用 legacy batch/review 写入，除非明确处于 migration/support fallback。

迁移 fallback：
- `legacy-batch-write` 只用于 legacy batch create 迁移补录。
- `legacy-review-write` 只用于 legacy `Position.trade_review / lessons / rating` 迁移修正。

安全回滚顺序：
- 先确认 `frontend/tests/legacy-ui-boundaries.test.mts` 没有被绕过，避免新页面继续扩张 legacy DTO。
- 如用户操作被阻塞，优先临时切回迁移/support 操作入口，而不是扩大普通 legacy 写路径。
- 如必须回滚代码，按最新到最旧逐个回滚 P11 行为提交并逐步验证：`b06f231`、`715816f`、`e9fbafe`、`a7fa1da`、`5a70275`。
- 每回滚一段后至少运行 truth lifecycle、legacy bridge、frontend boundary 三组回归。

---

## Timeline Snapshot Rollback

正常模式：
- `/api/timeline/home` 默认是 `SNAPSHOT_ONLY`。
- Timeline events 与 Review Inbox 默认从 `DerivedTimelineSnapshot`、truth lifecycle、auditable insight artifacts 读取。
- UI 正常标签应显示 `Snapshot-first truth/snapshot read model`。

回滚开关：
- 启用 feature flag `timeline_legacy_mixed_feed_enabled` 可恢复 legacy mixed feed。
- 回滚后 UI 应显示 `Legacy mixed fallback enabled`，让用户和排障人员知道当前不是默认 truth/snapshot 模式。

安全回滚顺序：
- 先启用 `timeline_legacy_mixed_feed_enabled`，不要先删除 snapshot 数据或修改 derived refresh。
- 验证 `/api/timeline/home`、`/`、`/timeline` 仍能加载，并确认 Review Inbox 没有丢失关键行动卡片。
- 如果 feature flag 不能恢复，再按需回滚 `2c82e54 feat: default timeline to truth snapshots`。
- 浏览器验证需要登录态；若未登录只覆盖到 `/login`，不能视为完整 Timeline smoke。

---

## Legacy Mutation Guards

以下 header 只能用于 migration/support，不是普通产品路径：
- `legacy-batch-write`：允许 legacy batch create 迁移补录。
- `legacy-review-write`：允许 legacy review 字段迁移修正。
- `legacy-position-delete`：允许 legacy position hard delete 迁移清理。
- `legacy-batch-edit`：允许 legacy batch edit/delete 迁移修正。

默认保护：
- truth lifecycle 存在时，普通 legacy batch create、legacy review write、position hard delete、batch edit/delete 应返回 `409`。
- `DELETE /api/positions/{position_id}` 不应成为 audited truth lifecycle 的普通删除方式。
- legacy batch edit/delete 不应替代 truth event reversal、manual adjustment 或未来 compensating event UX。

安全回滚顺序：
- 先确认是否只是 migration/support 操作缺少正确 header。
- 再确认用户是否实际应走 truth route 或 narrative route。
- 只有历史数据清理确实被阻塞时，才在受控调用里使用对应 `X-Migration-Fallback` 值。
- 如必须回滚 guard，逐个回滚 `715816f`、`e9fbafe` 或 `5a70275` 的相关保护，并保留 P12 OpenAPI contract tests，避免 header 文档消失。

---

## Verification

发布或回滚后至少运行：

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
cd ../frontend
node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts tests/generated-contracts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```
