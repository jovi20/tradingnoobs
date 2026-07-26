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

用户已提供一份真实 IBKR Activity Flex XML。它显著减少了普通成交 wire shape
的不确定性，但只是一份报表，不是完整 provider contract，也不满足 JRN-013 的
全部 evidence exit gate。原文件和脱敏候选只保存在 Git 忽略的私有目录，不能
提交；下文只记录结构和语义结论，不记录账户、身份、标的、成交号或金额。

这不是“每月必须新建账户”的产品决定。目标语义仍是：同一 IBKR external
account 绑定同一内部账户；后续可上传完全重复、区间重叠或纯增量的文件；系统按
稳定 execution identity 只应用新增事实。该用户流程要到 JRN-014 canonical
confirm 完成后才成立，JRN-015 再处理 correction/cancel-bust resolution。

## 真实报表字段评估

该文件包含一个 `FlexStatement`、95 条 execution 级 `Trade` 和 23 条
`OpenPosition`。安全结构检查确认：

- 普通成交使用 `Trade transactionType="ExchTrade"`；方向为 `BUY/SELL`，
  开平为 `O/C`，没有此前 synthetic contract 假设的 `tradeStatus`。
- 95 条成交都有非空且在文件内唯一的 `ibExecID` 和数值 `transactionID`。
  12 条成交共享 timestamp，因此不能只按时间排序；数值 transaction ID 对同时间
  顺序是必要字段。
- quantity 是 provider signed representation：BUY 为正、SELL 为负。parser
  必须按 side 校验符号后规范为正 magnitude，不能继续要求所有原始 quantity
  为正。
- 账户起始日期位于嵌套的 `AccountInformation@dateOpened`，不是
  `FlexStatement` 属性；当前持仓日期位于每条
  `OpenPosition@reportDate`，不是 `OpenPositions` container 属性。
- 本文件的 OpenPositions 是报告期末非零当前仓位，只能作为期末快照，不能证明
  fromDate 空仓；本文件可由 `fromDate <= dateOpened` 提供首次 flat-boundary
  候选证据。
- 79 条 STK/OPT execution 具有日志生命周期所需的 exchange、open/close、
  commission 和 commission currency；其中非零 commission 的符号与交易币种
  关系一致，足以形成脱敏真实候选证据。
- 另有 16 条 `CASH` execution 缺少 listing exchange/open-close，且 commission
  currency 与 trade currency 的含义不同。V1 不能静默忽略这些行，也不能将其
  当作 STK/OPT trade；在另行冻结 authority 与映射前，含这类行的整份报表必须
  fail-closed。

据此，这一份报表可支持 `BASIC_EXECUTION_FIELDS`、
`TRANSACTION_AND_OPEN_CLOSE`、`COMMISSION_SIGN_CURRENCY` 和
`FLAT_BOUNDARY` 的真实 fixture 候选。它不能证明：

- `GENERATION_ORDERING`：只有一次 report generation，没有跨 generation
  overlap 或相同 marker tie 样本。
- `COVERAGE_INCLUSIVITY_TIMEZONE`：没有恰好位于 fromDate 和 toDate 两端本地
  日期的 execution。
- `CORRECTION_CANCEL_TARGETS`：只有 `ExchTrade`，correction/cancel 相关字段
  为空，不能确定 event kind、source identity 和 target identity 的真实关系。

脱敏候选保留 95 条 Trade 和 23 条 OpenPosition，文件权限为 `0600`。二次检查
确认输出属性均在草案 allowlist 内，不含 PII 属性名，不含原账户、标的、conid、
execution/transaction ID 值；报告仍固定标记为
`NOT_PROVIDER_VERIFICATION / human_review_required`。

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
- field contract 现已显式冻结 quantity 是正 magnitude 还是按 side 带符号；
  parser 验证 wire sign 后统一输出正 magnitude。真实 Flex 单节点 85 个属性，
  安全属性上限由 80 调整为 128，同时保持总节点、总属性、字段长度与文件大小门。
- account inception 可从声明的嵌套 element 属性读取，并核对其 account 与
  statement account 一致；OpenPositions snapshot date 可来自 container 或每条
  position，逐 position 日期缺失或不一致均拒绝。report-end 非零仓位允许作为
  观测，但不被误判为 opening flat boundary。
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
- 实现 checkpoint `7743919` 新增只读 provider evidence readiness CLI；它对
  manifest、模板 artifact、官方 artifact/hash/quote/exact wire token 和逐语义
  fixture 运行与 route 相同的机器 gate，输出稳定 JSON 和精确 blocker，不输出
  Query Template ID、不修改 manifest，也不能自行升级 `UNVERIFIED`。
