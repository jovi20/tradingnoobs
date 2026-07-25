# JRN-013 进度与设计评审

日期：2026-07-26
评审范围：`0b03f85..87970b7` 的 JRN-013 实现，以及 active plan 中
`JRN-013` 至 `JRN-015` 的 IBKR Flex 文件导入设计。

## 结论

`JRN-013` 已完成大部分内部实现，但不能关闭，也不能向用户开放。

当前代码已经具备 source truth schema、安全 XML parser、provider evidence
机器门、未绑定和已绑定 preview、生命周期模拟复用、持久 projection、上传编排、
清理与边界测试。`POST /api/positions/import/ibkr-flex/upload` 已发布机器合同，
但它在文件 staging 前强制验证 provider evidence；默认 manifest 仍为
`UNVERIFIED`，因此稳定返回 `404 FEATURE_DISABLED` 且不创建临时文件或数据库
记录。前端没有该入口，`IBKR_FLEX_XML_V1` 继续保持 fail-closed。

这不是“每月必须新建账户”的产品决定。目标语义仍是：同一 IBKR external
account 绑定同一内部账户；后续可上传完全重复、区间重叠或纯增量的文件；系统按
稳定 execution identity 只应用新增事实。该用户流程要到 JRN-014 canonical
confirm 完成后才成立，JRN-015 再处理 correction/cancel-bust resolution。

## 已实现

- `c9d0e1f2a3b4`、`d0e1f2a3b4c5`、`e1f2a3b4c5d6` 三个线性 migration：
  source binding、statement、observation、sighting、execution、application、
  reconciliation case、coverage acceptance、preview digest 与 owner FK。
- 版本化且可校验的 provider-evidence manifest；模板、官方语义、真实 fixture、
  hash 或必需语义缺失时稳定拒绝。官方来源必须属于 IBKR 官方站点、guides、
  campus 或官方 GitHub，并留存 UTF-8 artifact、SHA-256、locator 和逐字引用；
  只填写 URL/semantic 标签不能通过。
- 禁止 DTD/entity/XInclude 的受限 XML parser，以及文件、execution、节点、
  属性、深度和字段长度限制；5,000 execution 边界接受，5,001 拒绝。
- provider contract 固定 generation 按 UTC instant 升序；同一 binding 下同一
  generation marker 对应不同文件时返回 `SOURCE_GENERATION_CONFLICT`。有 execution
  时创建持久 reconciliation case，空 statement 也保持 session-level conflict，
  不把 tie 猜成先后关系。
- 同一文件即使使用不同 upload key 重传，也复用 statement、observation 与
  sighting；同一 statement 内同 event ID、不同 fingerprint 则先于 order/target
  分支稳定归为 `SOURCE_PAYLOAD_CONFLICT`，每个 observation/sighting 均永久保留。
- accepted correction/cancel-bust 的 exact sighting 归为 `ALREADY_IMPORTED`；
  strict-earlier 新 payload 为 `STALE_SOURCE_OBSERVATION`，同 identity 的新
  fingerprint 为 conflict。严格更晚冲突会收口旧 OPEN/DIVERGED episode、链接
  winning sighting，并为仍冲突的 payload 建立新 OPEN episode。
- fingerprint payload 字段集合与 provenance/derived 排除项已锁定；fingerprint
  version 改变时创建新 observation 并 fail-closed 为 conflict，不静默匹配旧版本。
- parser 对齐永久 source schema 的字段宽度：external account/event/target/transaction
  为 255，conid/status 为 100，currency 为 10，组合 order key 为 512；超限在
  数据库写入前稳定返回 `IBKR_FIELD_TOO_LONG`。
- 同 owner 的两个 CLEAN 内部账户可同时 preview 同一 external account，两个
  preview 均不提前创建 binding；未知资产只产生 session-only terminal conflict。
- terminal normalized preview rows 在第 30 天前一微秒仍保留、恰好第 30 天
  才可批量清理；cleanup 不删除 ImportSession、idempotency、binding、statement、
  observation 或 sighting。OpenAPI 明确不发布 confirm/rebind/transfer/binding
  mutation 路由。
- binding、observation、sighting、execution 与 reconciliation case 的 owner
  graph 由数据库复合外键兜底；逐表跨用户改写均被拒绝，公开 ImportSession ID
  继续使用 owner-first 404。
- bound preview digest 已升级到 schema version 2，canonical payload 直接覆盖
  accepted execution disposition、current/canceled observation fingerprint 和
  active application；revision、authority、tombstone 或 group boundary 改变均会
  使旧 preview digest 失效。
- source identity、fingerprint、flat-boundary、coverage、bootstrap change-chain、
  bound preview、冲突 episode 和生命周期模拟基础。
- operation idempotency、owner/account 绑定、并发 session/rate limit、临时文件
  权限与清理路径。
