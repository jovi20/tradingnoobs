# Trade Record Source Import Design

更新时间：2026-07-17
状态：`ACTIVE_FILE_IMPORT_CONTRACT / NETWORK_SYNC_DEFERRED`

本文只定义交易记录来源文件导入，不包含行情价格、K 线、IBKR Web Service 主动拉取或 Binance API 同步。权威实施顺序见 [Trading Journal Launch-Safe Development Plan](./superpowers/plans/2026-07-16-dev-trading-journal-development-plan.md)。

## Release Scope

Beta 启用两种互斥的账户交易来源模式：

```text
CLEAN --首次手工交易或通用 CSV/Excel 非 noop confirm--> MANUAL
CLEAN --首次 IBKR Flex 文件非 noop confirm--> SOURCE_BOUND(binding)
SOURCE_BOUND --相同 binding 的重复、重叠或纯增量文件--> SOURCE_BOUND
```

`source_health` 是与上述来源模式正交的 `NOT_APPLICABLE / HEALTHY / RECONCILIATION_REQUIRED / SOURCE_DIVERGED` 状态。`ImportSourceBinding.source_health` 是唯一持久化真值；account API/UI 对 `SOURCE_BOUND` 投影其唯一 binding 的 health，对 `CLEAN/MANUAL` 投影 `NOT_APPLICABLE`，不得另存可漂移副本。已绑定账户出现任一未决 authority-changing case 时立即变为 `RECONCILIATION_REQUIRED`；存在被拒绝的权威来源 observation 时优先为 `SOURCE_DIVERGED`。账户始终保持 `SOURCE_BOUND`，两个非健康状态都冻结 NEW confirm 和可信指标。只有不存在 `OPEN/RESOLVING/DIVERGED_REJECTED`，即全部 case 均为 `RESOLVED_APPLIED` 或 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY`，才恢复 `HEALTHY`。

- `GENERIC_BOOTSTRAP`：canonical CSV/Excel 一次性导入，不信任文件自带的任意交易 ID。
- `IBKR_FLEX_XML_V1`：应用定义字段合同的本地 XML 文件 adapter，允许同一 external account 对同一内部账户重复、重叠和增量导入。
- 在线 `/api/broker-sync/**`、IBKR Flex Query/Token、Binance key、网络拉取、scheduler 和后台 sync job 全部关闭。
- Source-bound 账户的 trade financial facts 由来源文件和受审计 correction 管理；普通手工 OPEN/ADD/REDUCE/CLOSE 关闭，但 narrative、review、daily note、资金流水和 cash dividend 保留。

## Source Binding

首次 source preview/confirm 使用 `source_bind_eligible`：账户必须 active、owner-validated、`trade_source_state = CLEAN` 且 `trade_history_empty`（没有 position/event、成功 non-noop trade Import、source application 或 binding），并满足 external-account unique、currency compatible 和 flat-boundary 条件。IBKR V1 只权威管理 execution/commission，所以允许保留同账户币种的 opening balance、deposit、withdrawal、interest 和 account fee；cash dividend 要求关联已有 position，因此不可能出现在 trade_history_empty 的首次绑定前。通用 CSV/Excel 的更严格 `generic_bootstrap_eligible` 不适用于 source bind。绑定成功后的同源增量不再检查首次谓词。Beta 合同：

- 每个内部账户生命周期内最多一个 source binding；binding archive 永不释放唯一槽位。
- 同一 owner 的 `(adapter_kind, normalized_external_account_ref)` 在生命周期内只能绑定一个内部账户。
- binding 创建后不可换 external account、adapter kind/version、source IANA timezone 或 owner；archive 不释放唯一槽位。Beta 不提供 rebind/transfer：首次 confirm 必须二次展示掩码 external account 与目标账户，选错内部空账户只能重命名该账户，不能搬移已应用事实。
- external account 在普通 API、UI 和日志中掩码；完整值只用于 owner-scoped identity comparison。
- 文件中的无 offset 时间使用 binding 上显式选择的 IANA timezone；不得默认 UTC。

## IBKR Flex XML V1

`IBKR_FLEX_XML_V1` 只接受本地上传文件，不需要也不保存 Flex Token。支持的 Flex Query 字段必须版本化并在模板/文档中列明，至少包含：

- external account ID
- statement `fromDate` / `toDate`
- statement generation marker（V1 预期为 `whenGenerated`；确切时区和单调/优先级语义必须由官方合同及真实 fixture 证明）
- account inception date，或 `fromDate` 时点的显式完整 OpenPositions snapshot
- ordinary execution 的 `ibExecID`
- provider-declared `event_kind = TRADE/CORRECTION/CANCEL_BUST`
- 独立 correction/cancel-bust 的 stable source event ID，以及 provider 能提供时的 target execution ID
- numeric `transactionID`
- asset category 和 `conid`
- symbol、listing exchange/exchange、currency
- buy/sell、quantity、trade price、trade time
- open/close indicator
- execution/cancel-bust status，以及 adapter 能证明时的 correction target
- IB commission 和 commission currency

ordinary execution 缺失 `ibExecID`、change row 缺失 stable source event ID、一个文件包含多个 external account、未知 asset/open-close/side、缺少标的身份或币种不匹配时整批 fail-closed。不得使用 `symbol + time + row index`、order ID 或 price/quantity fingerprint 代替 execution/source-event ID；一个 order 可以有多笔真实 fill。

首次 source bootstrap 的 `flat_boundary_proven` 只能由以下证据之一建立：

1. statement `fromDate <= accountInceptionDate`。
2. 文件显式包含覆盖完整 external account 的 `fromDate` OpenPositions snapshot，且没有任何 non-zero supported position。

缺失、不完整或存在非零期初仓位时返回 `SOURCE_FLAT_BOUNDARY_UNPROVEN`。首行看似 OPEN 不是期初 flat 证据。

XML parser 必须禁用 DTD、external entity、XInclude 和网络访问，并限制 10 MB、5,000 executions、节点数、属性数、嵌套深度和字段长度。每个 owner 最多 2 个 nonterminal session 和 10 分钟 10 次 upload。原始 statement 不进入数据库、对象存储或应用持久目录；优先有界流/内存解析，框架必须 spool 时使用专用 `0700` 临时目录和 `0600` 文件，在成功、失败、超限、取消和异常的 `finally` 中 close+unlink，并由启动/maintenance scavenger 清理崩溃 orphan。只有 normalized rows 可持久化。

Adapter 只有在逐语义 provider evidence matrix 通过后才能启用，不能用一份普通 fixture 证明所有行为。来自同一文档化 Flex Query 模板的脱敏真实 fixtures/statement pairs 至少分别证明：基础 execution 字段；跨 generation 重叠、marker 严格顺序与 tie；account inception 或完整 OpenPositions boundary；`transactionID/openCloseIndicator`；同 ID/独立 ID cancel-bust/correction target；commission sign/currency。每项同时需要官方字段合同与真实 fixture，synthetic fixture 只用于恶意输入和边界测试。任何必需语义无法证明时返回 `FEATURE_DISABLED`，不能猜测映射。

Adapter 必须按已验证的 provider inclusivity/timezone 合同，把 statement `fromDate/toDate` 规范为 source timezone 下的半开本地日期区间 `[coverage_start, coverage_end_exclusive)`；不能从 execution 行的最早/最晚时间反推 coverage。binding 持久化 `accepted_coverage_through_exclusive` projection，并以 immutable `StatementCoverageAcceptance` 作为可重建真值。首次 nonempty bootstrap 建立从已证明 flat boundary 到 statement end 的连续 coverage；后续 statement 只有在其区间与已接受 coverage 重叠或首尾相接时才能推进 watermark。区间完全落在 watermark 之前是合法重复；`coverage_start > accepted_coverage_through_exclusive` 是 `SOURCE_COVERAGE_GAP`。没有 execution 的 statement 仍可在 confirm 后推进 coverage，从而证明无交易月份没有断档。只有 source full confirm 或 source-bound `COMPLETED_NOOP` 的成功事务才为其消费的每个 statement 写 acceptance 并推进 projection；preview、CONFLICTED、FAILED 和 EXPIRED 不写 acceptance。

Canonical action 映射固定为：

| `buySell` | `openCloseIndicator` | Direction | Action |
|---|---|---|---|
| `BUY` | `OPEN` | `LONG` | running quantity 为 0 时 OPEN，否则 ADD |
| `SELL` | `CLOSE` | `LONG` | 减至 0 时 CLOSE，否则 REDUCE |
| `SELL` | `OPEN` | `SHORT` | running quantity 为 0 时 OPEN，否则 ADD |
| `BUY` | `CLOSE` | `SHORT` | 减至 0 时 CLOSE，否则 REDUCE |

首次 bootstrap 的每个 `(instrument, direction)` 从 flat quantity 0 开始；后续增量与 correction replay 从完整 current-accepted source history 和受影响 suffix 前状态继续，不能把每个上传文件单独从 0 计算。running quantity 不得为负，单个 execution 不得跨零。违反时返回 `UNSUPPORTED_CROSS_ZERO`，不能自动拆分或反向开仓。

## Execution Identity

每笔经济 execution 与每个来源 row/change 分别使用：

```text
(source_binding_id, external_execution_id)
(source_binding_id, external_source_event_id)
```

普通 execution 的 source event ID 与 execution ID 都为 `ibExecID`。每个 observation 保存 provider-declared `event_kind = TRADE/CORRECTION/CANCEL_BUST` 和可空 `affected_external_execution_id`；独立 correction/cancel-bust 必须有自己的 stable source event ID，并将 provider target 规范到 affected execution，不能把 change event ID 当作新经济 execution。缺失 stable event ID 时 fail-closed；target 缺失时已有 binding 只创建 binding/change-observation-scoped `TARGET_UNRESOLVED` case，未绑定 bootstrap 则 conflict。数据库永久保存 `SourceStatement`、immutable `StatementCoverageAcceptance`、immutable `ExternalSourceObservation`、`StatementExecutionSighting`、`ExternalExecution` 和 versioned applications。每个 acceptance 链接 binding、statement、成功 confirm session/operation idempotency record、accepted source-state revision 和 accepted timestamp；`(binding,statement)` 唯一，且 composite FK/check 保证 same-binding。unique 至少覆盖 `(binding,file_hash)` statement、`(statement,external_source_event_id,observation_id)` sighting、`(binding,external_source_event_id,fingerprint_version,fingerprint)` observation；同 statement/event ID 的同 fingerprint exact duplicate 复用 sighting，不同 fingerprint 各自持久以保留冲突证据。相同 payload 在新 statement generation 出现时仍新增 sighting，相同文件重传不新增。`latest_authority_generation(execution)` 从该 execution 的全部 trade observation sightings，以及 provider-declared 或已成功 `RESOLVED_APPLIED` 的 user-target case lineage 指向它的 cancel/correction sightings 取最大 generation；`TARGET_UNRESOLVED`、OPEN/REJECTED 或尚未 apply 的用户 target 不进入该函数。它必须可重建，且所有 `ALREADY_IMPORTED` sightings 都参与计算，不能只按相同 external execution ID 推导。

`ExternalExecution` 保存 `current_trade_observation_id`、`ACTIVE/ACCEPTED_TOMBSTONE` disposition 与 `canceled_by_observation_id`。ACTIVE 任一时点最多一个 application；tombstone 没有 active application。独立 correction/cancel-bust observation 按 `(external_source_event_id,fingerprint_version,fingerprint)` 接受一次；correction application 以 `affected_external_execution_id` 更新 target 的 current observation/version，cancel-bust 的 canceled-by 指针必须通过 composite FK/check 保证 same-binding，不假定 change event 与 target external ID 相同。source fingerprint 使用字段顺序固定的序列化，至少覆盖 adapter kind/version、normalized external account、event kind、external source event/execution/affected execution ID、transactionID、instrument/conid、raw side/open-close、quantity、price、occurred_at UTC、source timezone、currency、normalized fee/currency、execution/cancel-bust status 和 provider-declared correction target。statement provenance、用户在 resolution 选择的 target、derived direction/action/pre-post quantity 与 canonical fact linkage 不进入 source fingerprint，只进入 case/application。fingerprint 算法升级必须有 migration/dual-read。

每个 `(binding, instrument, direction)` 的完整顺序是 `source_order_key = (occurred_at_utc, numeric transactionID, external_execution_id)`；`ibExecID` 只在 provider sequence 相同时作确定性 tie-break，不声明券商时序。缺失/重复 transactionID 且交换顺序会影响 lifecycle、FIFO、fee 或 PnL 时返回 `UNSUPPORTED_ORDER_CONFLICT`；只有模拟证明交换顺序财务等价时才可使用 external ID tie-break。append boundary 是该分组最后一个 current-accepted execution 的 order key；新 ID 小于或等于边界是 `LATE_NEW`。

同一个 source observation 在 preview 中只能得到以下状态之一：

| 状态 | 含义 | Confirm 行为 |
|---|---|---|
| `NEW` | ordinary TRADE execution 尚无 accepted application/tombstone 或 nonterminal case，且 chronology 可追加；允许此前已 sighted 但从未应用 | 纳入 binding-wide full confirm set，不允许逐行排除 |
| `ALREADY_IMPORTED` | `(external_source_event_id,fingerprint_version,fingerprint)` 匹配 current active trade 或已接受 correction/cancel-bust observation | canonical no-op；新 statement provenance 仍写 sighting |
| `KNOWN_HISTORICAL_OBSERVATION` | fingerprint 匹配已 superseded/reversed trade，或已由 terminal case supersede 的 target-known change，且 generation 严格早于 target `latest_authority_generation` | 固定 stale no-op + warning，不新建 case |
| `STALE_SOURCE_OBSERVATION` | 此前未见的 same-execution trade 或 target-known change payload，但 generation 严格早于 target `latest_authority_generation` | 保留 sighting/evidence，固定 stale no-op + warning，不冻结 health |
| `DIVERGED_REJECTED_OBSERVATION` | 同 observation 曾被明确拒绝，且当前 sighting 不构成 strict-later authority episode | 展示原 case；`source_health` 保持 SOURCE_DIVERGED |
| `SOURCE_PAYLOAD_CONFLICT` | 排除已知 historical/stale 后，同代或更晚 authority 的同 ID fingerprint 变化 | 阻断并进入 reconciliation |
| `LATE_NEW` | 新 ID 早于当前可追加边界 | 阻断并进入 reconciliation |
| `SOURCE_SEQUENCE_GAP` | binding-wide pending NEW 无法从 accepted boundary 连续重放 | 整批阻断，不允许跳行或部分确认 |
| `TARGET_UNRESOLVED` | change event 有稳定 identity，但没有 provider target | 创建 binding-scoped OPEN case；不做 target authority comparison 或自动 supersede |
| `CORRECTION` | 来源声明更正既有 execution；独立 event ID 仍以 affected target 为 authority scope | 阻断并进入 reconciliation，绝不作为 NEW |
| `CANCEL_BUST` | 来源声明取消/冲销既有 execution | 阻断并进入 reconciliation |
| `UNSUPPORTED` | 字段、资产或事件不在 allowlist | 阻断 |
| `ACCOUNT_MISMATCH` | 文件 external account 与 binding 不同 | 阻断 |

`SOURCE_COVERAGE_GAP` 是 statement/binding-wide 状态，不伪装成某一 execution 的 observation 状态：当 acceptances 重建的 coverage 与所有尚无 acceptance 的 pending statement coverage 并集仍不连续时，session 以 `CONFLICTED` 阻断 confirm，`source_completeness` 保持 `PENDING_IMPORT`，但不创建错误的 execution reconciliation case。后续上传能补齐缺口的 statement 后，新 preview 必须纳入 binding-wide pending statements/NEW 全集并可一次 full confirm。`transactionID` 只用于 statement 内 execution 顺序，数值不连续不能证明 coverage gap。

分类使用固定优先级，避免同一行同时命中 conflict 与 cancel：

1. 先判 `ACCOUNT_MISMATCH/UNSUPPORTED`。
2. 再以已接受 observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 匹配 current active trade 或已接受 correction/cancel-bust，命中即 `ALREADY_IMPORTED`，但新 statement generation 仍写 sighting；同 event identity 不同 fingerprint 不得 no-op。
3. 再查找相同的 nonterminal/rejected case 并附加 evidence；不得在此提前返回，所有新 sighting 仍继续做 authority comparison，strict-later 时可在同一事务收口旧 case 并建立 winning episode。
4. target 缺失的 change 无法做 authority comparison：若其 event identity 已有 accepted fingerprint 而本次不同，则固定为 `SOURCE_PAYLOAD_CONFLICT`；否则归为 binding-scoped `TARGET_UNRESOLVED`，只创建/复用 case 和 evidence，不执行 target authority comparison 或自动 supersede。
5. target 已知的 change 先以 target authority scope 判 historical/stale：fingerprint 匹配已由 terminal case supersede 的 change，且 generation 严格早于 target `latest_authority_generation`，归为 `KNOWN_HISTORICAL_OBSERVATION`；此前未见的 target-known change payload 若 generation 也严格更早，归为 `STALE_SOURCE_OBSERVATION`。即使同一 accepted change event identity 出现新 fingerprint，只要 generation 严格更早，也必须先走该 stale 分支。两者都只保留 evidence/warning，不重开 case。
6. 通过上一步后，同代或更晚 authority 上已接受 correction/cancel-bust event identity 的新 fingerprint 固定为 `SOURCE_PAYLOAD_CONFLICT`；其余 provider-declared cancel/bust 归为 `CANCEL_BUST`，correction 归为 `CORRECTION`。同 ID change 可覆盖 target ordinary event，独立 ID change 使用 `affected_external_execution_id`，两者都不能进入 NEW；同代或更晚时重申旧 change payload 必须创建新 episode。
7. 普通 TRADE observation 再按历史 fingerprint 和 `latest_authority_generation(execution)` 判 known historical、unseen stale 或 payload conflict。
8. 最后才按 group append boundary 判 `NEW/LATE_NEW`；已有 sighting 但从未 accepted 的可追加 TRADE 仍是 NEW。

cancel/bust 被应用后，target execution 持久化 `ACCEPTED_TOMBSTONE`，`canceled_by_observation_id` 指向 same-binding cancel observation，cancel observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 标记 accepted；该指针对 target 可空唯一且必须 same-binding。完全相同的取消文件重传是 `ALREADY_IMPORTED`。此后较旧 statement 中原 execution 是 `KNOWN_HISTORICAL_OBSERVATION`，同 generation 或较新 generation 重新声明原 execution 则是 `SOURCE_PAYLOAD_CONFLICT`。同理，C2@G2 的 rejected case 被 C3@G3 strict-later authority 终止后，C2 所在旧 statement 重分类为 `KNOWN_HISTORICAL_OBSERVATION` 并可接受其 coverage；G3 同代或 G4 更晚重申 C2 则创建新 episode。用户在 resolution 选择的 target 只存 case/application，不能回写 provider source fingerprint。任何历史 fingerprint 在 generation 相等但 payload 不同时都不能 stale no-op；只有严格更早才是 stale。generation marker 缺失或其优先级语义未通过 provider-contract gate 时 adapter fail-closed，不能用上传时间或本地文件修改时间猜测。

## Preview And Confirm

1. upload 强制 operation-scoped Idempotency-Key，request hash 包含 owner/account/adapter/file hash；同 key/hash 重放同一响应，different hash 409。随后持久化 owner/account-bound ImportSession。
2. 安全解析、规范化 instrument/time/fee，并生成 source payload fingerprint。
3. 已有 binding 时，在 owner/source binding 范围内幂等写 SourceStatement/observation/sighting 并分类每个 source event；ALREADY_IMPORTED 的新 generation sighting 也必须保留。尚无 `StatementCoverageAcceptance` 的 statement 才属于 pending coverage，preview/conflict 写入永久 SourceStatement 不等于 coverage 已接受。未绑定首文件只在 owner/account-bound ImportSession/Row 保存 normalized preview，首次 confirm 才原子创建 binding 和永久 source records。
4. Preview 展示 binding 当前全部 pending statements、coverage extensions 与 `NEW`，并生成 versioned `source_preview_digest`；source confirm 不接受 row selection。digest 覆盖 accepted-source-state revision/hash、`accepted_coverage_through_exclusive`、全部 pending coverage intervals、各 group append boundary、pending observation `(external_source_event_id,fingerprint_version,fingerprint,order key)`，以及展示的 derived action/pre-post quantity/amount/fee。pending coverage 的并集必须与 accepted coverage 连续，每个 `(instrument, direction)` 的 pending set 必须从 current accepted boundary 连续可重放，否则整批 conflict。
5. Confirm 按 account -> source binding -> positions 的顺序加锁并重新分类。
6. 普通成功路径在一个数据库事务中写 source statement/sighting/execution/observation/application、每个 consumed statement 的 `StatementCoverageAcceptance`、PositionEvent、ledger、session completion 和 watermark projection；source-bound 无 NEW 的 coverage-only noop 同样在一个事务中写 acceptance/session completion/watermark。
7. upload 与 confirm 使用不同 operation scope 的无 TTL idempotency record；请求顺序为 auth/owner -> operation record -> matching key/hash replay -> state/TTL。upload 的 `PREVIEW_READY/CONFLICTED` 和 confirm 的 `COMPLETED/COMPLETED_NOOP/CONFLICTED` 都可跨 TTL 确定重放。

重复、重叠和纯增量文件都是正常输入。coverage watermark 证明时间区间连续性，execution unique constraint 证明经济事实只应用一次，两者不能互相替代。相邻月报的旧 execution 是 `ALREADY_IMPORTED`；更正后重传较旧月报中的旧版本是 `KNOWN_HISTORICAL_OBSERVATION`；两者都不重复记账。已有 statement/observation/sighting 但因 session 过期或尚未 confirm 而从未 accepted 的 ordinary execution 仍是 `NEW`。首次 source confirm 若没有任何 `BOOTSTRAP_EFFECTIVE_NEW` unit 则进入 `COMPLETED_NOOP`，不创建 binding/permanent source records，账户保持 `CLEAN`；nonempty confirm 应用全部 folded economic units，不允许 partial selection。已有 binding 的 confirm 锁内按相同 schema 重算完整 preview digest；pending IDs 不变但 accepted baseline、coverage intervals、correction/replay、append boundary 或 derived result 变化同样返回 409 `SOURCE_PREVIEW_STALE`，相同才原子确认全部连续 coverage 并应用全部 pending NEW；没有 NEW 的合法相邻 statement 也可 `COMPLETED_NOOP` 并推进 coverage。并发重叠 confirm 最多允许一个 application 成功，另一请求必须重放/no-op/conflict，不能返回 500 或重复记账。

`source_completeness` 是从 `StatementCoverageAcceptance`、statement coverage、observations 和 applications 可重建的 `CURRENT/PENDING_IMPORT` 投影。frontier 只取从首次 accepted boundary 开始连续的 accepted intervals；binding scalar watermark 必须与该重建结果一致。preview 一旦持久化尚无 acceptance 的 coverage extension，或可确认但尚未 accepted 的 `NEW`，立即变为 `PENDING_IMPORT`；只有 coverage 连续且成功 full confirm 后才回到 `CURRENT`。这里的 `CURRENT` 只表示“截至 `accepted_coverage_through_exclusive` 没有已上传待确认内容”，不表示文件 adapter 已实时同步到券商当前时刻。`source_health = HEALTHY` 只代表没有 reconciliation divergence，可信 Dashboard/derived 和 release gate 还必须要求 completeness CURRENT。UI 始终显示 last-confirmed coverage/as-of；PENDING 时另显示待确认区间和数量。

Binding 真值（及其 account 投影）的 `source_health` 为 `RECONCILIATION_REQUIRED` 或 `SOURCE_DIVERGED` 时，preview 仍可收集新 observation，但普通 confirm 必须整体返回 409 并指向全部未清 cases；即使后续 statement 不再包含原冲突行，也不能绕过冻结继续记 NEW。

领域冲突不是技术失败。已有 binding 时，preview 或 confirm 重新分类发现 payload conflict、late/sequence gap、correction/cancel-bust 或 unresolved target，必须以零 canonical side effect 持久化 statement/sighting/observation、case episode、`CONFLICTED` session 终态和冲突响应。episode 以 `trigger_sighting_id + case_kind + against_source_state_hash` 标识；`SourceCaseEvidenceSighting(case,sighting)` 附加同 episode 的后续证据；`OPEN/RESOLVING/DIVERGED_REJECTED` 是仍影响 health 的 nonterminal 状态，`RESOLVED_APPLIED/RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 才是已清 terminal 状态。PostgreSQL partial unique 保证同一 `(binding,conflict_observation,case_kind,against_source_state_hash)` 最多一个 nonterminal case，但 terminal case 不阻止任一新的 trigger sighting 创建新 episode，即使 baseline hash 未变；相同 sighting replay 不创建 episode。`against_source_state_hash` 与 schema version 和可审计 snapshot 一起保存；snapshot 是按 case kind 选定 authority scope 的版本化 canonical serialization，至少包含 binding、current observation/fingerprint version、execution disposition、canceled-by observation、active application/version，并对 late/order/correction replay 加入受影响 group 的 accepted application/order-key 序列与 append boundary。`TARGET_UNRESOLVED` 保存 target=null、change observation 和 owner-scoped candidate execution ID digest，不伪造 execution scope。trigger/evidence 不进入 baseline hash；任何会改变冲突判断的 current source/application/group state 必须改变 snapshot/hash。每次变化调用唯一 health 聚合函数：任一 DIVERGED_REJECTED -> SOURCE_DIVERGED；否则任一 OPEN/RESOLVING -> RECONCILIATION_REQUIRED；否则 HEALTHY。

未绑定首文件在普通同-ID payload conflict 判定前，先在 ImportSession/Row 内运行 bootstrap change-chain recognizer。只有 provider-declared change kind、稳定 change identity、明确 target、完整 source order 且 chain 闭合的 correction/cancel-bust rows 才可折叠；被替代 trade 标记 `BOOTSTRAP_SUPERSEDED`，最终取消的 target 标记 `BOOTSTRAP_ACCEPTED_TOMBSTONE`。每个 ordinary trade 或 closed chain 形成一个 `BOOTSTRAP_EFFECTIVE_NEW` economic unit，winning observation 可以是 CORRECTION。没有这些 change 语义的同 event ID 不同 fingerprint 固定以 `CONFLICTED + SOURCE_BOOTSTRAP_CONFLICT(reason=PAYLOAD_ID_COLLISION)` 结束。首次 nonempty confirm 原子建立 binding、statements/sightings/observations/executions/tombstones，应用全部 effective units，并将 chain 中每个 correction/cancel-bust observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 记为 accepted/superseded lineage；winning correction 设置 target current observation，最终 cancel 设置 tombstone/canceled-by。source confirm 不允许 partial selection；已在文件内确定解决的历史 correction 不生成 compensating facts。payload collision、target 缺失/歧义、change identity 不稳定或 chain 不闭合都只保留 session evidence，以 `CONFLICTED + SOURCE_BOOTSTRAP_CONFLICT` 结束并提示扩大 statement 范围或修正 Query；不创建 binding、SourceStatement、observation、sighting、execution、case 或 canonical fact。技术错误或财务写入失败则回滚整个 confirm 事务，不留下部分 application/event/ledger/watermark。

## Reconciliation

`SOURCE_PAYLOAD_CONFLICT`、`LATE_NEW`、`SOURCE_SEQUENCE_GAP`、`TARGET_UNRESOLVED`、correction 和 cancel-bust 不自动改变财务事实。相同或更早 authority 的普通重传不会使它们自行消失；只有 versioned resolution，或对已知 target 且 provider order 可证明的 strict-later authority sighting，才能收口旧 episode。`SourceReconciliationCase` 使用：

```text
OPEN -> RESOLVING -> RESOLVED_APPLIED | DIVERGED_REJECTED
DIVERGED_REJECTED -> RESOLVING -> RESOLVED_APPLIED
OPEN | DIVERGED_REJECTED --strict-later authority--> RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY
```

`TARGET_UNRESOLVED` 使用 `OPEN` case state，但在 target 选定并通过 same-binding validation 前不允许走 strict-later authority transition。

- case 创建、reject、apply 和 authority-supersede 后都调用同一个 health 聚合函数；`DIVERGED_REJECTED` 不改变 canonical facts 和 `trade_source_state = SOURCE_BOUND`。相同 conflict observation、case kind 和 baseline 的后续 sighting 复用原 nonterminal case 并附加 evidence，但 evidence attachment 不得 short-circuit authority comparison；terminal case 永不 reopen，后续任一新 trigger sighting 可创建新 episode，即使 `against_source_state_hash` 未变。`RESOLVED_APPLIED/RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 都视为已清。
- `RESOLVED_APPLIED` 在 account/binding/position 锁内找出最早冲突后的 source application suffix，先从新到旧创建 compensating facts，再插入 late/corrected observation 或移除 cancel/bust application，最后按稳定 source 顺序从旧到新重放 suffix。
- 原 statement/sighting/observation、fact 和 application 不删除；旧 application 标记 `SUPERSEDED/REVERSED`，replacement application 递增 version 并链接 `replaces_application_id`。correction resolution 必须接受 correction observation 的 `(external_source_event_id,fingerprint_version,fingerprint)` 并更新 target current observation/version；cancel-bust resolution 必须接受 cancel observation 的 `(external_source_event_id,fingerprint_version,fingerprint)`，并设置 target accepted tombstone/canceled-by observation。
- resolution 在写入前锁定并复验 `latest_authority_generation(execution)`。若已有 strict-later winning sighting，且无 provider lineage 证明当前 observation 优先，则以零 canonical side effect 原子转为 `RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY` 并永久链接 winning sighting/observation；若 winning payload 仍与 canonical current 冲突，则必须在同一事务创建/复用针对当前 baseline 的新 `OPEN` episode，最后才重算 health，不能短暂或错误恢复 `HEALTHY`。否则 `RESOLVING` 和其余 work 在同一事务/锁范围内；全部补偿、replacement facts、accepted trade observation/canceled-by tombstone、case 终态、health 重算和 derived invalidation 一次提交。失败回滚到命令开始前稳定状态：从 `OPEN` 发起仍为 `OPEN/RECONCILIATION_REQUIRED`，从 `DIVERGED_REJECTED` 发起仍为 `DIVERGED_REJECTED/SOURCE_DIVERGED`。
- correction/cancel-bust 必须有 adapter 可证明的 target，或由用户显式选择 exact owner/same-binding original execution。`TARGET_UNRESOLVED` 重复 sighting 只附加 evidence，不执行 target authority comparison 或自动 supersede；用户选择后在 target lock 内保存 resolution snapshot/hash，并复验 event semantics、latest authority 和 replay，只有成功 APPLIED 后 user-target lineage 才进入该 execution 的 authority generation。无法唯一关联时不得解决为 APPLIED。
- 产品提供 owner-scoped case list/detail 与字段差异 UI；`APPLY_VERSIONED_REPLAY` 要求 exact owner/same-binding target，`REJECT_AS_DIVERGED` 对 `TARGET_UNRESOLVED` 允许 `target = null` 并保持 binding-scoped divergence。两种命令都要求 reason 和二次确认，不能接受任意或越权 internal ID，并必须清楚显示 REJECT 会冻结来源可信状态。

## Retention And Export

- 原始文件不长期保存，并遵守所有失败路径 unlink 与 crash orphan scavenging 合同。
- `COMPLETED/COMPLETED_NOOP/CONFLICTED/FAILED/EXPIRED` normalized preview rows 保留 30 天后由限批、幂等 maintenance command 删除。
- ImportSession audit shell、source binding、accepted coverage watermark、`StatementCoverageAcceptance`、SourceStatement coverage/sighting、external source event/execution ID/fingerprint、current trade observation/canceled-by tombstone、conflict/application linkage 和 confirm/CONFLICTED response 随账户永久保留。
- Canonical export 必须包含这些 source linkage，且能独立验证每个 observation/application version 最多应用一次、每个 `ACTIVE` execution 最多一个 active application、每个 `ACCEPTED_TOMBSTONE` 没有 active application。

## Deferred Network Sync

未来在线 IBKR/Binance sync 必须复用本设计的 binding、execution identity、preview classification 和 canonical confirm，不得直接把远程 payload 写入持仓。重新启用前还需完成受管个人凭据、connection lock/request idempotency、错误脱敏、失败恢复、调度与 provider 行为验证。
