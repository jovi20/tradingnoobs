# Trading Journal Launch-Safe Development Plan

计划日期：2026-07-16
最后修订：2026-07-17
执行分支：`dev`
计划状态：`REVIEWED_APPROVE_WITH_BLOCKERS`
当前发布判断：`NOT_READY_FOR_PRODUCTION`
目标发布形态：`INVITE_ONLY_TRADING_JOURNAL_BETA`

## 1. 文档权威关系

- `docs/design-implementation-gap-plan-2026-07-15.md` 是完整审计基线、风险登记册和 Gap ID 来源。
- 本文是当前唯一 active implementation plan，只负责交易日志范围、任务顺序和验收。
- `docs/TODO.md` 只摘录本文当前执行批次，不复制完整任务清单。
- `docs/project-summary-and-roadmap.md` 只维护产品方向和中期阶段。

本文不要求逐项实现原 gap。未进入本 release profile 的能力统一记为 `DEFERRED_BY_SCOPE`，不能记为 `IMPLEMENTED` 或 `CLOSED`。

`REVIEWED_APPROVE_WITH_BLOCKERS` 表示 2026-07-17 的 source-bound incremental Import 修订及后续首次零成交 binding-effective 澄清，已随 JRN-001 精确 checkpoint 取得覆盖该语义 plan blob 的双路独立批准；旧版 plan verdict 不自动沿用。该状态只批准开发计划，不表示后续功能已实现或产品可发布。所有 `Beta 阻断=是` 的任务与 JRN-021 人工批准仍是 release blocker。

## 2. 目标、架构判断与原则

目标是在现有模块化单体上交付一个可安全邀请真实用户使用的交易日志：用户可以记录、复盘、纠错和导出自己的交易数据；系统不能越权、重复、半写、静默混算或物理抹除已入账事实，并能在 PostgreSQL staging 上备份和恢复。

当前阶段没有必要建设量化平台式基础设施。必需拓扑只有 `Next.js + FastAPI + PostgreSQL`；现有 DB outbox/worker 可以保留为非权威 derived accelerator，但核心记账和读取不能依赖 worker 存活。若同步计算或按需重建能满足冻结的 SLA，就不为 Beta 强制部署常驻 worker。

执行原则：

1. 正确性优先于功能数量，先保证成交、费用、资金流水和持仓可重放、可对账。
2. `TradingPosition + PositionEvent + AccountLedgerEntry` 是 canonical truth；legacy 只允许迁移读取或同事务 projection。
3. 功能要么达到启用门，要么 API、UI、secret、job 和文档同时关闭。
4. 不引入 Redis、Kafka、微服务、多 schema 或新的事件平台。
5. 行情、风险、AI 和量化能力不能改写交易事实，也不能成为手工记账依赖。
6. 每个任务同时交付代码、自动化测试、迁移/回滚说明和必要文档。

## 3. Beta Release Profile

### 3.1 默认启用

| 能力 | Beta 边界 |
|---|---|
| 用户 | 单次、限时、哈希存储且受审计的邀请码；无公共共享码；管理员辅助找回密码。 |
| 账户 | 多账户；一个部署只允许一个 base currency，`JRN-001` 必须在会计实现前冻结确切币种和存量处理。账户首次产生 opening balance、交易、资金流水或 ledger 后币种不可改。 |
| 标的 | 只记录满足 `quantity * price` 语义的 `SPOT` 股票、基金/ETF 和现货加密资产；报价币种必须等于账户币种。身份至少包含 asset type、market/exchange 和 symbol。 |
| 交易 | 手工 `OPEN / ADD / REDUCE / CLOSE`、long/short、FIFO、费用、计划、情绪、checklist snapshot、叙事和复盘。系统不建模保证金、结算现金或 buying power。 |
| 持仓模式 | 固定为 `HEDGE_BY_DIRECTION`：同账户、同 instrument 可同时存在一个 long 和一个 short active lifecycle；同方向已有 active lifecycle 时再次 OPEN 返回 409，必须使用 ADD；系统不自动 net。 |
| 资金 | opening balance、deposit、withdrawal、account fee、interest；所有修正通过 reversal/void。原子双边 transfer 未完成前关闭 transfer。 |
| 公司行为 | 只启用同币种手工 cash dividend，并进入 ledger/reversal；stock split 和其他公司行为全部关闭。 |
| 通用导入 | canonical CSV/Excel 只用于一次性 bootstrap，可导入开放或已平仓 lifecycle；只有 `generic_bootstrap_eligible` 账户可执行非 noop confirm。普通文件自带的任意“交易 ID”不自动获得可信 source 身份。 |
| Source-bound 导入 | 仅启用机器 allowlist 中的 `IBKR_FLEX_XML_V1` 文件 adapter；首次 binding-effective confirm（至少一个 effective execution，或零成交但有 flat-boundary evidence 与有效 coverage）建立不可变 source binding。JRN-013 至 015 完成后，同一 IBKR external account 必须可向同一内部账户上传完全重复、窗口重叠或纯增量文件并只确认新增 execution，不要求每月新建账户。 |
| 复盘 | Timeline、Lifecycle、每日随笔、策略、规则/checklist、基础 realized Dashboard。 |
| 导出 | canonical 交易事件、资金 ledger、策略/checklist、日记和账户数据的 Unicode CSV/JSON 可携带导出。 |

同一账户内的成交、手续费、dividend 和资金流水币种必须等于账户 base currency，不满足时返回 422；`USDT` 不能静默等同于 `USD`。期权、期货、FX、债券应计、margin、stock split 和自动公司行为不在 Beta 范围。

Beta 的资金口径不是券商结算现金。用户可见名称统一为 `journal balance`：

```text
journal_balance = opening_balance
                + deposits - withdrawals
                + interest + cash_dividends
                + realized_pnl_gross
                - trade_fees - account_fees
                + compensating_reversals
```

交易名义本金不进出该余额。`cash_balance/current_balance` 只能作为待迁移的兼容字段，不能继续在 UI、API 或指标中被描述为真实 cash、NAV 或 buying power。

### 3.2 默认关闭

| 能力 | Gap 来源 | 重新启用条件 |
|---|---|---|
| 在线 Broker Sync | GAP-P1-03 | 账户映射、受管凭据、sync lock/idempotency、冲突预览、确认和 canonical/ledger 原子写入完成。Beta 的 source-bound statement 文件导入属于 Import，不启用网络拉取、Token 存储或后台同步。 |
| Market Data（按需与自动） | GAP-P1-07 | 平台托管凭据、provider 健康、source/as-of/stale、失败降级和独立发布验收完成。 |
| AI / Insights | GAP-P1-08、GAP-P1-13 | 最小 auditable run、失败状态、平台托管凭据、限流和成本边界完成。 |
| PDF | GAP-P0-08 | CJK 字体、文本提取、分页渲染和浏览器下载验收完成。 |
| 风险卡 | GAP-P0-09 | current mark、net transfer、base currency、source/freshness 与负向测试完成。 |
| 开放注册 | GAP-P0-05 | email verification、自助 reset、注册滥用防护和审计完成。 |

关闭能力必须满足：已知 capability path 由不导入真实 handler 的 deny-only stub 返回 HTTP 404 + 稳定 error code `FEATURE_DISABLED`；前端没有入口，普通设置页拒绝对应 secret，不产生 job/outbox，部署不要求相关凭据，用户文档不宣传。未知路径仍使用普通 404；只隐藏按钮不算关闭。

部署必须有不可由数据库管理员绕过的 capability ceiling。allowlist 只能来自镜像外的环境变量、部署清单或 secret manager 配置，不能存入 `FeatureFlag`、`PlatformSetting` 或其他业务数据库表：

```text
effective_enabled = deployment_capability_allowlist AND runtime_rollout_flag
```

缺失配置、未知 capability 或 flag 数据库读取失败时一律 fail-closed。Admin 只能在部署 allowlist 内 rollout；扩大 allowlist 属于 release change，必须重新走 staging 和人工批准。

### 3.3 明确排除

- 量化研究、因子、回测、Signal/Order/Fill、自动下单、OMS/EMS、pre-trade risk 和 kill switch。
- 分钟/tick 数据、point-in-time dataset、权威 security master 和公司行为平台。
- Redis/Kafka/Kubernetes、七域 PostgreSQL schema、对象存储平台。
- 全站 `/api/v1` 重写、完整 generated types 和完整 materialized read-model 平台。
- App、SSO、完整 i18n、邮件平台和复杂 Admin route family。
- prompt registry/state-machine/cache/计费等完整 AI 平台。
- `backend/models.py` 纯结构拆分；等 canonical/legacy 语义稳定后再执行。

## 4. 跨任务业务合同

这些合同必须在 `JRN-001` 和 `JRN-005` 固化为 ADR、schema/API 约束和 golden vectors；后续任务不能自行选择另一套口径。

### 4.1 金额、费用与事件顺序

- 持久化和计算只使用 Decimal；中间计算保持高精度，只在最终 posting 时量化到 `NUMERIC(20,8)` 并采用 `ROUND_HALF_EVEN`，导出保留持久化精度。
- Beta 每个 trade event 最多只有一个聚合 `fee_amount + fee_currency`，佣金、平台费等组成由用户先汇总；fee component breakdown 延期。该聚合 fee 在事件发生时产生一条负数 ledger posting；每个 REDUCE/CLOSE 产生 realized gross PnL posting。不得把 net PnL 和 fee 再重复入账。
- OPEN/ADD fee 按 FIFO lot quantity 分配；partial close 的 `realized_pnl_net` 等于 realized gross 减本次 close fee 和已消费 lot 对应的 opening fee。每个 lot 最后一次消费承接此前量化余数，保证 allocated fee 总和严格等于原始 fee；剩余 fee basis 跟随未平 lot。
- 每个 ledger posting 有数据库唯一键，例如 `(source_fact_public_id, posting_kind)`；同一 event 的 `TRADE_FEE` 和 `REALIZED_GROSS` 可各有一条，但重放和并发不能生成第二条同 kind posting。
- `PositionEvent`、`Transaction` 和 `AccountLedgerEntry` 是 append-only 财务事实；更正只能新增关联 reversal/void。重放和 projection 不得 update/delete 既有 ledger row。
- 同一 position 的稳定顺序是 `(event_time_utc, sequence_no)`；`sequence_no` 在持仓行锁内单调分配。普通手工 append 不允许早于最新 active trade event，历史回填只通过受约束 Import 或审计 runbook。
- 同 `(account, instrument, side)` 的普通新 OPEN 不得早于最近 non-void lifecycle 的 terminal time，非 void lifecycle 的历史区间不得重叠。修正较早 lifecycle 时，必须将它和所有后续同方向 lifecycle 从新到旧 void，再按时间从旧到新重录；不提供绕过 chronology 的普通 backdate header。

### 4.2 时间与时区

- 用户必须配置有效 IANA timezone；数据库持久化 UTC aware timestamp。
- 带 offset 的输入按其 offset 转 UTC；不带 offset 的输入按用户时区解释。DST ambiguous/nonexistent local time 返回 422，禁止猜测。
- 每日随笔、Timeline 日期分组和 Dashboard day boundary 使用用户时区；跨用户事实不共享隐式 server timezone。
- 通用导入同时间行按原始 row number 稳定排序。`IBKR_FLEX_XML_V1` 对每个 `(binding, instrument, direction)` 使用完整 `source_order_key = (occurred_at_utc, numeric transactionID, external_execution_id)`；`ibExecID` 只在 provider sequence 相同时作确定性 tie-break，不声称券商时序。缺失/重复 `transactionID` 时，若 tie 顺序会影响 lifecycle、FIFO、fee 或 PnL，则返回 `UNSUPPORTED_ORDER_CONFLICT`；只有经模拟证明交换顺序不改变财务结果时才可用 `external_execution_id` tie-break。append boundary 是该分组最后一个 current-accepted execution 的 order key；incremental replay 从已接受的完整 source history/state 继续，不把每个新文件重新从 0 计算。导出同时包含 UTC ISO-8601 timestamp 和生成时使用的 IANA timezone。

### 4.3 账户、纠错与删除

