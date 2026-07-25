# JRN-013 进度与设计评审

日期：2026-07-26
评审范围：截至 2026-07-26 当前 `dev` checkpoint 的 JRN-013 实现，以及
active plan 中 `JRN-013` 至 `JRN-015` 的 IBKR Flex 文件导入设计。

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
- IBKR 官方 Trades Flex Reference 已作为 hash-bound UTF-8 artifact 入库，并以
  精确 field-table 引用覆盖 `BASIC_EXECUTION_FIELDS`；测试证明 artifact/hash/quote
  完整，且缺失语义列表不再误报该项。该部分证据不证明 execution identity 稳定性、
  generation、coverage、correction target 或 commission sign。
- provider evidence gate 进一步要求 `VERIFIED` field contract 消费的全部 raw
  XML element/attribute 名和 parser 枚举值，必须作为 `wire_tokens` 逐字出现于
  hash-bound 官方摘录。只有语义标签、展示层字段表或真实 fixture 不能激活 adapter；
  未声明 token 与声明但 quote/artifact 中不存在的 token 都会 fail-closed。
- field contract 不再硬编码 event element shape 或 `BUY/SELL`、`OPEN/CLOSE`：
  manifest 必须显式选择 `ELEMENT_NAME` 或 `ATTRIBUTE_VALUE` discriminator，并冻结
  ordinary/correction/cancel、side 与 open-close 的 provider wire 值。parser 只按
  该合同分类并规范为 canonical `TRADE/CORRECTION/CANCEL_BUST`、`BUY/SELL` 和
  `OPEN/CLOSE`；未知 discriminator/value 稳定拒绝。混用两种策略、缺少值或重复值
  在 manifest 校验阶段拒绝。
- statement/generation/execution 的 source-timezone 语义、execution status 来源和
  change identity 模式也必须显式冻结。status 可来自 provider attribute，或在真实
  wire 没有该字段时由已验证 event kind 派生；change 可使用独立 event/target ID，
  或声明 event ID 即 target。未被所选合同消费的 `tradeStatus/affectedIBExecID`
  不再被误列为必需 wire token。
- IBKR 官方 Flex Codes 页面已作为第二份 hash-bound artifact 入库，准确保留
  `Ca=Cancelled`、`Co=Corrected Trade`、`O=Opening Trade`、`C=Closing Trade`。
  它只计为 `EVENT_CODE_VALUES` supporting evidence，不会满足
  `CORRECTION_CANCEL_TARGETS`，也不会把孤立 `O/C` 误当成
  `openCloseIndicator="O|C"` 的证明。枚举 wire evidence 必须绑定字段和值片段，
  例如 `transactionType="TradeCorrect"`。
- commission charge sign 与 commission/trade currency 关系已成为 field contract
  的显式必填项；parser 对非零反向 sign 稳定返回
  `IBKR_COMMISSION_SIGN_UNSUPPORTED`，只有符合合同的费用才规范为正 magnitude。
  evidence fixture 必须提供 finite non-zero commission、正确 sign 和相同 currency，
  不能再用两个字段存在冒充 `COMMISSION_SIGN_CURRENCY`。
- `FLAT_BOUNDARY` fixture gate 已对齐 parser：inception 仅在
  `fromDate <= accountInceptionDate` 时有效；否则必须恰好有一个 snapshotDate 等于
  fromDate 的 OpenPositions，子元素类型/账户必须一致且每个 quantity 都是 finite
  zero。旧日期 inception、非零仓位、非法数量或不完整 snapshot 均不能证明空仓。
- `COVERAGE_INCLUSIVITY_TIMEZONE` fixture 不再只检查日期可解析；必须在冻结的本地
  日期语义下出现 coverage 两端的实际成交。`CORRECTION_CANCEL_TARGETS` 必须同时有
  correction 与 cancel，符合冻结的 same-ID/distinct-ID 关系，并把每个 target
  链接到同一 evidence set 中实际出现的 trade execution。
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
- parser 在永久 source truth 写入前执行 instrument identity 宽度门：
  `symbol <= 50`、`listingExchange <= 32`，分别对齐 PostgreSQL symbol 列宽和
  冻结 release identity 合同。
- source identity、fingerprint、flat-boundary、coverage、bootstrap change-chain、
  bound preview、冲突 episode 和生命周期模拟基础。
- operation idempotency、owner/account 绑定、并发 session/rate limit、临时文件
  权限与清理路径。
- provider-gated 本地文件 upload API、双 adapter session DTO、跨 owner session
  deny 和 `CONFLICTED` preview 重启后行明细恢复；IBKR preview 永远不误报
  `confirm_available`。
- upload 编排在读取或暂存文件前先锁定 owner-scoped account；不存在或跨 owner
  account 均返回 `404 IMPORT_ACCOUNT_NOT_FOUND`，不调用上传读取、不创建临时文件、
  `IdempotencyKey` 或 `ImportSession`，并始终关闭上传句柄。
