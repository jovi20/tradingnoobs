# 设计承诺未实现项审计与执行计划

审计日期：2026-07-15
审计分支：`dev`
审计基线：`b9d564d` 加当前未提交工作区
计划状态：`REVIEWED_APPROVE_WITH_BLOCKERS`
发布判断：`NOT_READY_FOR_PRODUCTION`；当前交易日志 release 只有完成 active plan `JRN-000` 至 `JRN-021` 才可进入 `INVITE_ONLY_BETA_CANDIDATE`，再经人工批准进入 `INVITE_ONLY_TRADING_JOURNAL_BETA`

执行关系：本文保留为全量审计基线和风险登记册；第 8 节的全量阶段建议已被窄化 release profile 取代，不是当前任务队列。当前交易日志范围、任务顺序和完成定义以 `docs/superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md` 为准；其中 Market Data、在线 Broker Sync、AI、PDF 和风险默认关闭，`IBKR_FLEX_XML_V1` 本地文件 adapter 属于 Import，worker 改为非权威 derived accelerator 的结果门。

## 1. 结论

项目不是“整体未实现”。P9A-P9F 工作台、基础 truth event、Timeline snapshot、Job/Outbox 骨架、P13-P18 的窄化 V1 切片均有真实代码和测试。但是，文档中的“P0-P19 已完成或收口”只代表阶段计划归档，不代表平台目标、前端 patched spec 或生产闭环已经完成。

本轮确认的关键结论：

- 生产发布仍被数据正确性、部署拓扑和 PostgreSQL 验证阻断。
- `truth-first`、`artifact-first`、`market platform`、`admin operations` 都是部分完成，当前文档对完成面的描述偏宽。
- 导入、跨币种 PnL、中文 PDF 和风险 trust metadata 存在用户可见或财务正确性问题，优先级高于继续扩展功能。
- Redis/ECharts/PostgreSQL-only/IBKR OAuth 等旧设计与当前实现发生方向变化，必须先形成 ADR，不能把所有旧方案直接转换成代码待办。
- 明确写为 future/out of scope 的 App、完整 i18n、内容平台、对象存储和券商级实时风控不进入当前发布关键路径，但保留在决策登记表中。

## 2. 审计范围与方法

覆盖范围：

- 新增本文前 `docs/` 下原有的全部 59 份 Markdown：14 份 specs、3 份当前 plans、23 份 archive、19 份指南/基线/runbook/专题文档；本文加入后共 60 份。
- 根目录、`backend/`、`frontend/` 和 generated contract 的 README。
- 当前后端 models、schemas、routers、services、Alembic revisions、tests、Docker Compose、Caddy 和启动脚本。
- 当前前端 routes、workbench components、adapters、API client、tests 和页面实际 DOM 顺序。

判定规则：

| 状态 | 含义 |
|---|---|
| `未实现` | 文档给出当前承诺或完成定义，但没有可执行代码。 |
| `部分实现` | 有模型、API、UI 或测试切片，但端到端链路、生产运行或完成定义缺失。 |
| `需复验` | 历史计划曾通过，但当前工作区已显著变化，旧证据不能证明当前状态。 |
| `待决策` | 后续文档或实际实现改变了早期设计方向，需 ADR 后再排期。 |
| `明确延期` | 文档明确写为 future/out of scope，不作为当前缺陷。 |

证据原则：

- 以当前工作区代码为实现真相，不以 archive 目录、勾选框或提交说明替代代码证据。
- “V1 完成”只证明该计划冻结的窄化范围，不自动证明上位 spec 全部完成。
- 没有真实 provider、生产快照或 PostgreSQL 环境的事项只能标记为无法验证，不能推断通过。

证据路径约定：证据使用相对仓库根目录的完整路径、下表简称，或 `docs/` 根目录文件的 basename；单独的 `:行号` 继承同一项中最近出现的路径。下文简称对应如下：

| 简称 | 完整路径 |
|---|---|
| platform spec | `docs/superpowers/specs/platform-foundation-spec-v1.1-patched.md` |
| frontend patched spec | `docs/superpowers/specs/frontend-experience-redesign-spec-v1.1-patched.md` |
| platform plan / implementation plan | `docs/superpowers/specs/platform-foundation-implementation-plan-v1.md` |
| trust contract | `docs/superpowers/specs/2026-04-13-user-trust-metadata-contract.md` |
| sequencing plan | `docs/superpowers/plans/archive/2026-04-13-platform-frontend-sequencing-plan.md` |
| legacy inventory | `docs/superpowers/plans/archive/2026-06-10-dev-p10-legacy-cutover-inventory.md` |
| P9A/P9B/P9C design | `docs/superpowers/specs/2026-06-09-p9a-frontend-workbench-design.md`、`docs/superpowers/specs/2026-06-09-p9b-dashboard-workbench-design.md`、`docs/superpowers/specs/2026-06-09-p9c-lifecycle-detail-workbench-design.md` |
| current roadmap | `docs/project-summary-and-roadmap.md` |

## 3. 最近验证证据

| 检查 | 结果 | 解释 |
|---|---|---|
| 前端 Node tests | `140 passed` | 2026-07-17 当前工作区只读复验。 |
| 前端 TypeScript | `passed` | 2026-07-17 `npx tsc --noEmit --pretty false`。 |
| 前端 ESLint | `passed` | 2026-07-17 `npm run lint`。 |
| 前端 production build | `historical passed / current not rerun` | 2026-07-15 证据曾通过；2026-07-17 为避免只读审计产生构建文件未重跑，JRN-000 checkpoint 必须重新验证。 |
| 后端 pytest | `294 passed` | 2026-07-17 使用现有 `backend/venv` 对当前工作区复验。 |
| Alembic / SQLite | `passed` | 2026-07-17 单一 head `9cad10111213`；临时空库 upgrade 与 `9cad -> 8b9 -> 9cad` round-trip 通过。 |
| 旧 QA 证据 | `superseded` | `frontend-refactor-qa-2026-07-15.md` 的 247/278-test 快照已由本节 2026-07-17 定向复验取代；仍不能替代 JRN-000 clean checkpoint。 |
| CI | `missing` | `.github/` 当前没有主应用 workflow。 |
| PostgreSQL integration/migration | `not verified` | 当前只验证了 SQLite；尚无 PostgreSQL service-container 或真实 staging 证据。 |

因此，当前前后端本地自动检查为绿；PostgreSQL migration/integration 和干净环境可复现性需在 Phase 0 重建证据，端到端浏览器行为分别进入 Phase 1 staging smoke 与 Phase 4 UI 验收。

## 4. P0：发布与数据正确性阻断项