- 账户只有在从未产生 opening balance、position/event、transaction、ledger 或 import 时才允许硬删除；否则只能 archive/deactivate，且历史和导出仍可见。
- 任一持久化 ImportSession audit shell 一经写入（最早为 `UPLOADING`），账户即永久失去 hard-delete 资格；这不自动 archive/deactivate 账户，也不阻止 `SOURCE_BOUND` 账户对同一 binding 继续导入。活动态和 `FAILED/EXPIRED/COMPLETED_NOOP` 等无财务写入终态都不能通过删除账户抹除。
- 账户交易来源状态固定为 `CLEAN / MANUAL / SOURCE_BOUND`：首次手工 trade 或通用 CSV/Excel 非 noop confirm 使 `CLEAN -> MANUAL`；首次 `IBKR_FLEX_XML_V1` binding-effective confirm 使 `CLEAN -> SOURCE_BOUND(binding)`；opening balance 不改变该状态。binding-effective 表示至少应用一个 effective execution，或确认一份有 flat-boundary evidence 且 coverage 有效的零成交 statement；后者以 `COMPLETED` 建立 binding/acceptance，但不产生 canonical trade fact。
- `source_health` 与 `trade_source_state` 正交，固定为 `NOT_APPLICABLE / HEALTHY / RECONCILIATION_REQUIRED / SOURCE_DIVERGED`。`ImportSourceBinding.source_health` 是唯一持久化真值；account API/UI 对 `SOURCE_BOUND` 投影其唯一 binding 的 health，对 `CLEAN/MANUAL` 投影 `NOT_APPLICABLE`，不得在 account 另存可漂移副本。首次 source binding 原子设为 `HEALTHY`。任一 authority-changing case 进入 `OPEN/RESOLVING` 时立即重算为 `RECONCILIATION_REQUIRED`；存在任一 `DIVERGED_REJECTED` 时优先为 `SOURCE_DIVERGED`。两个非健康状态都不得把账户移出 `SOURCE_BOUND`，都阻止后续 NEW confirm 和可信指标；每次 case 状态变化后在同一 binding lock 内从全部 case 重算，只有不存在 `OPEN/RESOLVING/DIVERGED_REJECTED`，即全部 case 均为 `RESOLVED_APPLIED` 或 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY`，才恢复 `HEALTHY`。
- `trade_history_empty` 表示账户没有 position/event、成功 non-noop trade Import、source application 或 source binding。首次导入使用两个不同谓词：`generic_bootstrap_eligible = active + CLEAN + trade_history_empty + 除最多一条 opening-balance ledger 外无其他 transaction/ledger`；`source_bind_eligible = active + CLEAN + trade_history_empty + source/external-account unique + currency compatible + flat_boundary_proven`。IBKR adapter 的 authority scope 只覆盖 trade execution/commission，因此 source bind 允许已有同账户币种的 opening balance、deposit、withdrawal、interest 和 account fee；这些事实不能伪装成 trade，也不进入 source fingerprint。cash dividend 仍要求关联 owner-validated position，所以在 trade_history_empty 的首次绑定前不可存在。该拆分不表示 source bootstrap 后永久不能导入；`SOURCE_BOUND` 账户只接受同一不可变 binding 的后续文件。Beta 每个内部账户 lifetime 最多一个 binding，archive 不释放槽位；同一 owner 的 `(adapter_kind, normalized_external_account_ref)` lifetime 只能绑定一个内部账户。
- `trade_source_state` migration 必须 fail-closed backfill：只有确定没有 legacy/canonical trade、成功非 noop Import 或 source application 的账户才可为 `CLEAN`；任何已有或无法判定的交易历史一律为 `MANUAL`。archive、void、preview cleanup 和 binding archive 都不恢复 `CLEAN`。
- `SOURCE_BOUND` 账户的 trade financial command 只允许来源 Import 和受审计 correction；普通手工 OPEN/ADD/REDUCE/CLOSE 返回 409 `SOURCE_BOUND_ACCOUNT`。narrative/review/daily note、资金流水和 cash dividend 仍可按各自合同使用。
- account base currency 在第一笔财务事实后不可修改。
- Archive 只改变默认可见性，不改变财务结果；Void 必须产生 compensating facts，才可从 active 统计中排除原事实。
- 普通用户不能通过 header 或隐藏路由修改/删除 legacy position/batch。迁移 fallback 只能进入 admin/CLI namespace，并要求管理员身份、reason、actor 和 immutable audit。
- 所有 account-scoped 财务 mutation、ImportSession/source binding 操作和 account archive/hard-delete/currency 操作使用同一 PostgreSQL 锁协议：先锁 account 并在锁内复验删除/source-state 条件，再锁 source binding，最后按稳定 ID 顺序锁 position，禁止反向获取。OPEN、ADD/REDUCE/CLOSE、资金/dividend、reversal/void、Import upload/confirm 和 account hard-delete 都遵守该顺序。

### 4.4 Instrument identity 与日志内容

- 无 Market Data/security master 时，由用户或 Import 提供 instrument identity；规范键至少为 `(asset_type, market, exchange_code, normalized_symbol, instrument_type, quote_currency)`。JRN-001 冻结为先对未裁剪的原始 token 拒绝任意非 ASCII 字符，再只裁剪 ASCII whitespace 并 uppercase；`exchange_code` 长度 1 至 32，pattern 为 `^[A-Z0-9][A-Z0-9._-]{0,31}$`；`normalized_symbol` 受现有 legacy/PostgreSQL 列宽约束为 1 至 50，pattern 为 `^[A-Z0-9][A-Z0-9._/-]{0,49}$`。JRN-007 实现完整组合唯一约束；任何扩宽必须先做 forward migration 再升级合同。
- JRN-007 在 canonical 事务内 deterministic get-or-create 合法的 `AssetMaster/TradeInstrument`；并发唯一键竞争必须 replay/get existing。同 symbol 不同 market/exchange 不得串用，quote currency 必须等于 account base currency。
- instrument identity 一旦被财务事实引用就不可原地改；不支持的 asset/instrument/market 组合 fail-closed，不调用外部 provider 猜测。
- JRN-001 期间的 legacy bridge 只接受本次请求已显式校验并同事务传入的 identity，或已由 exact `journal_identity_v1` 证明的 identity；历史 `Position.exchange` 曾被写成 broker/`Imported` 等值，单凭格式合法不得升级为 canonical exchange。无上述证据返回 `LEGACY_INSTRUMENT_IDENTITY_UNPROVEN` 且零 canonical side effect；已有 pre-upgrade truth 可继续只读，但不得借读取重写缺失 identity metadata。显式 reconciliation/backfill 与同 symbol 多 market/exchange 的正式 schema 由 JRN-007 完成。
- 现有 `AssetMetadata(symbol)` 是跨 owner 共享 legacy 表，在 owner-scoped label 模型完成前视为 system-owned：普通 create/update 不能写 `name/sector` 或原地修改共享 metadata。用户自定义标签若进入 Beta，必须落到 owner/position-scoped 模型并通过 JRN-004 tenant matrix，不能复用全局 symbol 行。
- trade event 的财务字段和 checklist snapshot 不可变。narrative/review/daily note 是可编辑日志内容，编辑必须追加 revision/audit（actor、time、前后版本关联），不能原地改写财务 event；策略/checklist 新版本只影响未来 snapshot。
- 持仓采用 `HEDGE_BY_DIRECTION`，financially-open uniqueness 为 `(account_id, instrument_id, side)`；financially open 指 remaining quantity 大于 0 且未 void，archive 不释放该槽位。opposite-side OPEN 创建独立 lifecycle，PnL、FIFO lot、fee 和 reversal 各自重放；没有自动平旧开新或 long/short netting。

### 4.5 幂等、source identity 与 Import retention

- canonical financial mutation 和 Import upload/confirm 的 idempotency identity 固定为 `(owner_id, operation_scope, key_hash)`；`operation_scope` 使用稳定、版本化 command name，upload request hash 必须包含 adapter/account/file hash。通用 confirm hash 包含 session 与 selected rows；source confirm 不接受 row selection，hash 包含 session、command 和 versioned `source_preview_digest`。该 digest 覆盖 binding accepted-source-state revision/hash、`accepted_coverage_through_exclusive`、全部 pending statement coverage intervals、各受影响 group append boundary、全部 pending observation `(external_source_event_id,fingerprint_version,fingerprint,order key)`，以及用户预览的 derived direction/action/pre-post quantity/amount/fee；首次 bootstrap 则覆盖 account eligibility revision、flat-boundary evidence、statement coverage 和全部 folded units。原 key 只保存 hash、不保存明文。同一原 key 可由不同 owner 或同一 owner 的不同 operation 独立使用；同 owner/scope/key 下同 request hash 重放原响应，不同 request hash 返回 409。
- request hash、response snapshot/schema version 与 source fact 或 ImportSession audit shell 关联，并至少保留到关联事实的删除期限结束。Beta 财务事实和 Import audit shell 不硬删，因此这些记录无 TTL 自动删除。
- source binding 的身份固定为 `(owner_id, adapter_kind, normalized_external_account_ref)`，execution 身份固定为 `(source_binding_id, external_execution_id)`，source row/change identity 固定为 `(source_binding_id, external_source_event_id)`；adapter version 与 source IANA timezone 随 binding 冻结。每个 observation 还保存 provider-declared `event_kind = TRADE/CORRECTION/CANCEL_BUST` 和可空 `affected_external_execution_id`。普通 execution 的 event ID 与 execution ID 都为 `ibExecID`；独立 correction/cancel-bust 使用自己的 provider-declared stable event ID，并将 provider target 规范到 `affected_external_execution_id`，不能把 change event ID 当作新经济 execution。target 缺失时，已有 binding 只创建 binding/change-observation-scoped `TARGET_UNRESOLVED` case，未绑定 bootstrap 则 conflict；缺失 stable event identity 一律 fail-closed。external account 在日志和普通 UI 中掩码显示，不能跨 owner 或跨内部账户复用。
- 永久模型拆为：`SourceStatement`（generation、原始 from/to、规范化半开本地日期 coverage、file hash）、immutable `ExternalSourceObservation`（任意 trade/cancel/correction row）、`StatementExecutionSighting`（statement 到 observation 的出现关系）、`ExternalExecution`（经济 execution）和 versioned application；binding 保存可重建校验的 `accepted_coverage_through_exclusive`。数据库 unique 至少覆盖 `(binding,file_hash)` statement、`(statement,external_source_event_id,observation_id)` sighting、`(binding,external_source_event_id,fingerprint_version,fingerprint)` observation。case 使用 `trigger_sighting_id + case_kind + against_source_state_hash` 标识 episode，并以 `SourceCaseEvidenceSighting(case,sighting)` 附加同 episode 后续证据；`OPEN/RESOLVING/DIVERGED_REJECTED` 是仍影响 health 的 nonterminal 状态，`RESOLVED_APPLIED/RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 才是已清 terminal 状态。PostgreSQL partial unique 保证同一 `(binding,conflict_observation,case_kind,against_source_state_hash)` 最多一个 nonterminal case，但 terminal case 不阻止新 trigger sighting 创建新 episode，即使 baseline hash 未变。`against_source_state_hash` 必须与 `against_source_state_schema_version` 和可审计 snapshot 一起保存；其输入是按 case kind 选定 authority scope 的版本化 canonical serialization，至少包含 binding、current trade observation/fingerprint version、execution disposition、canceled-by observation、active application/version，并对 late/order/correction replay 加入受影响 `(instrument,direction)` 的 accepted application/order-key 序列与 append boundary。`TARGET_UNRESOLVED` snapshot 保存 `target = null`、change observation 和 owner-scoped candidate execution ID digest，不能伪造 execution scope。trigger/evidence 本身不进入 baseline hash；同 snapshot 必须生成同 hash，任一会改变冲突判断的 current authority/application/group state 必须改变 snapshot/hash。同 statement 内同 event ID + 同 fingerprint 复用 observation/sighting 并记 duplicate warning；同 event ID + 不同 fingerprint 必须各有 sighting。相同 payload 在新 generation 出现时新增 sighting；相同文件重传不新增。
- coverage 接受真值使用 immutable `StatementCoverageAcceptance`，链接 binding、statement、成功 confirm ImportSession/operation idempotency record、accepted source-state revision 和 accepted timestamp；`(binding_id, statement_id)` 唯一并以 composite FK/check 保证 same-binding。已有 binding 的 preview/conflict 可以永久写 `SourceStatement`，但只有 source full confirm 或 source-bound `COMPLETED_NOOP` 成功事务能为其消费的 statement 写 acceptance。`PREVIEW_READY/CONFLICTED/FAILED/EXPIRED` statement 不进入 accepted frontier；空 statement 可凭 acceptance 重建无交易月份。binding 的 `accepted_coverage_through_exclusive` 只是从首次 boundary 和连续 acceptance intervals 重建并校验的 projection。
- `latest_authority_generation(execution)` 是可重建函数/projection：取该 execution 全部 trade observations 的 sightings，以及 provider-declared 或已成功 `RESOLVED_APPLIED` 的 user-target case lineage 指向它的 cancel/correction sightings 的最大 generation。`TARGET_UNRESOLVED`、OPEN/REJECTED 或尚未成功 apply 的用户 target 不进入该函数。它不能只按相同 external execution ID 计算；`canceled_by_observation_id` 对 target 为可空唯一且 same-binding。任何 ALREADY_IMPORTED sighting 都必须参与该函数。
- `ExternalExecution` 保存 `current_trade_observation_id`、`ACTIVE / ACCEPTED_TOMBSTONE` disposition、可空 `canceled_by_observation_id`；active execution 任一时点最多一个 application，tombstone 没有 active application。独立 correction/cancel-bust observation 自身按 `(external_source_event_id,fingerprint_version,fingerprint)` 被接受一次；correction application 以 `affected_external_execution_id` 更新 target 的 current observation/version，cancel-bust 以 same-binding `canceled_by_observation_id` 关联 target，不能假设 change event 与 target 同 ID。source payload fingerprint 只覆盖稳定、规范化的 provider-declared 字段；statement provenance、用户在 resolution 选择的 target，以及依赖 running state 的 derived direction/action/pre-post quantity 都不进入该 fingerprint。derived action、用户 target 与财务结果只存 case/application version。
- source 分类按固定优先级执行：先 `ACCOUNT_MISMATCH/UNSUPPORTED`；再以已接受 observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 识别 `ALREADY_IMPORTED`，包括 current active trade 和已接受 correction/cancel-bust；仅 event identity 相同而 fingerprint 不同绝不能 no-op，同时为不同 statement provenance 幂等写 sighting。再查找 nonterminal/rejected case 并附加 evidence，但不得 short-circuit 后续 authority comparison。target 缺失的 change 无法比较 authority：若其 event identity 已有 accepted fingerprint 而本次不同，则固定为 `SOURCE_PAYLOAD_CONFLICT`；否则归为 binding-scoped `TARGET_UNRESOLVED`，只创建/复用 case 和 evidence，不执行 target `latest_authority_generation`、strict-later comparison 或自动 supersede。target 已知的 change 先以 target authority scope 判 historical/stale：匹配已由 terminal case supersede 的 change fingerprint，且 generation 严格早于 target `latest_authority_generation`，归为 `KNOWN_HISTORICAL_OBSERVATION`；此前未见的 target-known change payload 若 generation 也严格更早，归为 `STALE_SOURCE_OBSERVATION`。即使 accepted change event identity 出现新 fingerprint，strict-earlier 也先走 stale 分支；两者只保留 evidence/warning、不建 case。通过该分支后，同代或更晚 authority 上 accepted correction/cancel-bust event identity 的新 fingerprint 才固定为 `SOURCE_PAYLOAD_CONFLICT`；其余 cancel-bust 归为 `CANCEL_BUST`、correction 归为 `CORRECTION`，即使 event ID 独立也必须使用 `affected_external_execution_id` authority scope，绝不能成为 `NEW`。普通 `TRADE` observation 最后按历史 fingerprint/generation 与 group append boundary 判定。匹配已知 superseded/reversed trade fingerprint 且 generation 严格早于自身 `latest_authority_generation` 为 `KNOWN_HISTORICAL_OBSERVATION`；此前未见的 same-execution payload 若 generation 也严格更早，则为 `STALE_SOURCE_OBSERVATION`，只保留 evidence/warning、不建 case。generation 相等或更晚时重申任一历史 trade/change payload 都不得 stale no-op，必须进入 conflict/new episode。
- `NEW` 不以“数据库从未见过 ID”为条件，而表示 ordinary `TRADE` execution 尚无 accepted application/tombstone、没有影响该 observation 的 nonterminal case，且相对 current-accepted history chronology 可追加。已有 statement/observation/sighting 但因 session 过期或尚未 confirm 而从未应用的 execution，重传时仍分类为 `NEW`；provenance 存在不能把它误判为 duplicate。
- `source_completeness` 是 binding 上从 `StatementCoverageAcceptance`、statement coverage、observations/applications 可重建的 `CURRENT/PENDING_IMPORT` 投影，不是第二份手工状态。存在尚无 acceptance 的 coverage extension，或任一可确认但尚无 accepted application/tombstone 的 `NEW` 时为 `PENDING_IMPORT`；preview 一旦持久化任一此类内容就立即更新投影。accepted frontier 只取从首次 boundary 开始连续的 acceptance intervals，且必须与 binding scalar watermark 一致。`CURRENT` 只表示截至 `accepted_coverage_through_exclusive` 没有已上传待确认内容，不表示文件 adapter 已实时同步到券商当前时刻。`source_health = HEALTHY` 只表示没有 reconciliation divergence，不代表来源已追平；可信 derived 指标和 release gate 同时要求 `source_health = HEALTHY` 且 `source_completeness = CURRENT`。UI 始终显示 last-confirmed coverage/as-of；PENDING 时另显示待确认区间和数量，不把结果展示为当前完整。
- 当同 authority scope 出现严格更晚且 provider order 可证明的 trigger sighting 时，在同一 binding lock/事务中将被其取代的 `OPEN` 或 `DIVERGED_REJECTED` cases 转为 terminal `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY`，永久链接 winning sighting/observation/新 case；`RESOLVING` 需等待锁后重分类。即使 sighting 的 observation 已附加到旧 rejected/nonterminal case，也必须继续执行这一步。若 winning payload 自身仍与 canonical current 冲突，则在同一事务创建/复用针对当前 baseline 的新 `OPEN` episode，再重算 health，不能在关闭旧 case 的中间状态错误恢复 `HEALTHY`。只有 `source_health = HEALTHY` 且 binding-wide pending `NEW` 全集从 accepted boundary 连续可重放时才可普通 full confirm；completeness PENDING_IMPORT 允许执行该 full confirm，但其间可信 derived 保持降级。
- 增量导入允许文件时间窗口重复、重叠、首尾相接或纯增量。adapter 必须按 provider evidence 将 `fromDate/toDate` 规范为 source timezone 下的半开本地日期 coverage；不能从 execution row 反推。首次 binding 建立连续 coverage，后续只有 pending statement coverage 的并集与 `accepted_coverage_through_exclusive` 重叠或首尾相接才可 confirm；断档返回 statement-level `SOURCE_COVERAGE_GAP` 并保持 `PENDING_IMPORT`，补齐区间后才能 full confirm。无 execution 的 statement 仍可推进 coverage；`transactionID` 只排序，数值不连续不代表 coverage gap。coverage watermark 与 execution unique identity 分别证明“时间范围未漏”和“事实未重复”，不能互相代替。缺失稳定 execution ID 时必须 fail-closed，禁止使用 symbol/time/row-index 或 price/quantity fingerprint 自动去重。
- Beta 文件 adapter 仅允许 `IBKR_FLEX_XML_V1` 的冻结字段合同，不保存或请求 Flex Token，不发起网络请求。XML 禁止 DTD/entity/XInclude；限制 10 MB、5,000 executions、节点/属性/深度/字段长度、每 owner 最多 2 个 nonterminal ImportSession 和 10 分钟 10 次 upload。文件必须恰好包含一个 external account，statement 必须有经 provider contract/fixture 证明严格代际顺序与 tie 语义的 generation marker（V1 预期为 `whenGenerated`），execution 必须有稳定 `ibExecID`；无法证明 marker 单调性时 adapter 保持关闭。
- 原始上传不进入数据库、对象存储或应用持久目录。解析优先使用有界流/内存；框架必须 spool 时使用部署专用 `0700` 临时目录与 `0600` 文件，在成功、解析失败、超限、取消和异常的 `finally` 中 close+unlink，并由启动/maintenance scavenger 幂等删除超时 orphan；只有 normalized rows 持久化。进程崩溃和恶意 XML 测试必须证明无长期原文件残留。
- Import preview 的业务 TTL 为 24 小时。upload 与 confirm 使用不同 operation scope 的强制 Idempotency-Key；请求顺序固定为 auth/owner -> operation idempotency lookup -> 同 key/hash 返回持久响应 -> 其余请求检查 session state/expiry。upload 创建的 `PREVIEW_READY/CONFLICTED` session 响应和 confirm 创建的 `COMPLETED/COMPLETED_NOOP/CONFLICTED` 响应都可跨 TTL 永久重放；未消费 session 的普通读取和首次 confirm 在 `now >= expires_at` 返回 410。不同 key/hash 返回 409，不能借重放重新消费 session 或创建第二个 upload session。
- 原始上传文件不长期保存；normalized preview rows 在 session 进入 `COMPLETED/COMPLETED_NOOP/CONFLICTED/FAILED/EXPIRED` 后保留 30 天再批量删除。ImportSession audit shell、source binding、SourceStatement/sighting、source event/execution identity/fingerprint、current trade observation/canceled-by tombstone 和 canonical application linkage 随账户永久保留，不能被 preview cleanup 删除。
- 清理由幂等、限批的 PostgreSQL maintenance command 执行，并接部署 cron/运维 runbook；它不能依赖可选 worker，也不能影响 TTL 判定或 canonical 数据。