- 新增真实 Flex fixture 脱敏工具：按 draft field contract 做跨 statement 一致
  identity alias，只保留合同消费的 statement 子树与属性，删除自由文本、注释、
  PI、未知子树及未消费属性；拒绝 DTD/entity/XInclude、XML namespace、符号链接、
  非普通文件和超限输入。输出目录/文件固定为 `0700/0600`，exclusive create，
  中途失败不遗留 partial output。
- 脱敏报告固定为 `NOT_PROVIDER_VERIFICATION`、`REDACTED_REAL_CANDIDATE` 和
  `human_review_required=true`，不保存源文件名、源 hash 或 alias mapping，也没有
  能将 provider manifest 升为 `VERIFIED` 的路径。开发者指南已增加命令和提交前
  人工隐私复核清单。
- 实现 checkpoint `ba490a4` 的全部 `test_jrn013_*.py` 共 152 项通过；完整统一
  gate 在 PostgreSQL 16.14 上通过 693 个后端测试、165 个前端测试、OpenAPI、
  release contract、typecheck、lint 和 production build。

## 尚未实现或未满足

- 没有已冻结的真实 Flex Query 模板及其 hash。
- 没有同时来自该模板的脱敏真实 statement pairs，无法证明跨 generation
  overlap、flat boundary、correction/cancel target、commission 与 coverage
  语义。
- 已保留的官方 Trades Flex Reference 能证明基础字段的存在和含义；Flex Web
  Service 文档还能证明报告由 Client Portal 中预配置模板生成。但当前仍没有足以
  证明 `ibExecID` 唯一稳定性、generation 严格顺序/tie、数值 transaction order、
  correction/cancel target、commission sign/currency、flat boundary 和 coverage
  inclusivity/timezone 的完整官方合同。不能用字段存在替代这些语义证明。
- **P0 provider-contract blocker：**现有 synthetic fixtures 假设 correction 与
  cancel 是独立 `TradeCorrection/TradeCancel` 元素，以
  `sourceEventID/affectedIBExecID` 关联目标，并使用 `tradeStatus` 和
  `OPEN/CLOSE`；可配置 parser 已能表达 attribute discriminator、可选 status 和
  same-ID/distinct-ID change identity，但默认 manifest 尚未选择任何真实 field
  contract。IBKR 官方 Trades Reference
  没有证明上述 raw XML 名或枚举值，
  且其 “Original Trade ID”等取消字段与公开第三方 parser 暴露的
  `Trade transactionType=TradeCorrect|TradeCancel`、original/related ID、`O/C`
  形状均提示当前假设可能错误。第三方实现不是 release evidence，因此现在既不能
  按它选择“真实合同”，也不能把任何 synthetic contract 视为 provider-ready。
  必须先取得同一冻结 Query 的真实 correction/cancel 样本和 IBKR 官方 raw-wire
  合同，再决定 field contract/parser 重构。
- `backend/app_config/ibkr_flex_v1_provider_evidence.json` 因而保持
  `UNVERIFIED`；已发布 route 因 evidence-first gate 保持不可用。
- JRN-014 的 source-bound canonical confirm、coverage acceptance/frontier
  推进与“只应用新增 execution”尚未实现。
- JRN-015 的人工 correction/cancel-bust resolution 与 versioned replay 尚未实现。
- `ba490a4` 已通过完整统一 gate 与真实 PostgreSQL migration gate；尚未取得
  远端 CI、真实 provider evidence 和绑定该 SHA 的独立 review，因此仍只能视为
  进度 checkpoint。

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
   样本、commission/currency 和无成交 coverage 样本。先用
   `backend/scripts/redact_ibkr_flex_evidence.py` 生成候选，再按开发者指南逐文件
   人工检查；工具报告不等于 provider verification。
3. 为每项必需语义保留 IBKR 官方字段合同的 URL、取得日期、UTF-8 artifact、
   SHA-256、locator 与逐字引用，并把 parser 实际消费的 element/attribute 名和
   枚举值绑定为 exact `wire_tokens`；重点先冻结 correction/cancel 的真实元素/
   discriminator、source identity、target identity、`openCloseIndicator` 值和
   status 字段。公开材料无法证明的语义必须通过正式支持渠道确认，不能只用 fixture
   或第三方 parser 猜合同。
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

新增一个 P0 provider-contract blocker，但不要求回退 source-truth、preview 或
fail-closed 基础设施：现有 parser 的 correction/cancel wire shape 尚未被证明，
并可能与真实 Flex XML 不兼容。阻断项是取得 raw-wire 官方证据后修正 field
contract/parser、补齐真实 provider evidence、完成 release gate，以及尚属
JRN-014/JRN-015 的确认和纠错功能。产品状态继续为
`NOT_READY_FOR_PRODUCTION`。