### GAP-P0-01 导入链路不满足租户隔离、原子性和幂等

- 状态：`部分实现 / release blocker`
- 设计承诺：导入必须可重放且不产生重复交易，见 `platform-foundation-spec-v1.1-patched.md:773-778,829-831`；legacy inventory 要求导入转 truth，见 `2026-06-10-dev-p10-legacy-cutover-inventory.md:60`。
- 代码证据：`backend/routers/positions.py:1162-1180` 直接接受内部 `account_id`，没有校验账户属于当前用户；`backend/services/import_service.py:13-15` 使用无用户绑定、无 TTL 的进程内全局缓存；`:27` 一次性读完整文件而未使用 `backend/config.py:23-24` 的 10 MB 上限；`:231-248` 按行执行；`:250-332` 写 legacy 且逐行提交。
- 实际故障：`backend/services/import_service.py:289-290` 向 `Position` 传入不存在的 `entry_emotion` / `entry_confidence`；新仓位导入会在 ORM 构造时失败。解析出的 commission 在 `:198-204` 后没有进入 batch、truth event、FIFO 或 ledger。`:219-222` 把空选择当成“导入全部”；`:265-270` 查找已有仓位时漏掉 direction；孤立 EXIT 被静默跳过，但调用方仍增加成功计数。
- 同类租户边界：普通 position create/update 虽校验 account owner，却直接接受 `strategy_id`，没有校验 Strategy 属于当前用户，见 `backend/routers/positions.py:520-565,608-652`。
- 完成定义：上传 token 与 user 绑定并持久化/限时；流式或限额读取；账户使用 public_id 并做 owner 校验；所有外键输入做 owner/type 校验；确认接口支持 `Idempotency-Key`；整批单事务；直接写 truth 或原子 bridge；commission 进入统一费用口径；空选择不导入、opposite-side 不串仓、孤立行明确报错、reported count 与真实写入一致；覆盖跨用户越权、重放、部分失败回滚、进程重启、大小上限和新旧仓位测试。

### GAP-P0-02 多币种现金、FIFO、手续费与 Ledger 口径不可对账

- 状态：`部分实现 / financial correctness blocker`
- 设计承诺：PnL、fee、FX 必须中心化且保留原币与账户币口径，见 `platform-foundation-spec-v1.1-patched.md:45-55,247-276`。
- 代码证据：`backend/services/trading_accounting_service.py:92-97` 只把手续费乘 FX；`:128-146` 的 realized gross 仍是成交币金额，却直接减去已换算到账户币的 fee；`:157-166` 汇总继续混算。`backend/services/account_ledger_service.py:266-276` 又把该 net 值乘一次 FX 写到账户币。
- 其他不可对账路径：OPEN/ADD fee 进入 position `total_fees`，但 event net 固定为 0，ledger 又只同步非零 realized net，见 `backend/services/trading_accounting_service.py:99-109` 与 `backend/services/account_ledger_service.py:235-280`。任意币种资金流水直接以原数加到账户 cash，ledger 固定 FX=1，见 `backend/routers/transactions.py:58-74` 与 `backend/services/account_ledger_service.py:64-72`。
- 完成定义：每个 event 同时保留 native gross/net、fee native/account、account-currency gross/net；明确入场费进入 lot cost basis、按平仓分摊或独立 fee ledger 的唯一规则；资金流水要求 account-currency amount 或受审计 FX；ledger 只消费明确的账户币结果；建立逐事件、逐仓位和账户 ledger reconciliation invariant；覆盖 long/short、不同开平仓 FX、不同 fee currency、partial close、reversal、跨币种 deposit/withdrawal 和剩余 lot fee basis。

### GAP-P0-03 生产 Compose 未关闭运行时 `create_all`

- 状态：`未实现 / release blocker`
- 设计承诺：线上禁止依赖 `create_all()`，发布必须显式执行 migration，见 `platform-foundation-spec-v1.1-patched.md:797-810`。
- 代码证据：`backend/config.py:36-38` 默认 `ENV_NAME=development`；`backend/app_bootstrap.py:8-18` 在非 production 默认执行 `metadata.create_all()`；`docker-compose.yml:55-65` 没有设置 `ENV_NAME=production` 或 `AUTO_CREATE_SCHEMA=false`；`backend/Dockerfile:18` 直接启动 Uvicorn，没有 migration gate。
- 完成定义：生产配置弱默认值 fail-fast；独立 migration job/entrypoint 先成功再启动应用；生产强制 `AUTO_CREATE_SCHEMA=false`；PostgreSQL 空库、脱敏快照升级和失败不启动测试通过。

### GAP-P0-04 Outbox/worker 已有实现切片，但 derived 恢复闭环未验证

- 状态：`部分实现 / broader-platform blocker`；交易日志 Beta 以 active plan `JRN-016` 的结果门为准。
- 原设计承诺：核心写入后的异步刷新必须 transactional outbox，且 worker 常驻执行，见 `platform-foundation-spec-v1.1-patched.md:57-60,480-535`。当前窄化决定不让 worker 成为 canonical correctness 依赖。
- 已实现：Job/Outbox/BusinessLock、relay CLI、DB worker CLI、timeline/market handlers 和 admin jobs。
- 缺口证据：`docker-compose.yml:3-118` 没有 relay、worker 或 scheduler 服务；outbox producer 只在 `backend/routers/trading_positions.py`；新仓位、账户流水、导入、broker sync 和 AI 请求没有完整 outbox coverage。市场 warmup 会 enqueue，但没有 Compose consumer 自动执行。当前 claim 已有 CAS，PostgreSQL 使用 `FOR UPDATE SKIP LOCKED`；剩余风险是未在真实 PostgreSQL 多 worker、崩溃和重启场景完成集成验证。
- 交易日志完成定义：canonical 写入立即可读，Timeline/Lifecycle/Dashboard 在 SLA 内一致并可重建；stale derived 不覆盖新 watermark，worker 停止时可回退 canonical 或明确 degraded。若保留 relay/worker，再验证 health、graceful shutdown、coalescing、PostgreSQL 并发 claim、崩溃重放和 backlog recovery；同步/按需重建达到同一结果门时，不强制常驻 worker。

### GAP-P0-05 用户连接凭据明文存储，认证安全基线不完整