## 5. 任务总表

规模包含实现、测试、迁移/回滚和文档，不是日期承诺：`S=1-2`、`M=3-5`、`L=6-10` 人日；超过 10 人日必须继续拆分。

| 顺序 | ID | 任务 | Gap 映射 | 依赖 | Beta 阻断 | 规模 |
|---|---|---|---|---|---|---|
| S0-00 | `JRN-000` | 冻结当前 WIP、迁移链与 checkpoint | GAP-P0-07、全局范围治理 | 无 | 是 | M |
| M0-01 | `JRN-001` | 冻结 release contract 与部署 capability ceiling | 全局范围治理 | JRN-000 | 是 | M |
| M0-02 | `JRN-002` | 可复现基线与 PostgreSQL CI | GAP-P0-07 | JRN-001 | 是 | M |
| M0-03 | `JRN-003` | Invite-only auth 与 release secret 治理 | GAP-P0-05 | JRN-001 | 是 | L |
| M0-04 | `JRN-004` | Tenant/owner 边界审计与封闭 | GAP-P0-01 | JRN-002、JRN-003 | 是 | M |
| M1-01 | `JRN-005` | 会计 posting matrix 与 golden vectors | GAP-P0-02 | JRN-001、JRN-002 | 是 | M |
| M1-02 | `JRN-006` | Append-only ledger 与 journal balance 收敛 | GAP-P0-02、GAP-P0-10 | JRN-004、JRN-005 | 是 | L |
| M1-03 | `JRN-007` | Truth-native OPEN 单事务写入 | GAP-P1-01 | JRN-004、JRN-006 | 是 | M |
| M1-04 | `JRN-008` | Lifecycle 并发、幂等与 legacy projection | GAP-P1-01 | JRN-007 | 是 | L |
| M1-05 | `JRN-009` | 不可变资金流水、cash dividend 与账户 lifecycle | GAP-P0-10 | JRN-006、JRN-008 | 是 | L |
| M1-06 | `JRN-010` | 交易 reversal/void 与 legacy mutation 隔离 | GAP-P1-02 | JRN-008、JRN-009 | 是 | L |
| M1-07 | `JRN-011` | 持久化通用 Import upload/preview session | GAP-P0-01 | JRN-004、JRN-005 | 是 | L |
| M1-08 | `JRN-012` | 通用 bootstrap Import confirm 与 canonical replay | GAP-P0-01 | JRN-008 至 011 | 是 | L |
| M1-09 | `JRN-013` | Source binding 与 IBKR Flex 安全 preview | GAP-P0-01、GAP-P1-03（文件子集） | JRN-003 至 005、JRN-007、JRN-008、JRN-011 | 是 | L |
| M1-10 | `JRN-014` | Source-bound incremental canonical confirm | GAP-P0-01、GAP-P1-03（文件子集） | JRN-008 至 013 | 是 | L |
| M1-11 | `JRN-015` | Source correction 与 versioned replay | GAP-P0-01、GAP-P1-02/03（文件子集） | JRN-010、JRN-013、JRN-014 | 是 | L |
| M2-01 | `JRN-016` | Derived freshness 与故障恢复结果门 | GAP-P0-04、GAP-P1-06 | JRN-008、JRN-009、JRN-015 | 是 | L |
| M2-02 | `JRN-017` | 核心日志与复盘可信读体验 | GAP-P1-05、GAP-P1-09 至 11 | JRN-010、JRN-015、JRN-016 | 是 | L |
| M2-03 | `JRN-018` | Canonical 用户数据可携带导出 | 新增日志基础能力 | JRN-009、JRN-010、JRN-015、JRN-017 | 是 | M |
| M3-01 | `JRN-019` | 生产启动与 migration gate | GAP-P0-03 | JRN-002、JRN-003、JRN-018 | 是 | M |
| M3-02 | `JRN-020` | 单一 PostgreSQL 备份恢复路径 | GAP-P0-06 | JRN-006、JRN-019 | 是 | M |
| M3-03 | `JRN-021` | Staging 全链路与 invite-only Beta 发布门 | GAP-P0-07、GAP-P1-14（窄化） | JRN-000 至 020 | 是 | M |

## 6. 里程碑任务

### Step 0：WIP_BASELINE

#### JRN-000 冻结当前 WIP、迁移链与 checkpoint

完成定义：

- 为当前 dirty worktree 产出逐路径 disposition manifest，至少区分 journal/core、Broker/Market optional、frontend/docs、generated/runtime artifact 和无关用户改动；禁止把未分类文件扫入同一提交。
- 当前 migration decision 固定为 `IN_CHAIN_DISABLED`：保留 `6f7a8b9cad10 -> 7a8b9cad1011 -> 8b9cad101112 -> 9cad10111213` 在线性 Alembic 链中，checkpoint baseline head 为 `9cad10111213`；后续 revision 只能向该 head 追加，不能让这四个未跟踪文件留在仓库外。
- JRN-000 自己交付非数据库、不可运行时修改的静态 `JOURNAL_BASELINE` hard-off profile：Broker/Market 真实 router/handler 不 import、不注册，已知 path 只注册 side-effect-free deny stub 并返回 HTTP 404 + `FEATURE_DISABLED`；UI/secret write/job producer 不构建或不可达。JRN-001 后续把该静态 profile 升级为正式 deployment ceiling + runtime rollout 双层模型，但不改变关闭响应合同；JRN-000 不能借用后置任务才通过退出门。
- Broker/Market runtime WIP 无法通过该 hard-off profile 的代码必须留在独立分支或从 launch checkpoint 排除，禁止“迁移入链但功能半开启”。
- `6f7a8b9cad10` 增加的 `ibkr_flex_token` plaintext setting 只视为历史迁移过渡面；JRN-003 必须用 forward migration 清空并默认删除 secret 列或以等价 DB 约束永久禁写，最终 head 不得保留可用明文 secret path。
- hard-off smoke 必须覆盖异常和短 secret：Broker HTTP exception/query URL、query/reference metadata 和少于 8 字符的 secret 都不能经 API、日志或审计回显；JRN-000 前不得把当前半开启 route/settings/job checkpoint 为 launch baseline。
- 将 in-scope WIP 拆成可评审 checkpoint commits，记录 commit、文件清单、Alembic head、验证命令和未纳入项；不自动 merge、push 或 tag。

必测：单一 Alembic head、空库 `upgrade head`、`9cad10111213` downgrade/upgrade round-trip、已知 Broker/Market path 精确返回 404 `FEATURE_DISABLED`、未知 path 普通 404、真实 handler 无 import/side effect、secret/job/UI hard-off smoke、secret scan、backend/frontend baseline 和 `git diff --check`。

退出门：当前 WIP 有唯一书面处置，四个 migration 已被 checkpoint 跟踪且链决策不再悬空，optional runtime 没有半开启入口，后续任务都基于已记录 commit 而不是漂移的 dirty tree。

### M0：SAFE_BASELINE

#### JRN-001 冻结 release contract 与部署 capability ceiling

完成定义：

- 产出机器可读 release profile 和 ADR，冻结唯一 Beta 币种、instrument/event allowlist、`HEDGE_BY_DIRECTION`、单 event 聚合 fee、timezone、idempotency namespace/retention、Import 限额、`GENERIC_BOOTSTRAP` 与 `IBKR_FLEX_XML_V1` adapter allowlist、source-state 合同和禁用能力。
- `GENERIC_BOOTSTRAP` 与 `IBKR_FLEX_XML_V1` 在各自 implementation gate 关闭前都不等于已实现：旧 `/api/positions/import/upload|confirm|template` 必须由不 import legacy handler 的 deny-only stub 返回 404 `FEATURE_DISABLED`，从 OpenAPI 移除，前端入口不存在且 `/positions/import` 直达访问进入框架 not-found 视图；只有 JRN-011/012 或 JRN-013 至 015 的 owner-bound 持久会话实现通过后才能按对应 adapter 重新开放。
- 实现 deployment allowlist 与 runtime flag 的双层守卫；allowlist 只读环境/部署配置且不落业务数据库，Admin 不能强开 ceiling 外能力。
- 在线 Broker、Market、AI、PDF、风险和开放注册的 API、UI、secret、job/outbox、文档同时 fail-closed；`IBKR_FLEX_XML_V1` 只允许本地文件解析，不得借 adapter 触发网络或读取凭据。
- 未启用事件（stock split、option、transfer 等）即使直连 API 也稳定拒绝。
- 当前 legacy create/bridge 必须执行 raw-ASCII full instrument identity 校验；已有仓位提示按完整 identity（含 exchange、direction、market、instrument、currency）匹配，slash symbol 通过 query 传输。未证明的历史 exchange 和普通用户共享 AssetMetadata 写入 fail-closed，不能产生半写 truth。

必测：缺失/未知配置、DB flag 读取失败与 caller pending state 隔离、DB 内伪造 allowlist、Admin 强开、直连 API、legacy Import 跨 owner payload 的 deny-only 响应、导航、真实组件/1440x900 与 390x844 浏览器流程、设置写入和零 job/outbox side effect。

#### JRN-002 可复现基线与 PostgreSQL CI

完成定义：

- 固定 Python、Node 和依赖版本；干净环境不复用本机 venv/node cache 也可重建。
- mandatory CI 覆盖 backend、Alembic、frontend test/type/lint/build、OpenAPI snapshot 和 secret/legacy boundary checks。
- PostgreSQL service container 执行空库 `upgrade head`、存量 fixture upgrade 和 release-scope integration。
- 本地一条命令运行同一 gate，并保存 commit、工具版本和结果。

必测：现有 backend/frontend baseline；PostgreSQL migration、timezone、auth/account 和最小 canonical 写入 integration。