- `4db098c` 对齐真实 Flex wire shape；全部 `test_jrn013_*.py` 共 157 项通过。
  当前 worktree 完整统一 gate 在 PostgreSQL 16.14 上通过 698 个后端测试、
  165 个前端测试、OpenAPI、release contract、typecheck、lint 和 production
  build。包含实现与本评审的 `5f7f02f` 已由 GitHub Actions run
  `30188490363`、job `89757262465` 通过相同 Journal Baseline。

## 尚未实现或未满足

- 没有已冻结的真实 Flex Query 模板及其 hash。
- 已有一份真实 statement 和私有脱敏候选，但没有冻结 Query 模板配置/hash，也
  没有来自同一模板的 statement pairs。该文件只能候选证明普通 STK/OPT execution、
  transaction/open-close、commission 和 account inception flat boundary，不能
  证明跨 generation overlap、correction/cancel target 或 coverage 端点语义。
- 同一文件含 16 条 `CASH` execution，当前 STK/OPT lifecycle contract 无法完整
  消费。产品策略必须选择并用 provider evidence 冻结：V1 明确只接受不含 CASH
  execution 的专用 Query 模板，或新增独立的 cash-event authority/mapping；在此
  之前不得过滤后继续导入其余行。
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
- `4db098c` 已通过本地完整统一 gate 与真实 PostgreSQL migration gate，并由
  `5f7f02f` 的远端 CI 覆盖；尚未取得完整 provider evidence 和绑定最终 SHA 的
  独立 review，因此仍只能视为进度 checkpoint。

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

1. 在 Client Portal 保存专用 Activity Flex Query，记录非 secret 的字段/section
   配置并计算 hash；模板应只输出 adapter 承诺支持的资产/事件。不要提交 Token、
   Query ID、账户信息或原始报表。
2. 用同一模板再导出至少一份与当前报表日期区间重叠、generation 更晚的 statement，
   并取得包含 coverage 首尾本地日期成交的样本；如模板可排除 CASH execution，
   同时验证排除规则真实生效。
3. 从同一模板取得 correction 与 cancel/bust 真实样本，或从 IBKR 正式支持渠道
   取得 raw XML event kind、source event ID 和 target execution ID 的书面确认。
   不应为了造证据故意进行真实交易；可以使用历史上确有更正/撤单的报表或 paper
   account 可验证样本。
4. 将这些样本与当前普通成交样本组成最小脱敏 fixture 集。先用
   `backend/scripts/redact_ibkr_flex_evidence.py` 生成候选，再按开发者指南逐文件
   人工检查；工具报告不等于 provider verification。
5. 为每项必需语义保留 IBKR 官方字段合同的 URL、取得日期、UTF-8 artifact、
   SHA-256、locator 与逐字引用，并把 parser 实际消费的 element/attribute 名和
   枚举值绑定为 exact `wire_tokens`；重点先冻结 correction/cancel 的真实元素/
   discriminator、source identity、target identity、`openCloseIndicator` 值和
   status 字段。公开材料无法证明的语义必须通过正式支持渠道确认，不能只用 fixture
   或第三方 parser 猜合同。
6. 填充 evidence manifest，运行 artifact/hash/semantic gate、全部 JRN-013 测试、
   真实 PostgreSQL migration gate和统一 gate；readiness gate 的标准命令为
   `backend/venv/bin/python backend/scripts/verify_ibkr_flex_evidence.py
   --pretty`。再取得同一 SHA 独立评审。
7. 只有第 6 步通过才允许 evidence-first route 进入 owner-bound upload/preview，
   并在前端开放入口、关闭 JRN-013。
8. 按 JRN-014 实现同 binding 的重复、重叠、增量 canonical confirm；验证同一
   账户按月导入不会重复记账，也不需要新建内部账户。
9. 按 JRN-015 实现 correction/cancel-bust resolution；完成前相关文件继续
   fail-closed，不做近似映射。

## 评审判定

`APPROVE_IMPLEMENTATION_DIRECTION_WITH_EXTERNAL_EVIDENCE_BLOCKER`

新增一个 P0 provider-contract blocker，但不要求回退 source-truth、preview 或
fail-closed 基础设施：现有 parser 的 correction/cancel wire shape 尚未被证明，
并可能与真实 Flex XML 不兼容。阻断项是取得 raw-wire 官方证据后修正 field
contract/parser、补齐真实 provider evidence、完成 release gate，以及尚属
JRN-014/JRN-015 的确认和纠错功能。产品状态继续为
`NOT_READY_FOR_PRODUCTION`。