- 状态：`部分实现 / security blocker`
- 设计承诺：敏感凭据密文存储且只返回掩码；记录 auth/admin 安全事件并对高风险端点限流，见 platform spec `:659-697,736` 和 `docs/superpowers/specs/2026-04-06-platform-foundation-design.md:929-937`。
- 已有窄化实现：平台级 `IntegrationCredential.secret_ciphertext` 和 Fernet 加解密已存在，后台响应也使用 masked value；问题是多条运行路径绕过了这套机制。
- 代码证据：`backend/models.py:590-606` 的 IBKR Flex token、Binance key/secret、Finnhub key、用户 LLM key 直接存 `UserSettings` 字符串列；`backend/routers/settings.py:64-68` 直接写入。`backend/services/platform_config_service.py:24-31,72-94` 仍从普通 `PlatformSetting/SystemSetting.value` 回退读取 LLM/Finnhub secret，`backend/routers/admin.py:527-563,701-722` 会原样返回或写入这些值。仓库没有 auth event 模型/持久化写入，也没有 limiter/429 实现。
- 注册风险：`backend/routers/auth.py:30-39` 把共享邀请码硬编码为公开的 `bigme`，没有可轮换、使用次数、过期或审计语义；自助 password reset / email verify token 流程也未实现。
- 额外风险：`backend/config.py:15` 保留可工作的弱 `SECRET_KEY` 默认值；生产启动没有拒绝弱密钥。
- 完成定义：所有数据库持久化的用户级和平台级 secret 统一进入加密 credential store；运行时只允许 credential store、受管环境 secret 或外部 secret manager；迁移并清除 `UserSettings/SystemSetting/PlatformSetting` 明文与运行 fallback；普通 setting 禁止敏感 key，旧接口掩码或退役；密钥轮换方案；生产注册模式 fail-closed，invite token 哈希、可轮换、限次、过期且受审计；register/login success/fail/logout/reset/admin config 产生 immutable audit row；Auth 按 IP、AI/market/import/sync 按用户限流；弱生产 secret 启动失败。开放自助注册前必须实现 email verification 和自助 reset token 生命周期；若 V1 保持 invite-only + admin-assisted recovery，需在 ADR、UI 和 runbook 明确延期边界。

### GAP-P0-06 PostgreSQL backup 路径割裂，restore 与真实 staging 尚未验证

- 状态：`部分实现 / 未验证 / release blocker`
- 文档承认：`docs/project-summary-and-roadmap.md:53,65-70` 明确 staging 未部署；`docs/admin-operations-runbook.md:120-123` 明确 P17 应用内 PostgreSQL backup provider 未提供。
- 已有与缺口：`docker-compose.yml:97-117` 已配置 `postgres-backup-local` 定时备份和 retention；但 `backend/services/backup_service.py:49-55` 的 Admin/P17 路径对 PostgreSQL 固定抛 `BackupProviderNotConfigured`。两条路径未集成，当前同机目录也没有加密、异地复制、restore drill 或可观测证据。
- 完成定义：决定复用或替换现有 Compose provider，禁止长期保留两套互不相知的备份体系；Admin API 要么接入同一 provider，要么明确退役；确定加密/异地存储、保留周期、完整性检查、告警和 restore 命令；对生产相近 PostgreSQL 做 backup -> migrate -> restore drill；验证 Caddy、真实 provider、worker、outbox、登录、Timeline、Dashboard、Import、Insights、Admin；保存时间戳和结果证据。

### GAP-P0-07 主应用 CI、依赖锁和 PostgreSQL gate 缺失

- 状态：`部分实现 / release blocker`
- 文档承认：`project-summary-and-roadmap.md:54,62`、`project-structure-review.md:18`。
- 当前证据：现有 `backend/venv` 可运行，当前 278 个后端测试通过；但它是被忽略的本机状态，`requirements.txt` 使用宽泛下限而没有 lock，Python/Node 版本未由工具文件统一固定，`.github/` 无主应用 workflow，旧 P19/QA 证据也无法覆盖当前未提交迁移和代码。
- 完成定义：锁定 Python/Node 版本与依赖；在干净环境可重建；CI 执行后端 unit/integration、Alembic、前端 test/type/lint/build、OpenAPI drift、静态 secret/legacy boundary 检查；至少一条 PostgreSQL service-container 流水线；本地一条命令复现同一 gate。

### GAP-P0-08 中文周报 PDF 会丢失正文

- 状态：`部分实现 / broader advertised feature blocker`；active trading-journal Beta disposition：`DEFERRED_BY_SCOPE`。
- 文档声明：P14/P19 把周报 PDF 作为已完成发布范围；`report-export.md:34-45` 面向实际周报内容。
- 代码证据：`backend/services/report_export_service.py:18-19` 使用 Helvetica；`:169-170` 强制 Latin-1 并以 `?` 替换中文。测试 `backend/tests/test_report_export_service.py:9-39` 只使用英文正文。
- 完成定义：嵌入可分发 CJK 字体；中文标题、正文、分页和换行正确；通过 PDF 文本提取和页面渲染两类断言；在真实中文周报上做浏览器下载 smoke。

### GAP-P0-09 风险摘要的来源与 freshness 声明不真实

- 状态：`部分实现 / broader user trust blocker`；active trading-journal Beta disposition：`DEFERRED_BY_SCOPE`。
- 文档声明：P13 V1 已完成；trust contract 要求 source/freshness 与实际来源一致。
- 代码证据：`backend/services/risk_alert_service.py:81-95` 读取 legacy `DailySnapshot`；`:151-174` 用开仓均价而非当前 mark 计算 exposure；`:132-147` 却固定 `base_currency=USD`、`freshness=FRESH` 并声明 `AccountLedgerEntry` 来源；`:177-190` 的日损算法完全忽略 net transfers。`backend/routers/dashboard.py:545-575` 又将 `net_transfers` 固定写 0；测试 `backend/tests/test_risk_alert_service.py:192-205` 把“无数据仍 FRESH”固化为预期。
- 完成定义：current mark + FX 后计算集中度；日损剔除入出金；行情 stale 时返回 `DATA_STALE/DEGRADED`；source refs 与真实查询一致；覆盖多币种、无快照、入金日和 provider 失败。

### GAP-P0-10 现金流水可物理删除，破坏账本审计与重放

- 状态：`未实现 / financial audit blocker`
- 设计承诺：历史修正优先追加 adjustment/reversal，不静默改旧记录，见 platform spec `:55,117`；truth/ledger 必须可审计和可重放。
- 代码证据：`backend/routers/transactions.py:101-122` 回退余额后物理删除 transaction；`backend/services/account_ledger_service.py:284-287` 同时物理删除 ledger row，没有 compensating entry、actor、reason 或 request id。
- 完成定义：production profile 先禁用硬 DELETE；定义 void/reversal/compensating entry API 和权限；原 transaction/ledger immutable，追加 actor、reason、request id 与关联源；重复请求幂等；任意时点由 ledger replay 得到一致余额；覆盖 deposit、withdrawal、fee、transfer 和跨币种修正。