#### JRN-003 Invite-only auth 与 release secret 治理

完成定义：

- 管理员创建一次性、限时、随机且哈希存储的邀请码；兑换、过期、吊销、重放和 actor 均受审计。
- Invite onboarding 必须写入有效 IANA timezone；存量用户缺失时在继续写交易/日记前要求显式选择，禁止静默使用 server timezone。
- 生产弱 `SECRET_KEY` 或缺失必要配置时启动失败；login 和 invite redemption 有最小 IP/account 限流。
- Broker、Market/Finnhub、LLM 等用户 secret 写入口全部拒绝；迁移并清除 `UserSettings/SystemSetting/PlatformSetting` 明文 secret fallback，并按 JRN-000 决策用 forward migration 默认删除 plaintext secret 列。source-bound 文件模式不保存 Flex query/token。
- Beta 如需平台 secret，只能来自受管环境或 encrypted `IntegrationCredential`；日志和 API 永不返回明文。
- 管理员辅助 password recovery 不在日志中记录临时密码；所有外部 HTTP exception、URL query、短 secret 和 provider metadata 经过统一 redaction 后才能进入 API/log/audit。

必测：邀请成功/过期/吊销/重放、有效/无效 timezone、存量用户 timezone gate、暴力登录、弱密钥启动、普通/管理员 secret endpoint 和存量 secret migration。

#### JRN-004 Tenant/owner 边界审计与封闭

完成定义：

- 对当前存在的 account、strategy/checklist、position/event、transaction/ledger、daily note 和 idempotency record 做 ownership matrix；legacy Import 在 JRN-011 替换前先关闭或补 owner-bound deny guard，不能保留全局 token 越权路径。
- 冻结未来 owner-scoped resource contract 和可复用两用户交换 test harness；ImportSession/Row 由 JRN-011，source binding/execution/observation/application 与 `SourceReconciliationCase` schema/OPEN 创建由 JRN-013/014，case resolution 由 JRN-015 各自在创建/使用任务中实例化并通过矩阵，JRN-021 汇总验证。JRN-004 不把尚不存在的模型宣称已验证。
- 所有嵌套外键同时验证 owner 和资源类型；不存在只校验 ID 存在的写入。
- 跨租户读取/写入/导入/导出稳定返回 404/403 且无 side effect；管理员越权必须走单独受审计接口。
- public ID、内部 ID 和 legacy bridge 使用同一 owner resolver 规则。

必测：当前资源两用户交换矩阵、猜测 public/internal ID、混合 account/strategy/position、legacy import token 盗用被拒绝或端点关闭、future-resource owner test harness 和管理员边界。

退出门：WIP/checkpoint 与 migration head 固定；范围唯一；禁用能力不可达；CI/PostgreSQL 可复现；invite/secret/tenant 无已知越权入口。

### M1：DATA_SAFE

#### JRN-005 会计 posting matrix 与 golden vectors

完成定义：

- 用逐事件表冻结 4.1 的 journal balance、FIFO lot、entry/exit fee、long/short、`HEDGE_BY_DIRECTION`、dividend、interest、reversal，以及 IBKR commission sign/currency 到单 event 聚合 fee 的口径。
- 每个 vector 明确 event、lot、position aggregate、ledger postings 和 journal balance 的预期 Decimal 值。
- 冻结 sign、precision、只在 posting 量化、最后一次 lot 消费承接 fee 余数、posting unique key、event ordering、同时间 sequence 和不支持输入错误码。
- 选取脱敏存量样本运行 scanner，列出 currency、fee、ledger divergence；不静默修正。

必测：每 event 0/1 个聚合 fee、拒绝多 fee component、OPEN fee、多次 ADD、多次 partial REDUCE、不可整除 fee 且分配总和守恒、full CLOSE、long/short 同时存在且互不 net、IBKR 正/负 commission 与异币 fee 拒绝、dividend、资金流水、reversal、posting 唯一性、舍入和同时间排序。

#### JRN-006 Append-only ledger 与 journal balance 收敛

完成定义：

- 实现 JRN-005 posting matrix；trade fee、realized gross、dividend 和资金流水各自唯一入账，不重复 netting。
- ledger row 写入后不可 update/delete；projection replay 只重算派生值，差异通过 compensating entry 修复。
- 以 ledger replay 生成 journal balance；退役 `cash_balance/current_balance` 作为权威来源和真实 cash/NAV 文案。
- 存量 migration/backfill 可预览、可中止、可重跑，divergence 进入隔离报告，不猜测修复。未解决账户使用与 `source_health` 正交的 `accounting_health = ACCOUNTING_RECONCILIATION_REQUIRED`，禁止新增财务 mutation 和可信指标展示，只允许带警告的只读/导出与受审计修复；修复并通过 ledger invariant 后恢复 `ACCOUNTING_HEALTHY`。

必测：全部 golden vectors、append-only DB guard、故障回滚、重复 replay、backfill 重跑、divergent account 写入拒绝/指标降级/修复解锁和 reconciliation invariant。

#### JRN-007 Truth-native OPEN 单事务写入

完成定义：

- 按 4.4 的规范键在本地 deterministic resolve/create `AssetMaster/TradeInstrument`；不调用行情 provider，同 symbol 不同 market/exchange 保持隔离。
- 先按 4.3 锁 account，再做合法 instrument get-or-create 与新建 `TradingPosition + OPEN PositionEvent`，全部位于同一事务；legacy row 只能作为兼容 projection。
- 以数据库约束或等价 serializable guard 保证同一 `(account, instrument, side)` 最多一个 financially-open lifecycle；archived-but-not-voided position 仍占用该槽位。same-side OPEN 返回 409 并指向 ADD，opposite-side OPEN 创建独立 position，不修改另一方向。
- 普通 OPEN 的 occurred_at 必须不早于最近 non-void 同方向 lifecycle terminal time；即使旧 lifecycle 已 full close，也不能通过新 position 回填更早时间。
- OPEN event、fee/ledger、idempotency record 和必要 outbox/projection 一次 commit；移除 legacy-first 双提交。
- account `trade_source_state` 对新空账户默认为 `CLEAN`；迁移按 4.3 扫描 legacy/canonical/import 历史，任何已有或不确定 trade history 都 backfill 为 `MANUAL`。普通手工 OPEN 在同一事务执行 `CLEAN -> MANUAL`；opening balance/资金流水不改变该状态；JRN-014 启用 `SOURCE_BOUND` 后普通 trade command 必须在同一 account lock 内拒绝。
- mutating API 强制 `Idempotency-Key`；同 key/同 hash 返回原响应，同 key/不同 hash 返回 409。
- instrument/posting/idempotency 的 PostgreSQL unique race 转为确定 get-existing、replay 或 409，不返回 500。

必测：long/short OPEN、新空账户默认 CLEAN、legacy/canonical/历史成功 Import 与不确定存量均 backfill MANUAL、仅 opening balance 存量保持 CLEAN、首次 OPEN 原子 `CLEAN -> MANUAL`、opening balance 不改变 CLEAN、archive/void 不恢复 CLEAN、same-side OPEN 409、archive 后 same-side 仍 409、close@t3 后新 OPEN@t1 拒绝、void latest 后按原历史时间重新 OPEN、opposite-side OPEN 成功且独立、并发 opposite/same-side OPEN、带 offset/无 offset/DST ambiguous/nonexistent 时间、fee、同 symbol 不同 market、quote currency 422、不支持 instrument、并发 instrument create、两用户同 raw key、同用户跨 operation 同 key、同 scope 不同 payload、跨租户和各阶段故障注入全回滚。

#### JRN-008 Lifecycle 并发、幂等与 legacy projection

完成定义：

- ADD/REDUCE/CLOSE 先锁 account、再锁 position，在同一事务内验证剩余数量、分配 sequence 并提交。
- 不同 idempotency key 的并发 REDUCE/CLOSE 不能超量、重复平仓或覆盖新状态。
- 普通 append 不接受 backdated trade event；同 timestamp 以 sequence 稳定重放。
- legacy projection 与 canonical 同事务且可 reconciliation。legacy read bridge 至少保留到 JRN-014 与 JRN-016 完成，并且 canonical backfill/reconciliation 100% 通过、正常产品调用 telemetry 连续一个发布周期为零、restore/rollback drill 不再依赖 legacy 写入后，才允许通过独立迁移任务删除；JRN-008 不提前删除 legacy 表、route 或 rollback 数据。
- release-scope 财务 operation 的 idempotency record 以 `expires_at = NULL` 保留并关联 source fact；通用 cleanup 不得删除或把同 key 变成可复用状态。
- 本任务只交付供 correction 使用的锁、幂等和 sequence 基础；latest reversal/whole-position void 的产品语义与端点在 JRN-010 启用。

必测：ADD/partial/full close、带 offset/无 offset/DST ambiguous/nonexistent 时间、并发不同/相同 key、并发 REDUCE-vs-CLOSE、backdated 422、unique race、财务幂等 `expires_at` 为空且跨时钟推进/maintenance cleanup 仍重放原响应、projection failure 和 legacy 对账。

#### JRN-009 不可变资金流水、cash dividend 与账户 lifecycle

完成定义：

- opening balance、deposit、withdrawal、account fee、interest 先锁 account，使用正 magnitude + 类型决定 ledger sign；每次 create/reverse 都强制 `Idempotency-Key`，transaction、unique posting 和完成响应同事务。
- manual cash dividend 先锁 account、再锁 owner-validated position，使用正 magnitude + `RECEIVED/PAID_IN_LIEU` 决定 sign，强制账户币种、幂等、unique posting 和关联 reversal。
- 已入账 transaction/dividend event 不可改财务字段或删除；reversal 保留 actor、reason、request ID，重复/并发请求返回同一结果。
- 有任何财务事实或任一持久化 ImportSession 的 account 只能 archive；base currency 冻结。只有从未入账且从未创建 ImportSession 的空账户可硬删除。
- transfer API/UI 关闭；archive 后历史、reconciliation 和 export 仍完整。

必测：各资金类型与 dividend received/paid 的创建/冲正、创建响应丢失、重复/冲突 key、并发创建/冲正、非法 sign/币种/owner、纯空账户删除、任意 ImportSession 活动态/终态后只能 archive、session-create-vs-account-delete 并发不能级联抹除或返回 500、archive visibility 和余额重放。

#### JRN-010 交易 reversal/void 与 legacy mutation 隔离

完成定义：

- 使用 JRN-008 的 row lock、sequence 和 idempotency 基础启用 latest active event reversal；whole-position void 在一笔事务中按逆序创建 compensating facts，不删除 OPEN/event/ledger。
- reversal 先按统一顺序锁 account 和相关 positions；若撤销旧 REDUCE/CLOSE 会重新打开 lifecycle，而同 `(account, instrument, side)` 存在任何更晚的 non-void lifecycle，无论它当前开放或已关闭，都返回 409 `POSITION_LIFECYCLE_ORDER_CONFLICT`，并要求从最新到最旧 void 所有更晚 lifecycle。不存在更晚 lifecycle 但仍发现另一 financially-open lifecycle 时返回 409 `POSITION_SIDE_CONFLICT`；不允许自动 net 或合并。
- 已入账数量、价格、费用、方向和时间不可原地修改；non-latest correction 由受审计 runbook 处理。
- Archive 不改变统计，Void 才通过补偿改变统计；两者都有 actor、reason、request ID 和 UI 状态。
- Archive 不释放 `HEDGE_BY_DIRECTION` 的 financially-open uniqueness；只有 full close 或完成 compensating void 后才能同方向新 OPEN。
- void 较早 lifecycle 不允许跨过仍 non-void 的后续同方向 lifecycle 回填；必须从最新受影响 lifecycle 向前 void，再按时间顺序重录。原 void/replacement 关联保留在 audit/export。
- 移除普通路由的 `X-Migration-Fallback` 能力；迁移 mutation 仅限 admin/CLI namespace，强制 audit + reason。

必测：各 event reversal、whole-position void、A OPEN/CLOSE -> B OPEN -> reverse A CLOSE 409、A OPEN/CLOSE -> B OPEN/CLOSE -> reverse A CLOSE 仍为 409、仅 close 后续 lifecycle 不解锁而从新到旧 void 后 reverse 成功、reverse-vs-new-OPEN 并发最多一个成功、void 较早但保留后续 lifecycle 时 backdated OPEN 拒绝、受影响 lifecycle 全部 void 后按历史顺序重录成功、重复/并发、archive-vs-void、携带旧 header 仍拒绝、legacy edit/delete 负向矩阵。

#### JRN-011 持久化通用 Import upload/preview session

完成定义：

- 通用 CSV/Excel 限制 10 MB、5,000 行和 24 小时 TTL；超限在完整解析前拒绝。Import upload 强制 operation-scoped `Idempotency-Key`，request hash 包含 account/adapter/file hash；同 key/hash 重放原 session，different hash 返回 409。ImportSession/Row 持久保存 owner、account、adapter kind、file hash、原 row number、normalized values、validation/warning、expiry 和状态。
- 状态机合法边固定为：`UPLOADING -> PREVIEW_READY|CONFLICTED|FAILED|EXPIRED`；`PREVIEW_READY -> CONFIRMING|EXPIRED`；`CONFIRMING -> COMPLETED|COMPLETED_NOOP|CONFLICTED|FAILED`。`COMPLETED/COMPLETED_NOOP/CONFLICTED/FAILED/EXPIRED` 均为终态；通用 Import 不产生 CONFLICTED，但 source upload/preview 或 confirm 可以直接进入该终态。状态转换使用数据库 CAS，进程重启不丢 preview。
- canonical 模板要求完整 instrument identity、direction、明确 `OPEN/ADD/REDUCE/CLOSE`、timestamp、price、quantity、currency；别名映射和 normalization 在 preview 中显式展示。
- 合法但尚未建档的 identity 标记为“confirm 时本地创建”；只有 release allowlist 外 asset/instrument/market 或 currency mismatch 才是 unsupported error。
- 通用文件不能自我声明可信 source identity。完全相同的多行只标记 duplicate warning，不静默去重；同时间行按原 row number 稳定排序。
- 无 offset 时间遵守用户 IANA timezone；DST ambiguous/nonexistent 返回 422。upload/preview 不写 position/event/ledger，前端清楚显示 error、warning、normalized value 和 session expiry。
- upload 创建 ImportSession 前先锁 owner-validated account；account hard-delete 使用同一锁并在锁内复验不存在 ImportSession，禁止数据库级 cascade 删除会话或审计壳。
- 原始 CSV/Excel 与 XML 遵守 4.5 的临时文件合同：不进入持久目录，所有成功/失败/取消路径 close+unlink，启动/maintenance scavenger 清除崩溃 orphan。
- `expires_at` 对未消费 session 的读取和首次 confirm 强制检查；auth/owner 后，`COMPLETED/COMPLETED_NOOP/CONFLICTED` 的同 key/hash 重放按 4.5 绕过业务 TTL 返回持久响应，其他 terminal/expired 读取不恢复 preview。terminal/expired normalized rows 按 4.5 的 30 天策略由独立 maintenance command 限批清理，audit shell 保留且清理不依赖 worker。