- provider-gated 本地文件 upload API、双 adapter session DTO、跨 owner session
  deny 和 `CONFLICTED` preview 重启后行明细恢复；IBKR preview 永远不误报
  `confirm_available`。
- 本次复验的全部 `test_jrn013_*.py` 共 115 项测试通过；完整统一
  gate 在 PostgreSQL 16.14 上通过 656 个后端测试、165 个前端测试、OpenAPI、
  release contract、typecheck、lint 和 production build。

## 尚未实现或未满足

- 没有已冻结的真实 Flex Query 模板及其 hash。
- 没有同时来自该模板的脱敏真实 statement pairs，无法证明跨 generation
  overlap、flat boundary、correction/cancel target、commission 与 coverage
  语义。
- 已查阅的公开 IBKR 材料只能证明 Flex Query 的字段和生成方式取决于 Client
  Portal 中保存的模板；当前没有保留下足以逐字段证明 `ibExecID`、generation
  严格顺序、change target 和日期包含性的官方合同。不能据此猜测。
- `backend/app_config/ibkr_flex_v1_provider_evidence.json` 因而保持
  `UNVERIFIED`；已发布 route 因 evidence-first gate 保持不可用。
- JRN-014 的 source-bound canonical confirm、coverage acceptance/frontier
  推进与“只应用新增 execution”尚未实现。
- JRN-015 的人工 correction/cancel-bust resolution 与 versioned replay 尚未实现。
- `87970b7` 已通过当前工作树完整统一 gate 与真实 PostgreSQL migration gate；
  尚未取得远端 CI 和绑定该 SHA 的独立 review，因此仍只能视为进度 checkpoint。

## 设计必要性评估

对交易日志 Beta，以下设计是必要的：

- 稳定 external account 与 execution identity，否则重叠/月度文件无法可靠去重。
- statement coverage 与 execution identity 分离，否则“没有重复”会被误当成
  “中间没有漏单”。
- owner/account binding、永久 idempotency、审计记录和 fail-closed parser。
- preview 与 canonical confirm 分离，并复用同一交易 lifecycle 规则。

以下设计有意偏重，但作为未来量化底座仍合理：

- immutable observation/sighting 与 versioned application 能保留数据来源和修订
  历史，未来回测才能回答“当时知道了什么”和“后来为何改变”。
- reconciliation episode 与 authority lineage 能防止 correction/cancel 被当成
  新成交，避免仓位、费用和 PnL 静默漂移。

控制复杂度的边界：

- 当前只做本地文件 adapter，不做 Token、网络同步或后台调度。
- JRN-013 只允许 schema/parser/preview；没有 provider evidence 时 route 必须在
  staging 前返回 `FEATURE_DISABLED`，前端不展示入口。
- JRN-014 只做可证明的新 execution confirm；JRN-015 才启用 correction resolution。
- 不把 provider 特有字段扩散到 canonical journal；量化能力继续消费 canonical
  events、ledger 和 source provenance。

## 后续开发计划

1. 由真实 IBKR 账户在 Client Portal 冻结专用 Flex Query 模板，导出模板配置并
   记录 hash；不要提交 Token、Query ID secret 或未脱敏账户信息。
2. 从同一模板取得最小脱敏 fixture 集：基础成交、两个有重叠区间且 generation
   不同的 statement、账户 inception 或完整空 OpenPositions、correction/cancel
   样本、commission/currency 和无成交 coverage 样本。
3. 为每项必需语义保留 IBKR 官方字段合同的 URL、取得日期、UTF-8 artifact、
   SHA-256、locator 与逐字引用；公开材料无法证明的语义必须通过正式支持渠道
   确认，不能只用 fixture 猜合同。
4. 填充 evidence manifest，运行 artifact/hash/semantic gate、全部 JRN-013 测试、
   真实 PostgreSQL migration gate和统一 gate；再取得同一 SHA 独立评审。
5. 只有第 4 步通过才允许 evidence-first route 进入 owner-bound upload/preview，
   并在前端开放入口、关闭 JRN-013。
6. 按 JRN-014 实现同 binding 的重复、重叠、增量 canonical confirm；验证同一
   账户按月导入不会重复记账，也不需要新建内部账户。
7. 按 JRN-015 实现 correction/cancel-bust resolution；完成前相关文件继续
   fail-closed，不做近似映射。

## 评审判定

`APPROVE_IMPLEMENTATION_DIRECTION_WITH_EXTERNAL_EVIDENCE_BLOCKER`

未发现要求回退现有 JRN-013 内部实现的 P0/P1 问题。阻断项是产品合同本身要求的
真实 provider evidence、完整 release gate，以及尚属 JRN-014/JRN-015 的确认和
纠错功能。产品状态继续为 `NOT_READY_FOR_PRODUCTION`。