## 5. P1：平台与产品主链缺口

### GAP-P1-01 Truth hard cutover 仍是 create-and-sync bridge

- 状态：`部分实现 / active trading-journal blocker`；由 JRN-007/008 收敛。
- 文档证据：current roadmap `:50,72-82` 和 legacy inventory `:54-79` 明确 legacy 仍在；archive sequencing plan `:91,138,144,164` 仍未勾选。
- 代码证据：`backend/routers/positions.py:513-585` 先提交 `Position/TradeBatch`，再调用 `sync_legacy_position_to_truth`；后者 `legacy_truth_sync_service.py:276-328` 再次自行提交，失败不原子。Dashboard、Import、Transaction、Analytics、LLM、AssetMetadata、DailySnapshot 和前端 raw DTO 仍消费 legacy。
- 完成定义：truth-native create/list/import/cash commands；Dashboard/Analytics/LLM 改读 truth/ledger/derived；legacy mutation 移到 admin/migration namespace；经过一个 staging rollback window 后删除 mixed feed 和 allowlist 项。

### GAP-P1-02 历史修正、archive/void 与 non-latest compensation 仍缺语义

- 状态：`部分实现 / 待产品决策`
- 文档证据：legacy inventory `:71-87` 明确 OPEN archive/void 和 non-latest reversal 未定。
- 代码证据：truth 只允许最新 ADD/REDUCE/CLOSE reversal；OPEN void/archive 与 non-latest compensation 没有命令、权限和用户交互。现金硬删除已提升为独立发布阻断项 GAP-P0-10。
- 完成定义：冻结 archive/void/non-latest compensating event 权限与 UX；任何历史修正追加事件而非抹除；数量、PnL、fees、ledger、derived 全量可重放；保留 actor、reason、request id。

### GAP-P1-03 Broker RAW execution 尚未进入 truth/reconcile 流程

- 状态：`部分实现`；active trading-journal Beta disposition：IBKR Flex 文件 adapter 子集由 `JRN-013/014/015` 纳入，在线 Broker Sync 仍为 `DEFERRED_BY_SCOPE`。
- 设计证据：`trade-record-sync-design.md` 的 Release Scope、Execution Identity、Preview And Confirm 与 Deferred Network Sync。
- 已实现：Flex/Binance 拉取、RAW `BrokerExecution` 持久化、execution 级幂等、连接测试、手动同步、近期 run/execution UI。
- 缺口：没有 broker connection/external account 到 `TradingAccount` 的稳定映射；手动 sync 无请求幂等或 business lock；在 HTTP 请求内同步执行；没有确认、冲突分类、RAW -> OPEN/ADD/REDUCE/CLOSE/ledger 的原子 writer；产品入口集中在 Settings 而非账户/运维工作流。
- 当前 release 文件子集完成定义：只接收 `IBKR_FLEX_XML_V1` 本地文件；建立 owner/account/source binding、稳定 execution/source-event identity、immutable SourceStatement/observation/sighting、source fingerprint、versioned application、accepted tombstone 和 reconciliation case episode；重叠文件分类 NEW/ALREADY_IMPORTED/KNOWN_HISTORICAL_OBSERVATION/STALE_SOURCE_OBSERVATION/conflict/late/sequence-gap/correction/cancel-bust/TARGET_UNRESOLVED，旧 statement 重传不重复记账、新 generation sighting 不丢失、严格更早的旧 payload 不误冻账户、较新来源回改进入冲突且可由 versioned replay 或更晚权威 observation 收口。source confirm 不允许逐行排除，必须以 baseline-aware preview digest 全量消费 pending NEW；`source_completeness = PENDING_IMPORT` 时可信指标降级，full confirm 后才恢复 CURRENT。普通确认与 truth/ledger 单事务，correction 以 compensating replay 保留 lineage。现有 `BrokerExecution.idempotency_key` 只完成 RAW 层跳重，不能作为该文件子集已实现的证据。在线子集未来仍需：受管凭据、同连接 active sync lock、请求重放、失败恢复和拉取调度；不能因文件 adapter 完成而标记整个 GAP-P1-03 closed。
- 2026-07-17 增量合同澄清：首次可信 bootstrap 后，IBKR 同一 external account 绑定同一内部账户，长期接受完全重复、窗口重叠或纯增量 statement，不要求每月新建账户；稳定 identity 只应用 `NEW`，旧版本/correction/cancel-bust 进入历史 no-op 或 reconciliation。statement `fromDate/toDate` 还必须形成连续 accepted coverage；断档返回 `SOURCE_COVERAGE_GAP`，空 statement 可证明无交易月份并推进 coverage。immutable `StatementCoverageAcceptance` 区分“仅 preview/conflict 已观察”与“已由 full confirm/noop 接受”的 statement，并用于重建 frontier；coverage watermark 与 execution unique identity 分别证明“区间未漏”和“事实未重”，任何一项都不能替代另一项。

### GAP-P1-04 API version、public_id、Trust envelope 和 generated types 未统一

- 状态：`部分实现`
- 设计证据：trust contract `:23-30,124-215`；platform spec `:750-779`。
- 代码证据：只有 insight artifacts 使用 `/api/v1`；大量普通用户响应仍暴露 `id/user_id/account_id`；`frontend/lib/generated/contracts.ts:1-2` 是空 placeholder；`frontend/lib/api.ts` 已 1544 行。
- 合同漂移：trust contract 冻结 freshness 为 `FRESH/DELAYED/STALE/DEGRADED`，market 使用 `CACHED/UNAVAILABLE`；部分前端 adapter 自造 `LOCAL_*` source。Dashboard 根响应没有统一 `meta`。
- 完成定义：冻结 v1 OpenAPI；生成 TypeScript 并在 CI 做 drift check；新接口只用 public_id；旧路径有兼容/弃用窗口；根/module/item trust 共用同一枚举或通过正式版本扩展；逐项缩小 legacy DTO allowlist。

### GAP-P1-05 Dashboard/analytics 仍在请求内做 legacy 聚合和写入

- 状态：`部分实现`
- 设计证据：platform plan `:570-625`、legacy inventory `:57,75,78`。
- 代码证据：`backend/routers/dashboard.py` 仍直接查询 `Position/TradeBatch/DailySnapshot`、调用行情、拼 Sankey，并在 GET 请求内更新账户和写 `DailySnapshot`（约 `:461-583`）。`DashboardStats` 没有 page-level trust envelope。
- 完成定义：建立 `portfolio_snapshots/dashboard_cache/position_metrics/chart_materializations/risk_views` 或等价 read models；由 truth/ledger/market outbox 刷新；GET 只读；重建命令、freshness SLA 和 source refs 可审计。