必测：跨用户 token、进程重启、upload 同 key/hash 重放同 session/different hash 409/跨 owner 或 operation scope 可独立使用、非法/合法未建档 instrument、别名映射、重复行 warning、同时间 row order、DST ambiguous/nonexistent、伪造 source ID 仍按通用行处理、未消费 session 在 `now == expires_at` 返回 410、cleanup 未运行仍 410、upload PREVIEW_READY/CONFLICTED 与 confirm COMPLETED/CONFLICTED 同 key/hash 跨 TTL 重放原响应而不同 key/hash 409、terminal 后第 30 天 normalized rows 删除而 audit shell 保留、maintenance 限批/失败重跑/重复执行、原文件在成功/解析失败/超限/取消/异常后立即消失且崩溃 orphan 可 scavenging、全部活动态/终态的账户删除边界、session-create-vs-account-delete 并发、CSV/Excel、0/5,000/5,001 行和 10 MB 边界。

#### JRN-012 通用 bootstrap Import confirm 与 canonical replay

完成定义：

- 通用 confirm 只接受 `generic_bootstrap_eligible` 账户。confirm 使用 4.3 的统一 account lock 复验完整谓词，禁止与手工写入竞态合并。
- 任一非 noop 成功通用 confirm 原子执行 `CLEAN -> MANUAL`；后续通用 bootstrap 永久拒绝。whole-position void、account archive 或 preview cleanup 都不恢复 `CLEAN`。
- confirm 强制 `Idempotency-Key`，以 CAS 从 `PREVIEW_READY` 进入 `CONFIRMING`；首个请求拥有 session。auth/owner 校验后先查 terminal idempotency record：同 key/hash 永久返回持久化响应，任何其他 key/hash 返回 409，不能二次消费。
- confirm idempotency record 以 `expires_at = NULL` 与 ImportSession audit shell 一并保留；normalized-row cleanup 不删除该记录，也不允许旧 key 重新消费 session。
- 只对用户最终选中行重新执行 owner、instrument、currency 和 lifecycle-prefix validation；空选择进入 `COMPLETED_NOOP`、写入 0、消费 session，但账户仍为 `CLEAN`。
- 先按 `(instrument identity, direction)` 分组，再在组内按 `(occurred_at UTC, row number)` 稳定重放；每组必须以 OPEN 开始、quantity 永不为负。full close 后新的 OPEN 合法；同方向仍开放时再次 OPEN、字面 REOPEN、孤立 exit 和超量明确报错；opposite side 不自动 net。
- 合法未建档 identity 调用 JRN-007 deterministic get-or-create；duplicate-warning 行不自动去重，选中集合必须满足完整 lifecycle 规则。同一 session/row 永远只能写一次。
- commission 进入 JRN-006 posting；整批调用 JRN-007/008 canonical writer 并在一次数据库事务提交。任一行失败时 position/event/ledger/account state/session completion 全部回滚。
- 完成响应持久保存 selected row count、position/event/posting count 和 source IDs；进程在 commit 后丢失 HTTP 响应也可确定重放。

必测：纯空/仅 opening balance/非 CLEAN 账户、成功后第二次通用 bootstrap 永久拒绝、void/archive/cleanup 不恢复 CLEAN、跨用户、部分选择破坏 lifecycle、开放持仓结尾、`COMPLETED_NOOP` 后仍可新建 bootstrap session、重复/不同 confirm key、响应丢失、并发 confirm、confirm-vs-OPEN/deposit/opening-balance/account-archive、多轮 OPEN-after-close、非法 REOPEN、opposite-side 独立持仓、重复行的合法与拒绝结果、费用和任一行故障全回滚。

补充 eligibility 必测：仍为 `CLEAN` 但已有 deposit、withdrawal、interest 或 account fee 的账户必须拒绝通用 bootstrap；这些事实只在满足 `source_bind_eligible` 时允许首次 IBKR source binding。

#### JRN-013 Source binding 与 IBKR Flex 安全 preview

完成定义：