### GAP-P1-06 异步可靠性覆盖面与终态不完整

- 状态：`部分实现`
- 设计证据：platform spec `:482-535,771-779`。
- 缺口：outbox 未覆盖 dashboard refresh、market warmup、broker reconcile、AI 请求；import/manual sync 未接 request idempotency；用户侧看不到自己触发的 job progress；没有统一 `DEAD`/dead-letter 语义；队列积压和 handler coverage 没有启动时校验。
- 完成定义：列出所有 critical mutation matrix；每项明确 transaction/outbox/idempotency/lock/handler/replay；后台与用户侧展示可理解状态；dead-letter 和 replay 受审计。

### GAP-P1-07 市场数据持久化已起步，但自动平台未闭环

- 状态：`部分实现 / 不是 P16 窄化 V1 回归`；active trading-journal Beta disposition：`DEFERRED_BY_SCOPE`。
- 已实现：当前工作区新增 provider mapping、latest quote、daily bars、watermark、repository、quote/daily jobs、YFinance adapter 和首次 quote 后 daily warmup enqueue。
- 缺口：没有部署 worker；`enqueue_quote_refresh` 没有产品调用；无周期刷新；无 intraday active tracking；进程内 cache 重启丢失；无持久化 provider health/circuit breaker/admin health；`market_data_sources.md` 尚未同步新实现。
- 完成定义：新开放仓位自动 warmup；周期 quote refresh；仅开放仓位采分钟线；provider 连续失败熔断和降级；重启继续消费；admin 可查看 coverage/freshness/provider/job health。

### GAP-P1-08 AI artifact-first 只覆盖部分 analysis bridge

- 状态：`部分实现`；active trading-journal Beta disposition：`DEFERRED_BY_SCOPE`。
- 设计证据：platform spec `:587-625`、implementation plan `:631-688`。
- 代码证据：prompt 仍硬编码在 `backend/services/llm_service.py`；`InsightRun` 只有基础状态和 prompt 字符串，缺 provider/model/token/cost/latency/cache/schema version；AI 在请求内同步执行，成功后才补 run；周报和部分 summary 仍是 legacy 表/markdown。
- 完成定义：请求先创建 QUEUED run；provider 失败也保留 FAILED run；weekly/summary/analyze/position review 全部产出 artifact；prompt 可版本发布/回滚；usage/cost/latency/cache 可查询；上下文来自 truth-derived read models。

### GAP-P1-09 Timeline item-level trust 没有真正显示

- 状态：`P9 验收回归`
- 设计证据：P9A design `:42-50` 和 trust contract `:237-244` 要求事件卡显示 source/freshness/maturity。
- 代码证据：类型和 adapter 保留 trust，但 `frontend/components/timeline/workbench/TimelineEventCardV2.tsx:20-99` 与 `ReviewInboxPanel.tsx:15-56` 完全不消费。
- 完成定义：event/inbox 显示一致的 source、freshness、value status 和 maturity；stale/degraded 不能只靠颜色；用组件测试和浏览器截图验证。

### GAP-P1-10 Dashboard 错误态不可达

- 状态：`P9 验收回归`
- 设计证据：P9B design `:42-44,186-204`。
- 代码证据：`frontend/app/(product)/dashboard/page.tsx:45` 在 `stats` 缺失时先返回 `null`，`:49-52` 的 error callout 无法显示。
- 完成定义：总览、历史或仓位任一请求失败都有明确 partial/error state；页面不空白；组件测试覆盖 `stats=null + error`。

### GAP-P1-11 Lifecycle 和 Dashboard 的移动排序 helper 未控制真实 DOM

- 状态：`P9 验收回归`
- 设计证据：P9C `:83-96` 要求 hero -> action -> event -> AI/evidence -> cash -> legacy；P9B `:78-92` 要求 primary positions 早于 secondary evidence。
- 代码证据：`LifecycleWorkbench.tsx:65-91` 实际先 evidence 后 event/AI；`DashboardEvidenceStack.tsx:21-50` 实际先 Sankey、MAE/MFE 后 positions。pure helper 测试没有约束组件 DOM。
- 完成定义：DOM 顺序与冻结设计一致；390px 键盘/读屏顺序正确；用 Testing Library/Playwright 对真实组件而非 helper 断言。

### GAP-P1-12 移动端 4+1、Rules & Checklist、交易分组和 Admin route family 未完成

- 状态：`patched spec 未实施`
- 设计证据：frontend patched spec `:134-176,369-392,622-649,673-708`。
- 代码证据：`MobileBottomNav.tsx:28-57` 横向输出所有产品/设置入口，没有中央快速记录；`navigation.ts:11-25` 仍叫“策略”；Strategies 只做 CRUD，没有命中率/miss/表现/AI 健康度；Positions 仍 flat map legacy records，没有资产 -> 账户 -> instrument 分组；`AdminShell.tsx:12-15` 只有 ops/jobs，没有独立 platform/users/market-data/ai health 页面。
- 完成定义：按产品决策实现或正式修改 patched spec；移动端 4+1 与 quick capture；Rules & Checklist 分析；truth read-model 交易分组；admin provider/data/job/AI health；桌面/390px 浏览器验收。

### GAP-P1-13 Insights 档案能力和卡片协议仍不完整

- 状态：`部分实现`；active trading-journal Beta disposition：`DEFERRED_BY_SCOPE`。
- 设计证据：frontend patched spec `:396-429`。
- 已实现：周报、日期范围分析、近期分析、artifact detail、evidence/source refs、PDF。
- 缺口：缺稳定筛选/归档；部分周报仍展示 legacy markdown；AI card 没有统一 confidence/coverage/recommended action/deep-link contract；周报没有完整 artifact 路径。
- 完成定义：artifact archive/filter/query；所有新 AI 输出遵守 card contract；legacy markdown 只读迁移完成后移除；evidence deep link 可回跳到具体交易/账户/时间范围。

### GAP-P1-14 1000 用户与目标 VPS 容量没有运行证据

- 状态：`未验证 / production capacity blocker`
- 设计承诺：平台设计以 ARM 4 CPU / 24 GB、约 1000 用户为容量目标；worker、read model 和 provider 降级必须在这一资源边界内可运行。
- 当前证据：仓库没有 load profile、SLO、连接池预算、worker throughput 或 backlog recovery 基线；真实 VPS 资源容量仍未知。
- 完成定义：冻结代表性读写比例与数据量；记录 API p50/p95/p99、错误率、DB 连接/慢查询、relay/worker throughput、积压恢复时间、provider 限流与进程内存峰值；定义过载降级和告警阈值；在生产相近 PostgreSQL 与 VPS 规格上验证，结果关联到 commit/config。未达到 1000 用户时必须收窄公开容量承诺，而不是推断通过。