- 建立 owner-scoped `ImportSourceBinding`、`SourceStatement`、`ExternalExecution`、immutable `ExternalSourceObservation`、`StatementExecutionSighting`、`SourceCaseEvidenceSighting`、versioned `ExternalTradeApplication`，以及 `SourceReconciliationCase` schema 和 `OPEN/RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 创建/收口能力。JRN-013/014 创建/复用 episode、附加 evidence、用更晚权威 sighting 收口旧 case 并按统一函数重算 health；JRN-015 才启用人工 reject/apply transitions。`ExternalExecution` 保存 `current_trade_observation_id`、`ACTIVE/ACCEPTED_TOMBSTONE` disposition 与可空唯一 same-binding `canceled_by_observation_id`；application 保存 derived direction/action、pre/post quantity 和 canonical fact linkage。落实 4.5 的 statement/sighting/observation/case episode/partial unique 约束与 composite FK/check。Beta 每个内部账户生命周期内最多一个 binding；同一 owner 的 `(adapter_kind, normalized_external_account_ref)` 在生命周期内只能绑定一个账户；每个 `(binding, external_execution_id)` 唯一。binding archive 永不释放这些唯一槽位；Beta 不支持 rebind/transfer。首次 confirm 必须二次显示掩码 external account 与目标账户，选错内部空账户只能重命名该账户，不能搬移已应用事实。
- schema 同时建立 immutable `StatementCoverageAcceptance`。每条 acceptance 必须 same-binding 链接 `SourceStatement` 与成功 confirm session/operation，并记录 accepted source-state revision/timestamp；`(binding,statement)` 唯一。pending/conflicted/failed/expired preview 不写 acceptance，不能从 SourceStatement 存在本身推导 accepted frontier。
- adapter allowlist 只启用 `IBKR_FLEX_XML_V1` 文件上传。冻结并版本化必需字段，至少覆盖 account、单一 statement 的 from/to date、statement generation marker（V1 预期为 `whenGenerated`）、account inception date 或显式期初 OpenPositions snapshot、普通 execution 的 `ibExecID`、provider-declared event kind、独立 cancel/correction 的 stable source event ID 与 target（若有）、数值 `transactionID`、asset category/conid、symbol、exchange、currency、buy/sell、quantity、trade price/time、open/close indicator、execution/cancel-bust status，以及 commission/currency；未知枚举或不稳定 source event identity fail-closed。文件必须恰好包含一个 external account 和一个 FlexStatement。
- canonical action 真值表固定为：`BUY+OPEN -> LONG OPEN/ADD`、`SELL+CLOSE -> LONG REDUCE/CLOSE`、`SELL+OPEN -> SHORT OPEN/ADD`、`BUY+CLOSE -> SHORT REDUCE/CLOSE`，具体 OPEN/ADD/REDUCE/CLOSE 由该方向 replay state 决定。首次 bootstrap 每组从 0 开始；已有 binding 的增量/纠错从完整 current-accepted source history 与 suffix 前状态继续。running quantity 不得为负，单 execution 不得跨零；否则返回 `UNSUPPORTED_CROSS_ZERO`。
- preview 的 derived action、pre/post quantity、FIFO/fee 与 chronology validation 必须调用 JRN-008 canonical lifecycle writer 使用的同一 pure simulation/domain rules 和 golden vectors；不得在 adapter 内复制第二套会计状态机。JRN-013 的 parser/schema/provider-evidence 子项可提前开发，但任务退出门必须等 JRN-008 完成并通过交叉一致性测试。
- `source_payload_fingerprint` 使用版本化、排序字段固定的序列化，至少覆盖 adapter kind/version、normalized external account、event kind、external source event/execution/affected execution ID、transactionID、instrument/conid、raw side/open-close、quantity、price、occurred_at UTC、source timezone、currency、normalized fee/currency、execution/cancel-bust status 和 **provider-declared** correction target；不得包含 statement generation/file hash、用户选择的 target 或 replay-state 派生的 direction/action/pre-post quantity。后两类只进入 case/application version。
- XML parser 禁止 DTD/entity/XInclude，限制 10 MB、5,000 executions、节点数、属性数、嵌套深度和字段长度；每 owner 最多 2 个 nonterminal session 和 10 分钟 10 次 upload。遵守 4.5 的 `0700/0600` 临时文件、finally unlink 与 orphan scavenging 合同。文件必须恰好包含一个 external account，所有可确认 execution 都必须有真实 `ibExecID`，禁止 `symbol:time:index` fallback。
- adapter enable gate 必须建立逐语义 provider evidence matrix，而不是用一份普通 fixture 证明全部合同。来自同一文档化 Flex Query 模板的脱敏真实 fixtures/statement pairs 至少分别证明：基础 execution 字段、跨 generation 重叠与 marker 严格顺序/tie、account inception 或完整 OpenPositions boundary、`transactionID/openCloseIndicator`、独立/同 ID cancel-bust/correction target、commission sign/currency。官方字段合同与真实 fixture 缺一不可；synthetic fixture 只补恶意输入和边界。任一必需语义无法证明时 `IBKR_FLEX_XML_V1` 保持 `FEATURE_DISABLED`，JRN-013 不得关闭。
- provider evidence 还必须冻结 statement `fromDate/toDate` 的 inclusivity 与 source timezone 语义，并规范为半开本地日期 `[coverage_start, coverage_end_exclusive)`；禁止从 execution rows 反推。binding 保存 `accepted_coverage_through_exclusive`。已有 binding 的 pending statement coverage 并集必须与 accepted coverage 重叠或首尾相接；断档归为 statement-level `SOURCE_COVERAGE_GAP`，session 进入 `CONFLICTED`、completeness 保持 `PENDING_IMPORT`，但不伪造 execution case。后续 bridging statement 可让新 preview 纳入 binding-wide pending coverage/NEW 全集。无 execution 的 statement 也保留 coverage evidence；`transactionID` 数值不连续不构成 coverage gap。
- 首次 source preview 只允许满足除文件内 `flat_boundary_proven` 外其余 `source_bind_eligible` 条件的账户，并要求选择显式 IANA source timezone。flat boundary 仅在以下之一成立时为真：statement `from_date <= account_inception_date`；或文件显式包含覆盖完整 external account 的 `from_date` OpenPositions snapshot 且没有任何 non-zero supported position。随后每个 `(instrument, direction)` 从 0 重放且不跨零。缺失/不完整证据返回 `SOURCE_FLAT_BOUNDARY_UNPROVEN`，不能因首行看似 OPEN 而猜测。已有 binding 时只接受与其 adapter/account identity 完全一致的文件。
- source upload 强制 operation-scoped `Idempotency-Key`，再按 4.5 的固定优先级生成 `source_payload_fingerprint` 并分类。同一 statement 内相同 external source event ID + 相同 fingerprint version/fingerprint 合并为一个 normalized observation 并显示 duplicate warning。未绑定 bootstrap 的同 ID + 不同 fingerprint version/fingerprint 默认是 conflict；唯一例外是下一条 change-chain recognizer 成功消费的 provider-declared correction/cancel-bust rows。已有 binding 时，每个不同 statement generation/file hash 的出现都写幂等 permanent sighting，即使分类为 ALREADY_IMPORTED；未绑定首 preview 只在 ImportSession/Row 保存 normalized generation/file/change evidence，confirm 前不创建 binding/statement/observation/sighting。`latest_authority_generation` 按 4.5 跨 trade/cancel/correction lineage 推导。`ALREADY_IMPORTED` 必须匹配 current active trade 或 accepted correction/cancel-bust observation 的 `(external_source_event_id,fingerprint_version,fingerprint)`。严格更早 generation 的已知 superseded/reversed trade，或已由 terminal case supersede 的 target-known change，为 KNOWN_HISTORICAL；严格更早且此前未见的 same-execution trade/target-known change payload 为 STALE_SOURCE_OBSERVATION；二者都 no-op。同 generation 或较新 generation 的历史 payload、其余尚未接受的 correction/cancel-bust、late new、source mismatch 或 ambiguous order 都不能静默 skip。`TARGET_UNRESOLVED` 因无 authority target 永不进入 strict-earlier stale 分支。
- 未绑定账户的 preview 在普通同-ID payload conflict 判定前，先在 owner/account-bound ImportSession/Row 运行 bootstrap change-chain recognizer。只有 provider-declared `event_kind`、稳定 change identity、明确 target、完整 source order 且 chain 闭合的 correction/cancel-bust rows 才可被消费：被替代 trade 标记 `BOOTSTRAP_SUPERSEDED`，最终取消的 target 标记 `BOOTSTRAP_ACCEPTED_TOMBSTONE`。每个普通 trade 或已折叠 chain 形成一个 `BOOTSTRAP_EFFECTIVE_NEW` economic unit；其 winning observation 可以是 CORRECTION，但 confirm 单位是整个 chain，不是 raw row。所有 effective active units 从 flat state 重放。同 ID 不同 fingerprint 若无这些 change 语义，则 session 固定以 `CONFLICTED + SOURCE_BOOTSTRAP_CONFLICT(reason=PAYLOAD_ID_COLLISION)` 终止。首次含 effective unit 的 confirm 原子创建 binding、statements/sightings/observations/executions/tombstones，应用全部 bootstrap-effective units，并将 chain 中每个 correction/cancel-bust observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 记为已消费的 accepted/superseded lineage；winning correction 设置 target `current_trade_observation_id`，最终 cancel 设置 accepted tombstone/canceled-by。零成交但 flat boundary 与 coverage 均已证明的首份 statement 也属于 binding-effective confirm：它原子创建 binding、statement、coverage acceptance 和 watermark，但不创建 execution/application/canonical trade fact。source confirm 不允许 partial selection。不为已在单文件内确定解决的历史 correction 生成 canonical compensating facts。payload collision、target 缺失/歧义、change identity 不稳定或 correction chain 不闭合都只保留 session evidence，提示扩大 statement 范围或修正 Flex Query；不创建 binding/execution/permanent source records/case/canonical facts，也不能在未绑定状态走 JRN-015。
- 已有 binding 的 conflict 才创建幂等 immutable observation/sighting/case episode。同一 nonterminal episode 附加 `SourceCaseEvidenceSighting`；terminal 后任一新的 trigger sighting 以 `trigger_sighting + against_source_state_hash + case_kind` 创建新 episode，即使 baseline hash 未变；相同 upload/sighting 重放不创建 episode。严格更晚 sighting 可将旧 OPEN/DIVERGED_REJECTED case 原子收口为 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 并链接 winner；winning payload 仍冲突时在同一事务建立新的 OPEN episode。之后调用统一 `recompute_source_health(binding)`：任一 DIVERGED_REJECTED -> SOURCE_DIVERGED；否则任一 OPEN/RESOLVING -> RECONCILIATION_REQUIRED；否则 HEALTHY。已有 divergence 不得因新 OPEN case 被降级，相同 upload/sighting 重放复用 case/evidence。
- preview 不写 canonical facts；只有首次 binding-effective confirm 才创建 binding。external account 在 API/UI/log 中掩码。在线 `/api/broker-sync/**`、Flex token/query setting、Binance secret/job 仍按 JRN-001/003 hard-off。

必测：脱敏真实 fixture/provider-contract gate、statement generation marker 缺失/非法/时区/严格代际/tie、四格 side/open-close 真值表、replay 前后 derived action 改变但 source fingerprint 不变、from-date 覆盖 inception、显式空 OpenPositions、非零/缺失/不完整期初 snapshot 返回 SOURCE_FLAT_BOUNDARY_UNPROVEN、running quantity 负数与 cross-zero、合法 bootstrap/重叠预览、同 ID 同/不同 payload、同 statement 同 event ID+同 fingerprint exact duplicate 合并而不同 fingerprint 各自持久 sighting/conflict、未绑定同 ID 不同 fingerprint 只有 provider-declared change chain 完整时折叠而普通重复固定 conflict、独立 correction event C2 指向 E1 且绝不归为 NEW、accepted correction/cancel-bust 的 `(external_source_event_id,fingerprint_version,fingerprint)` exact 重传为 ALREADY_IMPORTED 而同 identity 新 fingerprint 为 conflict、F1@G3 后首次见 F2@G2 为 STALE_SOURCE_OBSERVATION 且不冻 health、F1 -> F2 resolved -> F3 -> 新 sighting 重申 F2 可创建新 episode、F2 case OPEN/REJECTED 后 F3 strict-later 将旧 case 收口为 RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY 并保留 winner lineage、rejected F2 被更高 generation 重申时 evidence attachment 不短路 authority comparison 且同事务关旧 episode/开新 episode、terminal 后同 baseline 的新 trigger sighting 可建 episode 而相同 sighting replay 不建、against-state snapshot/hash 同输入稳定且 current observation/application/group boundary 任一改变即变化、首次未绑定 target 明确且 chain 完整的同 ID/独立 ID correction/cancel 折叠为 BOOTSTRAP_SUPERSEDED/BOOTSTRAP_ACCEPTED_TOMBSTONE，只有 target 歧义/缺失或 chain 不闭合才从 UPLOADING 直达 CONFLICTED 且只持久 session evidence、不建 binding/case、已绑定 conflict 创建/复用/附加 evidence case episode 并按聚合函数重算 health、跨 ID cancel 纳入 target latest_authority_generation 且 canceled_by 对 target 唯一/same-binding、source fingerprint 全字段且 provenance/derived application 字段不进入 fingerprint、fingerprint version migration、缺失 ID/transactionID、单文件多账户/多 statement、账户不匹配、两个内部账户可同时 preview 且不提前建立 binding（confirm unique race 由 JRN-014 验收）、两用户交换 binding/execution/observation/sighting/case ID 全拒绝、binding archive 不释放槽位、rebind/transfer API 不存在、未知 asset/open-close/side、完整 source_order_key、group append boundary、incremental 从已接受 history 继续、duplicate transactionID 的 commutative tie 与财务敏感拒绝、显式 timezone 与 DST、naive time 不默认 UTC、恶意 DTD/entity/XInclude、5,000/5,001 execution、节点/属性/深度/字段/10 MB、2/3 active session 和 upload rate 边界、跨用户、进程重启、CONFLICTED 第 30 天 preview cleanup、全部原文件清理路径和 external account 掩码。

补充边界必测：未绑定普通同-ID payload collision 固定返回 `SOURCE_BOOTSTRAP_CONFLICT(reason=PAYLOAD_ID_COLLISION)`，只留 session evidence 且零 binding/source/canonical 永久写入；binding archive 后不可重新绑定；Jan -> Feb 首尾相接、Jan -> Jan/Feb overlap、Jan -> Mar 断档、上传 Feb 后桥接 Jan/Mar、完全无 execution 的月份、同区间完全重复，以及 transactionID 数值跳号但 coverage 连续。另验证 preview/CONFLICTED statement 没有 acceptance 且不推进 frontier、空 statement confirm 产生 acceptance、cleanup/进程重启后仅从 acceptance 重建相同 watermark/completeness；C2@G2 rejected -> C3@G3 strict-later terminal-supersede 后，旧 C2 statement 重分类 historical 并可 full-confirm coverage，而 G3 同代或 G4 更晚重申 C2 必须创建新 episode；accepted C2/F1@G2 后首次见 C2/F0@G1 必须 stale no-op，而 C2/F0@G2 或 G3 必须 `SOURCE_PAYLOAD_CONFLICT`。

#### JRN-014 Source-bound incremental canonical confirm

完成定义：

- 首次 source confirm 在 account lock 内复验完整 `source_bind_eligible`（包括 trade_history_empty、currency、unique slot、flat boundary）和文件 source identity；已有同币种 non-trade cash facts 可以保留。含 `BOOTSTRAP_EFFECTIVE_NEW` unit 的 confirm 与全部 canonical facts 一次 commit 创建 binding、完整 statement/sightings/observations/external executions、JRN-013 已折叠且已标记 accepted/superseded 的 change lineage、current corrected observations/accepted tombstones、全部 effective active applications、`PositionEvent`/ledger、session completion、`CLEAN -> SOURCE_BOUND`、`source_health = HEALTHY` 和 `source_completeness = CURRENT`。零成交但 flat boundary 与 coverage 均已证明的首份 statement 以 `COMPLETED` 完成同一状态转换并创建 binding、SourceStatement、`StatementCoverageAcceptance` 和 watermark，但不创建 execution/application/canonical trade fact；不能把这项永久 coverage 写入伪装成 `COMPLETED_NOOP`。tombstone target 不产生 canonical trade fact；若 concurrent confirm 已占用 external account 或目标账户 binding unique slot，则本请求稳定 409 且零 canonical/source side effect。
- 首次 binding-effective source bootstrap 创建 binding 时，必须在同一事务为首批全部 SourceStatement 创建 `StatementCoverageAcceptance`，将 proven flat boundary 到 statement end 建成 accepted frontier；任一 canonical/source/acceptance 写入失败都回滚整个首次 confirm。
- 已为 `SOURCE_BOUND` 的账户只接受同一 binding 的完全重复、窗口重叠或纯增量文件，不再要求 `source_bind_eligible`。`ALREADY_IMPORTED` 固定无 canonical side effect，但新 statement provenance 仍幂等写 `SourceStatement/StatementExecutionSighting` 并推进可重建 latest-authority projection；accepted correction/cancel-bust 只有 `(external_source_event_id,fingerprint_version,fingerprint)` 都匹配时才 no-op。`KNOWN_HISTORICAL_OBSERVATION` 和 `STALE_SOURCE_OBSERVATION` 均固定为 stale no-op + warning；此前已 sighted 但未 accepted 的 ordinary execution 仍可为 `NEW` 并令 completeness 为 PENDING_IMPORT。source preview 必须展示 binding 当前全部 pending NEW；confirm 不接受 row IDs/selection，而在 `source_health = HEALTHY` 时原子应用 preview digest 中每个 `(instrument,direction)` 的完整连续 pending set。任一 pending group 有 gap、late row 或无法从 current accepted boundary 连续重放时整批 conflict，不能跳过该 row 继续。
- source confirm 同时消费 binding-wide pending statements/coverage extensions 与 pending NEW。coverage intervals 必须从 acceptances 重建的 `accepted_coverage_through_exclusive` 连续，断档稳定返回 `SOURCE_COVERAGE_GAP`；补齐后同一 full confirm 可消费桥接后的全部连续区间。没有 NEW 的合法相邻 statement 进入 `COMPLETED_NOOP`，但仍为每个 consumed statement 写 immutable `StatementCoverageAcceptance` 并原子推进 coverage。preview 一旦出现无 acceptance 的 coverage extension 就令 `source_completeness = PENDING_IMPORT`。只有 acceptances、coverage watermark、source application、session completion 和 completeness 在同一事务提交后才恢复 `CURRENT`，且 UI 仍显示该 watermark，而不是声称实时同步到券商当前时刻。
- `SOURCE_PAYLOAD_CONFLICT`、`LATE_NEW`、`SOURCE_SEQUENCE_GAP`、correction、cancel-bust 和 `TARGET_UNRESOLVED` 必须进入持久 reconciliation 状态并阻止普通 confirm；不能原地修改旧 source execution、把独立 change event 当成 NEW，或借 Import 绕过 JRN-010。除 provider order 可证明的 strict-later authority sighting 可按 JRN-013/014 自动将旧 episode 收口为 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 外，其余冲突只能由 JRN-015 的 versioned resolution command 处理；相同或更早的普通重传不会自行消除冲突。
- confirm 强制无 TTL `Idempotency-Key`；请求顺序为 auth/owner -> terminal idempotency lookup -> matching replay -> state/TTL，再按 account -> source binding -> positions 加锁。锁内按相同 schema 重算完整 `source_preview_digest`；pending IDs 未变但 accepted coverage/pending intervals、correction/replay、current observation/application、append boundary 或任一 preview derived amount/action 改变也必须返回 409 `SOURCE_PREVIEW_STALE`，且不应用未展示/已变化 rows。相同 digest 的 confirm 必须消费全部连续 pending coverage 与 pending NEW，成功后重建 `source_completeness = CURRENT`。同 binding 的并发 session 以 CAS/unique 保证每个 observation/application 最多接受一次；`COMPLETED/COMPLETED_NOOP/CONFLICTED` 同 key/hash 跨 TTL 返回原响应。任一 unique race 转为 replay/no-op/conflict，不返回 500。
- source statement/sighting、source event/execution identity、source payload fingerprint、current trade observation/canceled-by tombstone、immutable observations、application linkage 和响应永久保留；30 天 cleanup 只删 preview rows。accepted coverage watermark 仅在成功 source confirm 事务中推进，不能作为 execution 去重或 latest-generation 依据。
- source-bound 后普通手工 trade command 稳定返回 409；narrative/review、daily note、资金流水、cash dividend 和受审计 correction 仍按各自权限可用。
- commission 遵守 JRN-005/006 的单 event 聚合 fee 和币种合同；source confirm 与 JRN-007/008 canonical writer 单事务。已有 binding 的领域冲突以零 canonical side effect 持久化 statement/sighting/observation/case，调用唯一 `recompute_source_health(binding)` 聚合函数，并持久化 `CONFLICTED` session 终态和冲突响应；未绑定首文件歧义遵守 JRN-013 的 session-only 规则。技术错误或财务写入失败则整个 confirm 事务回滚，不留下部分 binding/sighting/execution/event/ledger/application/watermark。

必测：首次 source bootstrap 在 pure empty/opening balance，以及已有同币种 deposit/withdrawal/interest/account fee 时成功；已有 cash dividend/position/trade history、异币 cash fact 或 generic bootstrap 时拒绝。零成交且有 proven flat boundary/有效 coverage 的首次 confirm 为 `COMPLETED`，创建 binding/statement/acceptance/watermark 且零 execution/application/canonical trade fact；含 effective unit 的 confirm 全量应用所有 `BOOTSTRAP_EFFECTIVE_NEW`，任何 row-selection payload 拒绝。已有 binding preview 后过期的 observed-but-unapplied execution 保持 NEW/PENDING_IMPORT，下一 preview 必须纳入 full set。target 明确的同 ID 与独立 ID correction/cancel chain 在首次 statement 内折叠，confirm 创建完整 statement/sighting/superseded/tombstone lineage 且 canceled trade 无 canonical fact；T0->C1->C2 与 T0->C1->cancel 的每个 consumed change `(external_source_event_id,fingerprint_version,fingerprint)` 在重叠文件中均 no-op/historical，不重开 correction case；歧义 target 零 source/canonical 写入。source-bootstrap-vs-generic-confirm/manual-OPEN 在 account lock 后最多一个成功；source-bootstrap-vs-同币种 deposit 可串行后都成功且无混合 trade facts。还需覆盖两个账户抢同 external account 的 confirm unique race、同文件重传不新增 sighting、新 generation 同 fingerprint 写新 sighting 但不记账、F1@G1 -> F1@G3 sighting -> F2@G2 不得当最新可应用、相邻月份重叠旧+新只写新、F1 -> correction F2 后旧月报重传 F1 stale no-op、独立 correction/cancel event 应用后重复同 `(external_source_event_id,fingerprint_version,fingerprint)` 为 ALREADY_IMPORTED 而同 identity 新 fingerprint 为 conflict、target tombstone/canceled_by same-binding 约束、旧月报重传原 execution stale no-op、同 generation 或较新 statement 重申历史 fingerprint 进入 conflict、DIVERGED + 新 OPEN 仍 DIVERGED；清 rejected 后有 OPEN 则 RECONCILIATION_REQUIRED；全清才 HEALTHY、任一未清 case 已存在但新文件不含冲突行时仍阻断全部 NEW、同日同价量但不同 exec ID 均写入、同 ID 改内容/late new/correction/cancel-bust/SOURCE_SEQUENCE_GAP 在零 canonical 写入下持久化 CONFLICTED evidence、PENDING_IMPORT 立即降级 derived 且 full confirm 后 CURRENT、preview 后新增 pending row 或并发 correction/replay 即使 pending IDs 未变也因 digest 变化返回 SOURCE_PREVIEW_STALE、两用户交换 application/session/sighting ID 全拒绝、source mismatch、普通手工 trade 409、同 binding 并发 confirm、confirm-vs-account archive/correction、unique race、commit 后响应丢失及 COMPLETED/CONFLICTED 跨 TTL 同 key/hash 重放、commission/currency、技术/财务故障全回滚、cleanup 后仍去重、source/canonical/ledger reconciliation。

补充增量必测：完全不重叠但与 watermark 首尾相接的纯增量文件只应用 NEW；完全重复和窗口重叠文件不重复记账；Jan -> Mar 返回 `SOURCE_COVERAGE_GAP`，补传 Feb 后 binding-wide full confirm 一次消费连续 pending set；无 execution 月份以 `COMPLETED_NOOP` 写 acceptance 并推进 coverage；binding archive 后不可用新内部账户或原账户 rebind；coverage/digest 并发变化返回 `SOURCE_PREVIEW_STALE`。还需覆盖 acceptance/confirm/idempotency linkage、每 statement 最多一次 acceptance、commit 后响应丢失重放不重复 acceptance、scalar watermark 与 acceptance 重建不一致时 fail-closed，以及被 strict-later authority 终止的旧 correction/cancel statement 能 stale no-op 后取得 acceptance。

#### JRN-015 Source correction 与 versioned replay

完成定义：

- 在 JRN-013/014 已创建的 case episode schema 上启用人工 resolution 状态机：`OPEN -> RESOLVING -> RESOLVED_APPLIED|DIVERGED_REJECTED`，`DIVERGED_REJECTED -> RESOLVING -> RESOLVED_APPLIED`；另允许 JRN-013/014 在 strict-later authority ingestion 时将 `OPEN|DIVERGED_REJECTED -> RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY`。每次转换使用 CAS，并永久记录 owner、actor、reason/request ID（自动收口记录 system actor）、trigger/evidence/winning sightings、against state、受影响 applications/events 和响应。terminal case 永不 reopen。
- case 创建、reject、apply 和 authority-supersede 后都调用同一个 `recompute_source_health(binding)`：任一 `DIVERGED_REJECTED -> SOURCE_DIVERGED`；否则任一 `OPEN/RESOLVING -> RECONCILIATION_REQUIRED`；`RESOLVED_APPLIED/RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 均视为已清；否则 `HEALTHY`。`DIVERGED_REJECTED` 不改变 canonical facts 或 `trade_source_state = SOURCE_BOUND`。两个非健康结果都阻止后续 source confirm、可信 derived 指标和 release gate。correction/cancel-bust 的 provider-declared target 留在 source fingerprint。target 缺失时 case 保持 `TARGET_UNRESOLVED/OPEN`，重复 sightings 只附加 evidence，不能执行 target authority comparison 或自动 supersede；用户选择的 exact owner/same-binding target 只存 resolution/application/authority lineage，不能回写 observation fingerprint。resolution 在锁定 target 后保存 target-state snapshot/hash，重新复验 owner、same-binding、event semantics、latest authority 和 replay；只有 `RESOLVED_APPLIED` 后该 user-target lineage 才进入 target 的 `latest_authority_generation`。无法唯一关联时保持 OPEN。
- `RESOLVED_APPLIED` 在 account -> binding -> positions 锁内找出每个受影响 `(instrument, direction)` 从最早 conflict 起的 applied source suffix：先按从新到旧创建 compensating void/reversal，再插入 late/corrected observation 或移除已 cancel/bust 的 application，最后按 source 稳定顺序从旧到新重放完整 suffix。
- 原 source statements/sightings/observations、canonical facts 和 applications 不删除；旧 application 标为 `SUPERSEDED/REVERSED`，replacement application 使用递增 version 并记录 `replaces_application_id`。payload correction/late insertion 更新 `current_trade_observation_id`，并将 correction observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 标记 accepted；已应用 cancel-bust 将 target execution 设为 `ACCEPTED_TOMBSTONE`、`canceled_by_observation_id` 指向 same-binding 独立 cancel observation 且 active application 为空，并将 cancel observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 标记 accepted。每个 observation/version 最多应用一次。
- replay 使用 JRN-005 至 010 的相同会计、chronology 和 canonical writer；narrative/review/checklist 通过 source/application replacement lineage 保留可追溯关系，不能因财务 replay 丢失用户日志内容。
- 提供 owner-scoped case list/detail API 与前端冲突工作流：展示旧/新规范化字段差异、受影响 lifecycle 和 REJECT 将导致 SOURCE_DIVERGED 的后果。`APPLY_VERSIONED_REPLAY` 必须有 exact owner/same-binding target；`REJECT_AS_DIVERGED` 对 `TARGET_UNRESOLVED` 允许 target=null，并保持 binding-scoped divergence。两种命令都强制 reason 与二次确认；普通用户不能输入任意 internal ID 或越权 target。
- 已知 target 的 resolution 在写入前锁定并复验 `latest_authority_generation`；`TARGET_UNRESOLVED` 必须先按上一条锁定并验证用户 target，不能直接进入本段的 authority-supersede 分支。若已有 strict-later winning sighting 且无 provider lineage 证明当前 observation 优先，则不保持永久 OPEN：原子转为 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 并链接 winner；winning payload 仍与 canonical current 冲突时，在同一事务创建/复用针对当前 baseline 的新 `OPEN` episode，最后才重算 health，并以零 canonical side effect 返回。否则 `RESOLVING` 与其余 work 在同一数据库事务/锁范围内；全部 compensating facts、replacement events/ledger、accepted trade observation/canceled-by tombstone、case 终态、source_health 重算和 derived invalidation 一次提交。任一失败全回滚到命令开始前的稳定状态：从 `OPEN` 发起仍为 `OPEN/RECONCILIATION_REQUIRED`，从 `DIVERGED_REJECTED` 发起仍为 `DIVERGED_REJECTED/SOURCE_DIVERGED`，不得留下半个 replay 或 stranded RESOLVING。

必测：case list/detail owner 隔离、case 创建即 RECONCILIATION_REQUIRED 且阻止不含冲突行的后续 NEW/可信指标、字段 diff/target/reason/二次确认 UI、payload correction、late new 插入、correction/cancel-bust 有/无明确 target、TARGET_UNRESOLVED 重传只附 evidence 且不做 authority supersede、用户 target 越权/跨 binding 拒绝、成功 APPLIED 后 lineage 才进入 target authority generation、accepted tombstone 与重复 cancel no-op、REJECT_AS_DIVERGED 原子降级、同 case 后续 APPLY 清除最后一个 divergence、多个 OPEN/diverged case 未全清时不恢复、两用户交换 reconciliation case/observation/application ID 全拒绝、同 case/key 重放、不同 resolution payload 409、两个 resolver 并发最多一个成功、纠正后同文件成为 ALREADY_IMPORTED、bust 后较旧原 execution 为 KNOWN_HISTORICAL 而同/较新 generation 重申为 conflict、resolution-vs-strict-later race 在 winner 仍冲突时原子关旧/开新且不恢复 HEALTHY、跨多个后续 lifecycle 的逆序 void/正序 replay、replay 令 derived action 改变但 source fingerprint 稳定、partial close/FIFO/fee、narrative lineage、分别从 OPEN 与 DIVERGED_REJECTED 发起且任一 replay 阶段故障时回滚原稳定状态、旧/新 application 唯一性和 source/canonical/ledger reconciliation。

补充 resolution 必测：`TARGET_UNRESOLVED` 允许以 `target = null` 执行 `REJECT_AS_DIVERGED` 并保持 binding-scoped divergence；`APPLY_VERSIONED_REPLAY` 缺 exact owner/same-binding target 时稳定拒绝。

退出门：系统不能越权、重复、半写、硬删除已有财务事实/ImportSession 的账户或产生不可对账金额；纯空账户仍按 4.3 可硬删除。通用 bootstrap 与 source-bound incremental/correction 共用 canonical writer，Import session 可恢复，每个 observation/application version 最多应用一次且每个 ACTIVE execution 最多一个 active application，ACCEPTED_TOMBSTONE 没有 active application。

### M2：JOURNAL_COMPLETE

#### JRN-016 Derived freshness 与故障恢复结果门

完成定义：

- 发布门是 canonical 写入立即可读、Timeline/Lifecycle/Dashboard 在冻结 SLA 内一致且能重建，不是必须存在某个 worker 容器。
- derived snapshot 带 source watermark/version；旧任务重试不得覆盖更新 snapshot；stale 时回退 canonical read 或显示明确 degraded，不伪造 freshness。
- account 的 `accounting_health = ACCOUNTING_RECONCILIATION_REQUIRED`，其 binding 真值投影的 `source_health` 为 `RECONCILIATION_REQUIRED/SOURCE_DIVERGED`，或 `source_completeness = PENDING_IMPORT` 时，Timeline/Lifecycle 可保留带 warning 和 last-confirmed watermark 的 canonical history，但 Dashboard/derived 指标必须立即明确 degraded 且不能展示为当前可信完成。只有 JRN-006/JRN-015 分别清除账务 divergence 与全部未决/diverged source case，并由 source full confirm 将 completeness 恢复为 CURRENT，才能恢复可信指标。
- 若保留 DB relay/worker：两个 relay 只能生成一个 unique job，大批 Import 按 aggregate/watermark coalesce，handler 可重放，health 证明进程、DB 和最近 heartbeat，支持 graceful shutdown/stale recovery。
- 若同步/按需 rebuild 达到相同验收，可不部署常驻 worker；必须记录 ADR、负载证据和恢复路径。

所有方案必测：derived 不可用时 canonical fallback、RECONCILIATION_REQUIRED/SOURCE_DIVERGED 指标立即降级且清除后恢复、PENDING_IMPORT 显示 last-confirmed as-of 且 full confirm 后恢复 CURRENT、旧 watermark 不覆盖新结果、completeness/derived 重建结果一致。ADR 选择同步/按需方案时，验证零多余 outbox/job、代表性负载和 rebuild；选择保留 relay/worker 时，验证并发 relay、Import job coalescing、崩溃重放、积压恢复和 health 失真。

#### JRN-017 核心日志与复盘可信读体验

完成定义：

- Timeline、Lifecycle 和 realized Dashboard 读取同一 canonical truth/可信 projection；Dashboard GET 不写业务状态。
- 无 Market Data 时不展示伪造 current price、market value、unrealized 或 risk；明确显示 unavailable 或隐藏非核心指标。
- 核心页覆盖 loading/empty/error/partial；手工事实不堆 trust badge，只有 derived 状态显示简化 source/as-of/stale。
- 完整主链覆盖创建策略和规则/checklist、OPEN/ADD/REDUCE/CLOSE、immutable checklist snapshot、narrative/review revision、daily note revision、纠错、重载和跨日分组；日志内容修订不改写财务 event。
- Desktop 与 390px 下可完成记录和复盘，DOM/键盘顺序合理。

必测：上述 E2E、两用户隔离、data/empty/error/partial、时区跨日、derived degraded、1440x900 与 390x844 浏览器流程。

#### JRN-018 Canonical 用户数据可携带导出

完成定义：

- 导出 accounts、canonical positions/events、ledger/transactions、strategies/checklists、narrative/daily-note revisions、Import audit linkage、source binding/state/health/completeness、accepted coverage watermark、`StatementCoverageAcceptance` 及其 confirm linkage、SourceStatement 原始日期/规范化 coverage/sightings、external source observations/fingerprints、current trade observation/canceled-by tombstones、reconciliation cases、versioned application/replacement lineage 和必要 source IDs。
- 只导出当前用户；Unicode/中文、Decimal 原精度、UTC ISO-8601、IANA timezone、金额和记录数可对账。
- CSV/JSON 有 manifest、schema version、生成时间和 checksum；大数据集流式处理，可由独立 parser 读取。
- archive/void/reversal 全部保留并可区分；不把 legacy projection 当第二份事实导出。

必测：owner 隔离、金额/数量/记录数、source binding/health/completeness/accepted coverage、statement 原始日期/规范化 coverage/acceptance-confirm linkage、sighting/event/execution/observation/application/tombstone/case/divergence linkage、fingerprint/application version、中文、空账户、较大数据集、checksum 和 parser round-trip。

退出门：用户能完整记录、复盘、纠错和导出；核心页面不依赖外部行情，不伪造 freshness，derived 故障可降级恢复。

### M3：BETA_READY

#### JRN-019 生产启动与 migration gate

完成定义：

- Compose production profile 强制 `AUTO_CREATE_SCHEMA=false`；独立 migration job 成功后才启动 API 和可选 worker。
- 所有进程使用同一配置来源；缺失配置、弱 secret、capability ceiling 或 migration failure 时 fail-fast。
- 从 JRN-000 baseline head `9cad10111213` 向最终 release head 的所有 revision 均被跟踪；空库和脱敏存量快照均能升级，记录支持窗口内 rollback/downgrade 或 forward-fix 策略。
- JRN-018 关闭时记录 final release schema manifest 和 Alembic head；设施实现可以提前，但 migration 证据只能在该 freeze 后生成。JRN-019/020/021 原则上禁止新增 schema revision；若确需新增，必须重新打开 JRN-018 freeze，使旧证据失效并强制重跑 JRN-019。

必测：空库、存量快照、migration failure、弱配置、capability 缺失和启动顺序。

#### JRN-020 单一 PostgreSQL 备份恢复路径

完成定义：

- 复用或替换 Compose backup sidecar，只保留一套正式 PostgreSQL backup 路径。
- 冻结加密/异地策略、保留期、完整性检查、告警和 restore 命令。
- Admin backup API 接同一 provider 或退役，避免两套互不相知的体系。
- restore 后执行 migration、owner 隔离、记录数量和 JRN-006 reconciliation invariant。

必测：backup -> restore -> migration -> smoke、损坏备份识别、恢复后账务和 tenant 隔离。

#### JRN-021 Staging 全链路与 invite-only Beta 发布门

完成定义：

- 真实 PostgreSQL staging 完成邀请、登录、账户、手工 lifecycle、纠错/void、资金、通用 bootstrap Import、IBKR source-bound bootstrap/重叠增量 Import、source conflict reject/correction replay、策略/checklist、daily note、Timeline、Dashboard 和导出。
- release-scope account 的 `accounting_health = ACCOUNTING_RECONCILIATION_REQUIRED` 必须为 0；`SourceReconciliationCase` 必须没有 `OPEN/RESOLVING/DIVERGED_REJECTED`，binding 真值及 account 投影的 `source_health` 必须没有 `RECONCILIATION_REQUIRED/SOURCE_DIVERGED`。所有 source binding 的 `source_completeness` 必须为 `CURRENT`，pending NEW 与尚无 acceptance 的 pending coverage count 都为 0，`StatementCoverageAcceptance` 重建 frontier 必须等于 scalar watermark。ledger scanner、case/application/tombstone/coverage-acceptance lineage、pending projection 重建、修复记录、reject reason 和解锁证据都纳入 go/no-go。
- 验证 derived accelerator 停止时的 canonical fallback、migration failure 和 backup restore；不要求任何默认关闭 provider。
- 按邀请人数、每用户账户/交易量和代表性并发冻结 Beta 容量预算，不沿用抽象“1000 用户”承诺。
- 冻结 capability ceiling/runtime flags、rollback/runbook、监控/告警和人工 go/no-go checklist。
- 用户文档、Import template 和对应确认/错误状态必须明确：通用 CSV/Excel 只允许 `generic_bootstrap_eligible` 账户一次 bootstrap；首次 IBKR source-bind 使用 `source_bind_eligible`，不能已有 trade history，但允许保留同币种的 opening balance、deposit、withdrawal、interest 和 account fee；cash dividend 因必须关联 position，不属于 pre-bind 允许事实。首次 IBKR statement 必须从 account inception 开始，或携带显式完整且全零的期初 OpenPositions snapshot，否则返回 `SOURCE_FLAT_BOUNDARY_UNPROVEN`。
- 未绑定首文件中 target 明确且完整的 correction/cancel chain 可在 session 内折叠为 economic units，并于首次 confirm 全量应用、原子建立 accepted correction/tombstone lineage。普通同-ID payload collision 固定返回 `SOURCE_BOOTSTRAP_CONFLICT(reason=PAYLOAD_ID_COLLISION)`；target 缺失/歧义、change identity 不稳定或 chain 不闭合也返回对应 reason 的 `SOURCE_BOOTSTRAP_CONFLICT`。这些冲突只保留 session evidence，零 binding/source/canonical 永久副作用，并提示扩大 statement 范围或修正 Flex Query。
- 成功 binding 后，同一 external account 可在同一内部账户导入完全重复、窗口重叠或纯增量文件，不需要每月新建账户。statement coverage 必须与 accepted watermark 重叠或首尾相接；断档返回 `SOURCE_COVERAGE_GAP`，补齐后才能 full confirm。无 execution 月份可用合法空 statement 以 `COMPLETED_NOOP` 推进 coverage。source confirm 不允许逐行排除，必须确认 preview 展示的完整 pending statement/coverage/NEW set；preview 后到 confirm 前 coverage、baseline、pending set 或 derived result 变化返回 `SOURCE_PREVIEW_STALE`。PENDING_IMPORT 期间 Dashboard 显示 last-confirmed coverage/as-of，不宣称实时同步到券商当前时刻。
- binding 不可 rebind/transfer，首次确认选错内部账户只能重命名该账户；已绑定后的 payload change、correction/cancel-bust、TARGET_UNRESOLVED、late new 和 sequence gap 进入持久 case 并立即冻结 NEW/可信指标。versioned replay 可清除对应 case；strict-later observation 只会收口旧 episode，且仅当 winning payload 与 canonical 一致、同时没有其他 `OPEN/RESOLVING/DIVERGED_REJECTED` case 时才解冻，否则新 episode 继续保持冻结。`REJECT_AS_DIVERGED` 会保留冻结，直到之后改为 apply 或被满足上述解冻条件的更晚权威 observation 取代。source-bound 账户禁止普通手工 trade；同方向 lifecycle 禁止普通 backdate；无 offset 时间按显式 IANA timezone 解释，DST ambiguous/nonexistent 返回 422。
- 通过后状态只能变为 `INVITE_ONLY_BETA_CANDIDATE`；人工 release approval、变更窗口和 checklist 签署后才进入 `INVITE_ONLY_TRADING_JOURNAL_BETA`。

必测：PostgreSQL integration、Desktop/390px 浏览器主链、通用一次性、CLEAN/flat-boundary、source-bound 增量/correction/full-confirm/PENDING_IMPORT 限制在文档/模板/相关 UI 状态中可见且与 API 一致、重叠导入和 conflict resolution 矩阵、在线 Broker Sync/secret/job 仍 hard-off、故障恢复、容量 smoke/soak 和 restore drill。

退出门：真实 staging 的 migration、恢复、核心浏览器流程和容量预算全部通过，并获得人工 release approval。

## 7. 依赖与并行策略

Release closure dependency spine（fork/join）：

- `JRN-000 -> JRN-001 -> (JRN-002 || JRN-003)`。
- `JRN-002 -> JRN-005`；`(JRN-002 + JRN-003) -> JRN-004`。
- `(JRN-004 + JRN-005) -> JRN-006 -> JRN-007 -> JRN-008 -> JRN-009 -> JRN-010`；`(JRN-004 + JRN-005) -> JRN-011`。
- `(JRN-010 + JRN-011) -> JRN-012`；`(JRN-003 + JRN-004 + JRN-005 + JRN-007 + JRN-008 + JRN-011) -> JRN-013`；`(JRN-012 + JRN-013) -> JRN-014`。
- `JRN-014 -> JRN-015 -> JRN-016 -> JRN-017 -> JRN-018 -> JRN-019 -> JRN-020 -> JRN-021`。

并行支线：

- JRN-002 与 JRN-003 在 JRN-001 后并行；JRN-005 是只冻结合同/golden vectors 的支线，可在 JRN-002 后开始，JRN-004 等 JRN-002/003，两支必须在 JRN-006 汇合。JRN-006 的任何会计实现仍须等 JRN-004/005 全部关闭。
- JRN-011 在 JRN-004/005 后可与 JRN-008 至 010 并行。JRN-013 的 source schema、纯 parser、安全限制和 provider evidence 可在 JRN-003/004/005/007/011 后提前准备，但依赖 running lifecycle 的 action/pre-post quantity、FIFO/fee preview、digest 与整个 JRN-013 退出门必须等待 JRN-008；收口阶段可与 JRN-009/010 并行。JRN-014 等 JRN-012/JRN-013 完成，JRN-015 再收口 source correction。
- JRN-018 的基础导出可在 JRN-009、010、012、014/015 schema 稳定后开始，但 narrative/daily-note revision 导出必须等 JRN-017 合同完成才可收口。
- JRN-019/020 的部署和备份设施可在 M1 后半段提前开发；但 JRN-019 只能在 JRN-018 schema freeze 后重跑空库/存量升级并关闭，JRN-020 随后使用最终 head 和 JRN-006 reconciliation 形成有效证据。

禁止并行混做：

- JRN-005/006 会计语义与 `backend/models.py` 纯结构拆分。
- JRN-007/008 canonical writer 与全量 legacy 表删除。
- JRN-011 至 015 Import 修复与在线 Broker Sync；只能复用纯文件 parser，不能顺带启用网络 route、secret 或 job。
- JRN-016/017 可信读修复与完整 materialized read-model 平台。

## 8. 通用 Definition of Done

每个任务必须同时满足：

1. release-scope 行为有正向、负向、并发/重放和 owner 隔离测试；不适用项写明原因。
2. PostgreSQL 特有事务、锁、unique race、timezone 和 migration 行为不得只用 SQLite 证明。
3. UI 变更测试真实组件/浏览器行为，不能只用 helper 或源码正则代替。
4. schema 变更有 Alembic revision、空库/存量升级、数据扫描和 rollback/forward-fix 说明。
5. feature gate 验证 API、UI、secret、job/outbox、部署 ceiling 和文档边界。
6. 账务任务证明 event/lot/position/ledger/journal balance 与 golden vectors reconciliation。
7. derived handler 可重放，失败有可理解终态、watermark 和 recovery path。
8. source Import 证明 binding/execution/application identity、payload conflict、late arrival、重叠窗口、并发 exactly-once 和 canonical/ledger reconciliation。
9. 更新对应 runbook/README/TODO，并记录验证命令、环境和结果。

任何任务不得用“文件存在”“路由存在”“历史计划已勾选”代替完成证据。

## 9. 当前执行批次

第一批只执行：

1. `JRN-000`：分类并 checkpoint 当前 WIP，固定 `9cad10111213` migration baseline 与 optional-code disposition。
2. `JRN-001`：冻结 release contract，关闭非日志能力并建立部署 capability ceiling。
3. `JRN-002`：建立可复现环境和 mandatory PostgreSQL CI。
4. `JRN-003`：完成 invite-only auth 与 release secret 治理。
5. `JRN-004`：完成 tenant/owner 边界矩阵和负向封闭。

JRN-000 必须先完成；之后 JRN-001 先行，JRN-002 与 JRN-003 可并行，JRN-004 等两者基础可用后收口。本“第一批”是当前调度上限，因此本批不启动 JRN-005；进入下一批后，JRN-005 合同/golden vectors 可按 DAG 在 JRN-002 后准备，但 JRN-006 会计实现与 canonical writer 必须等 Step 0/M0 和 JRN-005 全部通过。不得提前做 UI 扩展、模型拆分、在线 Broker Sync、Market、AI 或量化能力。

## 10. 计划评审

2026-07-16 由两个独立只读 reviewer 分别从“范围/发布门”和“任务可执行性/依赖”复审。初审 verdict 均为 `CHANGES_REQUIRED`，主要问题是会计口径可多解、账户和 legacy 可硬删、feature flag 可被管理员绕过、Import 合并规则缺失、worker 被误设为拓扑型 blocker，以及任务规模过大。

本版已完成以下修订：

- 将 Market Data 全部移出日志 Beta，禁用 Broker/Market/AI/PDF/风险，减少外部依赖。
- 增加 deployment capability ceiling、Finnhub/普通 setting secret 清理和 fail-closed 验收。
- 明确 journal balance、append-only ledger、FIFO entry fee 分摊、Decimal/rounding 和事件顺序。
- 明确账户币种冻结、历史账户 archive-only、void 与 archive 差异，以及关闭普通 `X-Migration-Fallback`。
- 2026-07-16 当时将通用 bootstrap 与首次 source binding 统一限定为 `import-clean`；2026-07-17 复审后拆为 `generic_bootstrap_eligible` 与允许同币种非交易 cash facts 的 `source_bind_eligible`，并放开 binding 建立后的同源增量。10 MB/5,000 行/24 小时、持久 session、instrument identity、timezone 和 replay 规则继续保留。
- 将 worker 改为结果型 freshness/recovery gate，允许同步或按需重建，不让 worker 成为 canonical correctness 依赖。
- 2026-07-16 版将原 14 个大任务拆为 19 个任务（JRN-000 至 JRN-018）；会计合同与实现、truth create 与 lifecycle、Import preview 与 confirm 分开估算，并修正 derived 依赖和核心日志 E2E 覆盖。
- 根据后续 WIP 复审增加 JRN-000，决定四个 Broker/Market migration 以 `IN_CHAIN_DISABLED` 纳入 `9cad10111213` baseline；同时冻结 `HEDGE_BY_DIRECTION`、单 event 聚合 fee、幂等/Import retention 和三项用户可见限制。
- 根据 Claude 后续审阅归档两份遗留 P10 文档，并补严更晚 non-void lifecycle 对旧 CLOSE reversal 的阻断、ImportSession 创建与账户删除的统一锁协议，以及 JRN-002/003 分叉、JRN-004/005 汇合到 JRN-006 的 release closure。
- 2026-07-17 根据用户对 IBKR 月度导入的复核，废止“所有成功 Import 后必须每月新建账户”的统一限制：通用 CSV/Excel 仍是一次性 bootstrap，`IBKR_FLEX_XML_V1` 则使用 immutable source binding 与 execution ID，在同一账户接受完全重复、窗口重叠或纯增量文件。
- 2026-07-17 JRN-001 精确 SHA `cf4766de0e843b0a58a1882b30b3fe8556e1a23a` 的三路独立评审均要求修改：关闭可跨租户写入且绕过 identity 的 legacy Import；以 canonical truth 判定 open/side 和 symbol filter；禁止只读 pre-upgrade identity 进入 ADD；隔离 runtime flag read 与 caller pending state；保留 duplicate-OPEN 的 position public ID 以恢复 ADD；用 Playwright 真实浏览器测试替换源码正则完成声明；所有修复必须进入新 checkpoint 并重新取得同一 SHA 双路批准。
- source-bound revision 增加 fingerprint/generation authority、旧 trade/change stale no-op、payload/correction/cancel reconciliation、binding-wide full confirm、永久幂等响应和 `TARGET_UNRESOLVED` 处理，避免重叠月报重复记账或旧更正反复开 case。
- 增加 statement coverage continuity 与 immutable `StatementCoverageAcceptance`：execution identity 证明事实不重，accepted coverage 证明时间区间不漏；gap/bridge、空月份 noop、frontier 重建、导出和 release gate 均有验收。`CURRENT` 只表示 last-confirmed coverage as-of，不伪装成实时同步。
- 冻结首次零成交 IBKR statement 语义：只要 flat boundary 与 coverage 均可证明，它就是 binding-effective `COMPLETED`，会建立 binding 和 acceptance；`COMPLETED_NOOP` 只用于已有 binding 下没有新增 canonical fact 的合法重复或 coverage-only confirm。ImportSession 只永久取消 hard-delete 资格，不会禁止同 binding 的后续增量。
- 为避免把来源解析、bootstrap、增量 confirm 和 correction replay 塞入同一大任务，Import 拆为 JRN-011 至 015，后续任务顺延；当前共 22 个任务（JRN-000 至 JRN-021）。在线 Broker Sync、Flex Token 存储和后台拉取仍保持关闭。
- JRN-013 退出门依赖 JRN-008，并强制复用同一 lifecycle simulation/domain rules；schema/parser/provider evidence 可提前，但 source preview 不得复制第二套会计状态机。
- 代码现实复核确认现有 `BrokerExecution.idempotency_key` 只在 RAW 层跳重，IBKR parser 仍有不可信 ID fallback，且没有 source binding/fingerprint/coverage/canonical application/reconciliation；不得把本轮计划批准写成已实现。
- JRN-001 代码预审确认 legacy `Position.exchange` 曾由 broker/`Imported` 填充，且共享 `AssetMetadata(symbol)` 无 owner；计划据此冻结 default-deny identity provenance、已有 truth 只读兼容和 system-owned shared metadata。normalized symbol 上限同步现有 PostgreSQL/legacy 列宽收敛为 50，扩宽必须先 migration 后升级合同。

2026-07-16 版曾经过独立 reviewer 复核并取得 `APPROVE`。2026-07-17 source-bound revision 及后续首次零成交 binding-effective 澄清改变了产品合同、任务编号和发布闭包，任何旧 verdict 都不自动覆盖修订后的 plan blob。修订版已随 JRN-001 稳定 checkpoint 接受两路独立只读评审；评审所绑定的 commit、获批 plan blob、finding 与最终 verdict 记录在 JRN-001 checkpoint record，避免由计划正文自证批准。

当前计划状态：`REVIEWED_APPROVE_WITH_BLOCKERS`。该状态转换只更新评审元数据，不改变已获批 plan blob 的产品语义；所有 `Beta 阻断=是` 的任务完成并取得 JRN-021 人工批准前，发布判断保持 `NOT_READY_FOR_PRODUCTION`。