## 6. P2：结构、治理与增强项

| ID | 状态 | 未完成项 | 证据与完成边界 |
|---|---|---|---|
| GAP-P2-01 | `待决策` | 七域 PostgreSQL schema 与 expand/migrate/contract 模板 | sequencing plan `:63-75` 明确未完成；当前所有表仍在默认 schema。先 ADR 判断收益和迁移成本，再单独执行，禁止与 truth cutover 混做。 |
| GAP-P2-02 | `未实现` | `backend/models.py` 模块化 | current TODO `:23` 和 model plan `:14-63`；当前文件 1249 行。只做移动/re-export，放在语义迁移稳定之后。 |
| GAP-P2-03 | `部分实现` | 完整 observability | 目前主要是 request id/latency/error helper；缺 request completion logs、未捕获异常统一 envelope、DB/worker/outbox/provider metrics、慢查询和告警。 |
| GAP-P2-04 | `未来规划` | 风险与绩效指标 | `trading-fields-design.md:90-179`、`trading-metrics.md:252-345`：risk/trade、portfolio heat、VaR、correlation、profit factor、commission ratio、margin、配置与 alert log。P13 V1 不等于这些已完成。 |
| GAP-P2-05 | `明确增强` | PDF/报告增强 | `report-export.md:97-103`：图表、主题、statement、邮件/定时/批量；先修 P0 中文正确性，再决定产品优先级。 |
| GAP-P2-06 | `部分实现` | 页面与模型热点拆分 | `settings/page.tsx` 1230 行、`admin/ops/page.tsx` 1256 行、position detail 1176 行、`api.ts` 1544 行、`schemas.py` 1321 行；按 ownership 拆分，不能只搬 JSX。 |
| GAP-P2-07 | `未实现` | 文档状态治理 | archive README 的“完成/收口”与 sequencing 未勾选项冲突；market、metrics、QA、trade sync 索引滞后。建立 design status/ADR/superseded 标记和代码证据链接。 |
| GAP-P2-08 | `未实现 / 待产品决策` | 公司行为事件与批量修正 | platform spec 把 `stock_split`、`symbol_change`、`delisting` 列入 V1，并要求产生可审计事件或 correction run；当前除部分枚举/字段外，没有 writer、重放、批量修正、行情映射或 UX。进入股票生产范围前必须实现；否则通过 spec amendment 明确延期和手工运维边界。 |

## 7. 设计分歧与明确延期

这些事项不能直接进入实现队列，必须先做书面决策：

| 决策 | 旧设计 | 当前实现 | 本计划建议 |
|---|---|---|---|
| Worker | Redis + worker 冻结 | PostgreSQL JobRun + DB worker CLI | 交易日志仅把 DB worker 作为非权威 accelerator；先证明 freshness、canonical fallback 和恢复结果。确有吞吐收益才常驻部署，只有 DB worker 不满足已测 SLA 才评估 Redis。 |
| 图表 renderer | ECharts | 内部 SVG renderer + `chart.v1` | 接受内部 SVG 为当前决策，更新旧 spec 为 superseded；不做无收益迁回 ECharts。 |
| 开发数据库 | dev/prod PostgreSQL-only | 本地默认 SQLite，部署 PostgreSQL | 允许 SQLite 快速开发；CI/staging/production 强制 PostgreSQL，关键 migration/locking 测试只以 PostgreSQL 结论为准。 |
| IBKR | Web API/OAuth 半自动同步 | `IBKR_FLEX_XML_V1` 本地文件 bootstrap/增量/correction；网络 Flex/OAuth/TWS/Gateway 关闭 | 文件 adapter 进入 JRN-013/014/015；在线连接器仅在受管凭据、sync lock 和 provider 验收完成后重开。 |
| 七域 schema | 架构冻结 | 默认 schema 单体 | 延后到 truth/legacy 收敛之后做收益评审；没有明确运维/权限收益则可正式取消。 |
| 注册与恢复 | open/invite_only/approval_required/closed，可选邮箱验证与自助 reset | 公开硬编码共享邀请码 + admin-assisted password reset | V1 建议先固定为 invite-only：邀请码哈希、限次、过期、轮换、审计；开放注册前补 email verification 与 self-service reset。用 ADR 明确产品边界。 |

明确延期，不进入当前 release blocker：

- App 客户端。
- 完整 i18n 翻译平台。
- content/news/SEC ingestion 平台。
- S3/object storage（除非截图、原始文件或报告保留需求先触发）。
- SSO/第三方登录、复杂套餐计费。
- 股票期权完整生命周期、券商级实时风控、WebSocket 实时推送。

## 8. 历史全量分阶段建议（非当前任务队列）

本节保留 2026-07-15 全量审计时的排序证据。当前 release 已主动延期 Market/在线 Broker Sync/AI/PDF/风险，并由 active trading-journal plan 的 JRN-000 至 JRN-021 取代以下执行顺序；IBKR Flex 本地文件增量导入是 Import 的窄化子集。

### Phase 0：冻结基线与架构决策

目标：先让“当前实现是什么、如何重复验证”变成事实。

任务：

1. 对现有大规模 dirty worktree 建立变更清单，分离用户改动、生成文件、运行产物和本计划文档。
2. 固定 Python/Node 版本和依赖 lock；在不复用 `backend/venv` 的干净环境重建依赖，并重跑全量后端、Alembic、前端 test/type/lint/build。
3. 先建立最小 mandatory CI：与本地同命令执行当前 baseline，保存 commit、依赖版本、测试数和 artifact。
4. 新增 PostgreSQL service-container/integration profile；在空库上跑 `upgrade head`，把 migration chain 纳入 CI。
5. 为 DB worker/Redis、SVG/ECharts、SQLite/PostgreSQL dev、IBKR Flex/OAuth、七域 schema、注册/恢复模式写 ADR。
6. 更新文档索引和状态语言：`implemented slice`、`partial`、`superseded`、`future`、`verified at commit`。

退出门：

- 当前 commit/diff 范围固定。
- mandatory CI 已运行，且本地和 CI 使用同一组命令。
- 后端/前端/Alembic/PostgreSQL 空库基线可从干净环境重跑。
- 六个架构/产品分歧均有明确决定，不再同时保留互斥“冻结项”。
- 达到 `READY_TO_DEPLOY_STAGING`；它只允许部署隔离的非生产环境，不代表功能或数据安全已通过。

### Phase 1：数据正确性与 staging 安全

顺序：

1. 修 GAP-P0-01 导入租户隔离、无效字段、事务、幂等和 commission。
2. 修 GAP-P0-02 多币种 cash/PnL/fee/ledger reconciliation。
3. 修 GAP-P0-10 现金 hard delete，改为受审计 reversal/void。
4. 修 GAP-P0-09 风险 source/freshness、net transfer 和 current mark。
5. 修 GAP-P0-08 中文 PDF 与中文回归。
6. 修 GAP-P0-03 生产配置/migration gate/weak secret fail-fast。
7. 完成 GAP-P0-05 用户/平台凭据治理、注册安全、auth audit 和最小限流。
8. 部署 GAP-P0-04 relay/worker/scheduler 与 healthcheck，并验证 PostgreSQL 并发 claim。
9. 全程把新增回归、负向测试、secret scan 和 PostgreSQL integration 同步加入 GAP-P0-07 CI。
10. 完成 GAP-P0-06 单一 backup provider、restore drill 和真实 staging evidence。

退出门：

- GAP-P0-01 至 GAP-P0-10 全部有自动化测试和负向测试。
- PostgreSQL staging 完成 backup -> migrate -> smoke -> restore drill。
- 仅 `docker compose up` 能跑完整 API/relay/worker 闭环。
- 达到 `STAGING_VERIFIED`；不得把它写成 production ready 或 production candidate。

### Phase 2：Truth、Ledger、Import 与 Sync 收敛

任务：

1. 实现 truth-native position create，消除双 commit create-and-sync。
2. 实现 truth-native import，或一个明确且原子的 legacy-to-truth migration mode。
3. 实现 ledger-native deposit/withdrawal/fee/transfer 命令；删除改为 reversal/void。
4. 冻结 archive/void/non-latest compensation 事件语义并实现审计 UX。
5. 建 broker connection、external account mapping、sync lock/idempotency、RAW confirm/conflict/truth writer。
6. 扩 outbox matrix 到 create/import/sync/cash/AI/market warmup。
7. 逐项迁移 Dashboard、Analytics、LLM、AssetMetadata、DailySnapshot 和前端 raw DTO；每删除一项都保留 rollback 证据。

退出门：

- 普通用户主路径不写 `Position/TradeBatch/Transaction`。
- 任意 truth aggregate 可由事件和 ledger 重建。
- Import/Sync 重放不重复，失败不产生半成品。
- legacy mixed feed/headers/DTO allowlist 只剩明确 admin migration 项。

### Phase 3：契约、Read Model 与市场平台

任务：

1. 冻结 `/api/v1` 和弃用策略；普通用户新契约 public_id-only。
2. 从 OpenAPI 生成 TypeScript，CI 检测 drift；按页面迁出 `api.ts` 手写 DTO。
3. 统一 Trust envelope 和 freshness/source 枚举；修 Timeline item-level trust。
4. 把 Dashboard、risk、position metrics 和 chart materialization 移到 derived read models。
5. 完成 market periodic refresh、warmup、intraday active tracking、provider health/circuit breaker 和 admin health。
6. 补用户可见 job progress、dead-letter/replay 和 backlog health。
7. 完成 GAP-P2-03 的 release-scope observability：request completion/unhandled exception、DB/worker/outbox/provider metrics、慢查询、backlog 和告警。
8. 执行 GAP-P1-14 容量基线：API 延迟/错误率、DB pool、worker throughput、backlog recovery、provider 限流与内存峰值。

退出门：

- Dashboard/Timeline/Lifecycle/Insights 新接口均通过 schema snapshot 与 generated type 编译。
- GET read model 不产生业务写入。
- 断开 provider 后能读取带真实 degraded/stale metadata 的 last-known data。
- worker 重启后继续处理，不丢 job、不重复写。
- 在目标 VPS/PostgreSQL 规格上达到已冻结的容量/SLO；未达标时同步收窄容量承诺。

### Phase 4：前端产品承诺与 AI 平台

任务：

1. 修 Dashboard 空白错误态、Lifecycle/Dashboard 实际 DOM 排序和 position detail shell。
2. 实现或正式修改移动 4+1、quick capture、context drawer 冻结项。
3. 完成 Rules & Checklist 分析、truth 交易三层分组、Insights filter/archive/card contract。
4. 完成 admin platform/users/market-data/AI health 信息架构；继续保留 ops/jobs 窄化工作台。
5. 建 AI prompt registry/versioning、workflow state machine、usage/cost/latency/cache；所有新结果 artifact-first。
6. 引入 Testing Library + Playwright + axe，测试真实 DOM、键盘、读屏顺序和 desktop/390px 响应式。

退出门：

- patched frontend spec 中仍有效的冻结项逐项有浏览器证据，或已通过 ADR/spec amendment 取消。
- helper 测试不再替代组件 DOM 和交互测试。
- AI provider 失败也留下可审计 run；weekly/summary/analyze 结果均可回跳证据。

### Phase 5：结构债与未来产品项

任务：

1. 语义迁移稳定后按现有 plan 拆分 `backend/models.py`，保持 re-export 和 metadata 一致。
2. 再评估七域 schema；如执行，使用 expand -> backfill -> switch -> contract 独立计划。
3. 拆分巨型 settings/admin/position/API/schema 文件，按领域 ownership 而非行数机械拆分。
4. 按用户价值选择 risk/metrics、PDF 图表/主题、定时报告等 P2 增强。
5. 对 GAP-P2-08 公司行为做实现或 spec amendment；进入股票生产范围前不得保持未决。
6. 为 App/i18n/content/object storage/options/SSO，以及开放注册触发的 email verification/self-service reset 设置明确触发条件，不提前建设空平台。

## 9. 历史发布状态门（HISTORICAL_SUPERSEDED）

本节是 2026-07-15 面向“全量平台同时发布”形成的旧状态模型，保留作审计证据，不再约束当前交易日志 Beta。当前状态转换只以 active plan 的 `NOT_READY_FOR_PRODUCTION -> INVITE_ONLY_BETA_CANDIDATE -> INVITE_ONLY_TRADING_JOURNAL_BETA` 为准。

| 状态 | 必要条件 | 明确不代表 |
|---|---|---|
| `READY_TO_DEPLOY_STAGING` | Phase 0 完成；干净环境、本地/CI、PostgreSQL 空库 migration 基线通过；部署目标隔离且不接生产用户数据。 | 不代表 P0 数据正确性、安全或功能闭环完成。 |
| `STAGING_VERIFIED` | Phase 1 完成；GAP-P0-01 至 GAP-P0-10 关闭；真实 staging 完成 provider、worker、backup/restore 和全链路 smoke。 | 不代表容量达标，也不自动授权生产发布。 |
| `PRODUCTION_CANDIDATE` | `STAGING_VERIFIED` 持续为绿；GAP-P1-14 容量/SLO 通过；所有 release-scope P1/P2 有关闭证据或书面 scope acceptance；GAP-P2-08 已实现或完成 spec amendment；rollback、监控、值班与 ADR 完整。 | 不等于已发布；仍需人工 release approval 和变更窗口。 |

任何文档不得再用含混的 `READY_FOR_STAGING_ONLY` 同时表达上述三个状态。

## 10. 历史全量验收矩阵（HISTORICAL_SUPERSEDED）

下表包含当前已明确延期的在线 Broker Sync、Market、AI、PDF 和风险能力，不是 JRN-021 的验收清单。当前必测矩阵见 active plan 第 6、8 节。

| 层级 | 必须通过 |
|---|---|
| Backend unit | accounting、import、truth lifecycle、ledger reconciliation、sync conflict/idempotency、risk、PDF CJK、job/outbox。 |
| Backend integration | PostgreSQL auth、create/import/sync -> outbox -> worker -> derived、AI provider failure、backup/restore。 |
| Migration | PostgreSQL 空库、脱敏生产快照、支持窗口 downgrade、失败不启动应用。 |
| Contract | OpenAPI snapshot、generated TS drift、public_id-only、Trust enum/envelope。 |
| Frontend | Node tests、TypeScript、ESLint、production build、component DOM tests。 |
| Browser | 登录、Timeline、Dashboard error/empty/data、truth create/edit/reversal、import、sync conflict、Insights/PDF、admin health；1440x900 与 390x844。 |
| Ops | worker/relay health、outbox backlog、provider degraded、backup/restore、rollback flags。 |
| Capacity | 目标 VPS/PostgreSQL 上的 API p95/p99、错误率、DB pool/慢查询、worker throughput、backlog recovery、provider 限流和内存峰值。 |

任何阶段不得用“文件存在”“路由存在”“归档勾选”替代对应验收门。

## 11. 2026-07-15 全量计划评审（HISTORICAL_SUPERSEDED）

### 评审方式

初稿经过四路检查：全量文档状态审计、后端实现审计、前端实现审计，以及主线对代码证据、测试结果和跨模块依赖的复核。定稿前又增加三路独立只读评审：一组抽查 P0/P1 代码证据，一组检查遗漏、优先级和验收可执行性，一组检查索引、文档数与引用。独立计划评审首轮结论为 `CHANGES_REQUIRED`，以下纠正已进入本版并完成二次复审。

### 评审发现

1. `P0 / 基线纠正`：初稿误判本机没有可用后端环境。复审发现 `backend/venv`，主线重新执行并确认 278 tests passed；当前阻断已收窄为依赖锁、干净环境、CI 和 PostgreSQL gate。
2. `P0 / 财务与租户边界`：在原导入越权/故障和 FIFO FX 混算之外，复审补出 strategy owner、空选择、opposite-side、孤立行计数、上传上限、跨币种现金、开仓 fee ledger 和现金硬删除。计划已扩充 GAP-P0-01/02，并把硬删除提升为 GAP-P0-10。
3. `P0 / 安全范围`：初稿只覆盖 per-user 明文凭据。复审确认平台级 encrypted credential 已存在，同时发现 UserSettings 与 SystemSetting/PlatformSetting fallback 绕过机制、Admin raw value、硬编码邀请码及缺失注册/恢复边界；GAP-P0-05 已改为统一治理且承认已有窄化实现。
4. `P0 / 备份事实纠正`：Compose 已有定时 PostgreSQL backup 容器，不能写成“完全未实现”。GAP-P0-06 已收窄为应用路径割裂、同机未加密、无 restore/staging 证据，并要求只保留一套正式 provider。
5. `P1 / 顺序纠正`：Phase 0 原要求 CI 同命令，却把 CI 建设排在 Phase 1。最小 mandatory CI 和 PostgreSQL 空库 gate 已移到 Phase 0，发布状态拆成 `READY_TO_DEPLOY_STAGING`、`STAGING_VERIFIED`、`PRODUCTION_CANDIDATE`。
6. `P1 / 验收补齐`：补入 1000 用户/目标 VPS 的容量基线、worker 并发 claim、backlog recovery 与 SLO；P9 helper 测试不得替代真实 DOM、浏览器和可访问性证据。
7. `P1 / 结构顺序`：不能在 legacy 语义仍变化时先拆 `models.py` 或迁七域 schema。纯结构拆分移到 Phase 5，schema 改造只允许 ADR 后单独执行。
8. `P2 / 范围控制`：P12-P18 的窄化 V1 有真实成果，不写成“全部失败”；ECharts、Redis、IBKR OAuth、多 schema 不机械实施；公司行为补入待决策项，future 平台保留明确延期。

### 评审结论

当时的全量计划评审结论：`APPROVE_WITH_BLOCKERS`。该结论说明全量 gap registry 的证据质量，不再定义当前 release scope 或 Beta 发布门。

以下是当时面向全量平台候选的条件，仅作为未来扩展风险清单，不是当前交易日志 Beta blocker：

- GAP-P0-01 至 GAP-P0-10 全部关闭。
- 当前 278-test 后端基线持续通过，且干净环境与 PostgreSQL integration gate 可复现。
- Compose 常驻 worker/relay、backup/restore 和真实 staging smoke 有新证据。
- GAP-P1-14 容量/SLO 达标，所有 release-scope P1 有关闭或书面 scope acceptance。
- release-scope P2 有关闭或书面 scope acceptance，GAP-P2-08 已实现或完成 spec amendment。
- 所有架构/产品分歧均通过 ADR 选择唯一方向。

历史残余不确定性：真实 provider 行为、生产数据分布、历史 legacy 数据量、VPS 资源容量和用户对 archive/void、移动导航、IBKR 实时性的产品选择。其中在线 provider/IBKR 拉取已延期，IBKR Flex 文件合同由 JRN-013/014/015 验证；当前范围内的存量数据、archive/void 和容量问题由 JRN-005、JRN-010、JRN-021 消除。

## 12. 文档维护动作

执行本计划时同步完成：

1. `[已完成]` 将本文加入 `docs/README.md` 推荐阅读与当前计划索引，并同步发布状态措辞。
2. 将 `project-summary-and-roadmap.md` 的 P0-P19 表述改为“阶段切片已收口”，避免理解成目标架构完成。
3. 给旧 platform implementation plan 和 sequencing plan 加 `superseded/partial` 状态头。
4. 更新 `market_data_sources.md`、`trading-metrics.md`、QA Alembic head 和 trade sync 索引。
5. 每个 gap 只在代码、测试、运行证据和文档四项齐全后标记关闭。
