# Platform Foundation & Frontend Redesign Sequencing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align backend platform foundation delivery with the patched frontend redesign so the new timeline-first product can ship without rework on stale DTOs or deprecated trading semantics.

**Architecture:** Backend owns truth models, user-facing read contracts, and trust metadata. Frontend starts in parallel on shell, design system, and adapters, then migrates Timeline, Lifecycle Detail, Dashboard, and Insights only after the matching backend gates are complete.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Redis, Next.js App Router, TypeScript, Tailwind CSS, ECharts

---

## Current Status

**Authoritative plan:** This document is the current execution plan for new platform/frontend work. `docs/TODO.md` is retained as a legacy backlog and historical progress snapshot.

**Implementation state:** Not started. The current codebase still uses runtime `Base.metadata.create_all()`, old `Position / TradeBatch` semantics, dashboard-first home routing, and `frontend/lib/api.ts` as the broad DTO layer.

**Next active gate:** Task 1. Task 0 decisions are locked below. Do not begin schema migrations or page rewrites until the shared contract surface is frozen.

---

## Decision Register

Task 0 locks these choices for implementation workers. Reopen a decision only with an explicit plan amendment.

| Decision | Locked choice | Depends on it |
| --- | --- | --- |
| Public identifiers | Use ULID strings for all external `public_id` values. Store as fixed-length `CHAR(26)` / `String(26)` with unique indexes. Generate application-side in the domain/service layer. Route params use lower-risk opaque strings such as `/api/v1/trading-positions/{position_public_id}`. | Task 1 contracts, Task 2B identity baseline, Task 3 truth model, all frontend deep links |
| API versioning | All new user-facing and admin endpoints use `/api/v1/...`. Existing `/api/...` endpoints remain legacy until hard cutover. | Task 1 contracts, Task 2B auth/session routes, Task 5 read models |
| Alembic strategy | Use one Alembic env for all schemas with `include_schemas=True`. Migrations create schemas explicitly and remain the only schema evolution path. | Task 2A migration baseline, Task 3 schema cutover |
| Async execution | Use Redis + `arq` workers for job execution. Persist visibility in `audit.job_definitions`, `audit.job_runs`, and `audit.job_run_events`. Failed jobs stay queryable; dead-letter means terminal failed `job_runs` plus retry metadata, not a hidden queue. | Task 2C observability, Task 3 outbox/job/idempotency, Task 7 admin job views |
| Transactional outbox | Business writes that require derived refresh must insert `audit.outbox_events` in the same database transaction. A relay publishes outbox events to Redis/arq. | Task 3 truth model, Task 5 derived read models |
| Realtime UX | Use polling for simple page refresh and SSE for job/data freshness streams. Do not implement WebSocket in V1 unless a later AI/chat interaction requires bidirectional communication. | Task 4 frontend primitives, Task 5 freshness UX, legacy risk-alert reclassification |
| Rate limiting | Use Redis sliding-window limits: auth `10/min/IP`, general API `120/min/user`, market data `60/min/user`, import `5/hour/user`, AI `10/hour/user` until pricing/quota exists. | Task 2C observability/security, Task 7 AI usage controls |
| Structured logging | Use JSON structured logs with `request_id`, `actor_type`, `user_public_id`, `route`, `method`, `status_code`, `latency_ms`, `error_code`, `object_public_id`, and provider/job fields when relevant. Replace `print()` on touched paths. | Task 2C observability, Task 7 ops views |
| Error taxonomy | Use namespaced error codes: `auth.*`, `trading.*`, `market.*`, `analytics.*`, `ai.*`, `content.*`, `platform.*`. Public responses expose stable codes and safe messages. | Task 1 trust contracts, Task 2C logging, frontend error states |
| External signals | Treat `ExternalCatalyst`, `EvidenceItem`, and `NarrativeSignal` as V1 read-model concepts, but not as a raw news product. Store source metadata, links/refs, short copyright-safe summaries, timestamps, confidence, and invalidation clues. | Task 1 contracts, Task 4 mocks, Task 5 timeline/lifecycle read models |
| Connection pooling | Defer PgBouncer until worker and production deployment work begins. Safe to defer because Task 2/3 can use SQLAlchemy pool settings locally, and PgBouncer does not change user-facing contracts. | Task 7 ops/release hardening |
| PDF export | Defer until lifecycle detail and chart schema contracts stabilize. Safe to defer because it is a secondary output surface and should consume stabilized read models. | Legacy backlog reclassification, Phase 5 polish |

## Shared Contract Register

Task 1 freezes these names and enums for backend schemas, read models, frontend adapters, and trust UI.

**Canonical domain names:**
- `AssetMaster`: stable listed asset or currency/crypto identity.
- `TradeInstrument`: tradable instrument under an asset, including options.
- `TradingPosition`: one user/account/instrument lifecycle from open to close.
- `PositionEvent`: append-only event that changes or documents a trading position.
- `AccountLedgerEntry`: cash truth for deposits, withdrawals, fees, dividends, adjustments, and event-linked cash movements.
- `ExternalCatalyst`: external event or narrative linked to a position, symbol, rule, or review action.
- `EvidenceItem`: source-backed evidence object referenced by timeline, lifecycle, Review Inbox, or AI artifacts.
- `NarrativeSignal`: derived interpretation of one or more evidence items, with sample size and confidence.

**Frozen enums:**
- `cost_basis_method`: `FIFO`. `AVERAGE_COST` is reserved but not enabled in V1.
- `freshness`: `FRESH`, `DELAYED`, `STALE`, `DEGRADED`.
- `source`: `MANUAL`, `IMPORTED`, `SYNCED`, `DERIVED`, `AI_GENERATED`, `EXTERNAL`.
- `maturity`: `INSUFFICIENT_SAMPLE`, `EARLY_SIGNAL`, `STABLE`.
- `value_status`: `ESTIMATED`, `FINAL`.
- `severity`: `INFO`, `LOW`, `MEDIUM`, `HIGH`, `BLOCKING`.
- `timeline_event_type`: `OPEN`, `ADD`, `REDUCE`, `CLOSE`, `REVIEW_COMPLETED`, `AI_INSIGHT`, `CHECKLIST_MISS`, `LOSING_STREAK_ALERT`, `DATA_STALE`, `SYNC_EXCEPTION`, `EXTERNAL_CATALYST`.
- `review_inbox_kind`: `MISSING_THESIS`, `REVIEW_DUE`, `CHECKLIST_MISS`, `LOSING_STREAK`, `PLAN_DRIFT`, `DATA_STALE`, `SYNC_EXCEPTION`, `CATALYST_REVIEW`.
- `lifecycle_node_type`: `OPEN`, `ADD`, `REDUCE`, `CLOSE`, `REVIEW`, `AI_CONCLUSION`, `EXTERNAL_CATALYST`.
- `evidence_kind`: `USER_NOTE`, `CHECKLIST`, `SCREENSHOT`, `IMPORT_FILE`, `BROKER_SYNC`, `MARKET_DATA`, `NEWS_LINK`, `SOCIAL_SIGNAL`, `AI_ARTIFACT`, `SYSTEM_EVENT`.
- `narrative_signal_type`: `NEWS_CATALYST`, `SOCIAL_SENTIMENT`, `OPTION_POSITIONING`, `MACRO_EVENT`, `EARNINGS_EVENT`, `POLICY_EVENT`, `DATA_QUALITY`.

**User-facing read-model envelopes:**
- Every user-facing read model returns `meta: TrustMeta`.
- Every object intended for routing returns `public_id`; internal integer `id` stays server-side.
- Every AI-visible conclusion returns `evidence_refs`; unsupported commentary is not a valid artifact.
- External catalyst signals are included only when linked to user positions, watchlist symbols, rules, or lifecycle evidence.

**Backend gates that unlock frontend phases:**
- Frontend Phase 1 unlocks after Task 1 contracts are frozen.
- Frontend Phase 2 unlocks after Task 3 minimum truth-model slice plus Task 5 timeline/read model contracts.
- Frontend Phase 3 unlocks after Task 3 plus Task 5 lifecycle/evidence contracts.
- Frontend Phase 4 unlocks after chart schema and AI artifact contracts are stable.

### Task 0: Lock the pre-implementation decision register

**Why this exists:** Several choices affect database shape, URL contracts, async semantics, and frontend adapters. Freezing them first prevents expensive "almost right" work.

**Decisions to lock:**
- Public identifier strategy: `UUID` vs `ULID`, storage type, generation location, and route format.
- API versioning: whether all new user-facing endpoints start at `/api/v1`.
- Alembic strategy: single Alembic env with `include_schemas=True` for all schemas.
- Async strategy: worker library or queue primitive, retry policy, dead-letter handling, and job visibility.
- Realtime strategy: polling vs SSE vs WebSocket for job/data freshness updates.
- Rate limiting baseline: auth, AI, market data, import, and general API budgets.
- Structured logging baseline: event names, request IDs, actor fields, and error-code taxonomy.
- External signal boundary: whether `ExternalCatalyst / EvidenceItem / NarrativeSignal` are first-class read-model concepts in V1.

- [x] Create a short decision register inside the implementation plan or linked spec.
- [x] Choose one option for each decision above; do not leave alternatives open for implementers.
- [x] Record which later task depends on each decision.
- [x] Mark any deferred decision as explicitly non-blocking and explain why it is safe to defer.

**Exit Criteria:**
- Task 1 contracts can use final names and URL/id assumptions.
- Task 2 migration/auth/logging/test work can proceed without reopening architecture debates.

### Task 1: Freeze the shared contract surface

**Outputs:**
- `TradingPosition / PositionEvent / AccountLedgerEntry / public_id / FIFO`
- User-facing meta fields: `as_of / freshness / source / maturity / value_status`
- Home contracts: `timeline feed`, `review inbox`, `context rail`, `external catalyst signals`
- Detail contracts: `lifecycle thread`, `evidence list`, `AI sidecar references`

- [x] Freeze names and enums before schema work spreads.
- [x] Freeze the user-facing trust metadata envelope.
- [x] Freeze homepage event types and Review Inbox item shape.
- [x] Freeze lifecycle detail node types and evidence link requirements.
- [x] Record the backend gates that unlock each frontend phase.
- [x] Freeze external catalyst / narrative signal shape as evidence, not as a raw news feed.

**Contract minimums:**
- `TrustMeta`: `as_of`, `freshness`, `source`, `maturity`, `value_status`, `generated_by`, `source_refs`.
- `TimelineEvent`: `public_id`, `type`, `occurred_at`, `subject`, `summary`, `impact`, `trust_meta`, `linked_object_public_id`, `evidence_refs`.
- `ReviewInboxItem`: `kind`, `severity`, `summary`, `reason`, `recommended_action`, `linked_object_public_id`, `due_state`, `trust_meta`.
- `LifecycleNode`: `type`, `occurred_at`, `position_public_id`, `event_public_id`, `decision_fields`, `execution_fields`, `ledger_refs`, `evidence_refs`.
- `EvidenceItem`: `public_id`, `kind`, `source_name`, `source_url_or_ref`, `captured_at`, `summary`, `linked_tickers`, `confidence`, `invalidates_if`.
- `NarrativeSignal`: `public_id`, `signal_type`, `direction`, `strength`, `sample_size`, `time_window`, `linked_evidence_public_ids`, `trust_meta`.

**Exit Criteria:**
- Frontend can build adapters and trust components without guessing field shapes.
- Backend can refactor internals without breaking page contracts.
- Homepage remains an action timeline, not a social/news feed.

### Task 2: Ship Package 0 and Package 1 first, as four baselines

**Scope:**
- Stage 0 freeze items
- `A1`, `A2`, `A3`
- `B1`, `B2`, `B3`
- `H1`, `H4`

- [ ] Make Alembic the only schema path.
- [ ] Introduce `public_id` and auth/session tables.
- [ ] Freeze logging and error-code conventions.
- [ ] Build migration and test baseline before truth-model cutover.

**Baseline slices:**
- `2A Migration baseline`: schema creation, Alembic env, migration template, removal plan for runtime `create_all()`.
- `2B Identity baseline`: user `public_id`, normalized email, user status, session/credential/token tables, route identifier policy.
- `2C Observability baseline`: structured logs, request ID propagation, error-code namespaces, provider/job log fields.
- `2D Test baseline`: pytest skeleton, migration smoke test, auth smoke test, trading accounting unit-test fixture pattern.

**Exit Criteria:**
- No more `create_all()`-driven schema drift.
- Frontend routing can assume `public_id`.
- Core changes are testable and observable.
- A new worker can run `migration/auth/logging/test` verification without reading legacy TODO.

### Task 3: Move the trading truth model before page migrations

**Scope:**
- `C1`, `C2`, `C3`, `C4`, `C5`
- `D1`, `D2`, `D3`

- [ ] Replace `Position / TradeBatch` semantics with `TradingPosition / PositionEvent`.
- [ ] Move cash truth to `AccountLedgerEntry`.
- [ ] Centralize FIFO, fee, FX, and realized/unrealized rules.
- [ ] Promote decision-quality fields into first-class event data.
- [ ] Put outbox, job model, and idempotency in place before derived refresh depends on them.

**Minimum truth-model slice:**
- Open a trading position from one opening event.
- Add or reduce via additional position events.
- Close the position with FIFO realized PnL.
- Write related account ledger entries for cash, fees, dividends, and manual adjustments.
- Emit outbox events for derived refresh after core writes.

**Exit Criteria:**
- Frontend no longer depends on old DTO names or moving-average cost math.
- Timeline, Review Inbox, and lifecycle pages have the minimum story data they need.
- Import, dashboard, and AI migration are not started until this minimum slice is demonstrably stable.

### Task 4: Let frontend start in parallel, but only on stable surfaces

**Frontend may start now:**
- user/admin shell split
- navigation
- token system
- typography and number system
- primitive components
- freshness / source / sample-size UI
- adapter skeleton and mock view models
- evidence card primitives
- external catalyst / narrative signal display mocks

**Frontend must wait:**
- Timeline + Review Inbox waits for `Task 5`
- Lifecycle Detail waits for `Task 5` plus decision-quality data
- Dashboard + Insights waits for `Task 6`
- Real external catalyst ingestion waits until evidence contracts and source policy are approved.

- [ ] Avoid new work on `frontend/app/page.tsx` as the product's long-term home.
- [ ] Avoid expanding `frontend/lib/api.ts` as the permanent DTO contract layer.
- [ ] Land reusable trust and UI primitives before page rewrites.
- [ ] Keep mock timeline data behind adapters so it can be replaced by Task 5 read models.

**Exit Criteria:**
- The visual and system layer can move without baking in obsolete backend shapes.
- Frontend can show evidence and catalyst concepts without turning the homepage into a news terminal.

### Task 5: Deliver user-facing read models before the new homepage

**Scope:**
- `I1`, `I2`, `I3`
- `E1`, `E2`
- `F1`, `F2`, `F4`

- [ ] Publish the user-facing meta envelope.
- [ ] Build `timeline + review inbox` read models.
- [ ] Build `lifecycle detail + evidence` read model.
- [ ] Split market orchestration and stabilize provider mapping.
- [ ] Move expensive dashboard and detail reads into derived/materialized paths.
- [ ] Add external catalyst signals only when linked to user positions, watchlist symbols, rules, or lifecycle evidence.

**Read-model boundaries:**
- Timeline returns action-worthy events only; raw system noise is excluded by default.
- Review Inbox is a task list, not a notification stream.
- Context rail summarizes the selected object and links evidence, but does not duplicate Dashboard.
- External catalysts must include source, timestamp, linked ticker/object, confidence, and an invalidation clue.
- AI sidecar references evidence artifacts; it does not emit unsupported markdown commentary.

**Exit Criteria:**
- Frontend Phase 2 can ship the new homepage.
- Frontend Phase 3 can ship lifecycle detail without stitching raw endpoints.
- Dashboard and charts can consume schema-first payloads.
- Sell-the-news style signals are absorbed as evidence-linked catalysts, not copied as a realtime news product.

### Task 6: Ship pages in product order, not current code order

**Page order:**
1. Timeline + Review Inbox
2. Lifecycle Detail + Rules & Checklist
3. Dashboard + Insights
4. Settings and admin polish

- [ ] Ship the homepage as the default landing surface.
- [ ] Make single-trade detail a lifecycle thread, not a tabbed field sheet.
- [ ] Keep Dashboard as macro view, not the default home.
- [ ] Keep AI as evidence-linked sidecar across surfaces.

**Exit Criteria:**
- Product center of gravity shifts from dashboard-first to timeline/review-first.
- Users can move from capture to review to learn without page-model mismatch.

### Task 7: Hold the AI and chart migrations until their contracts are real

**Scope:**
- `F3`
- `G1`, `G2`, `G3`
- `D4`
- `H3`, `H5`

- [ ] Switch chart rendering only after chart schema is stable.
- [ ] Switch AI cards only after `insight_runs / insight_artifacts` are auditable.
- [ ] Expose job status and data freshness before relying on async UX.
- [ ] Finish release and rollback playbooks before hard cutover.

**Exit Criteria:**
- Charts are renderer-swappable.
- AI output is explainable and linkable.
- Ops can see stale, broken, and backlogged systems before users do.

### Frontend Gate Table

| Frontend phase | Backend gate |
| --- | --- |
| Phase 0: adapter mocks / token exploration | Task 0 decisions complete |
| Phase 1: shell / nav / design system / trust layer | Task 1 complete |
| Phase 2: timeline + review inbox | Task 3 core truth complete + Task 5 timeline contracts complete |
| Phase 3: lifecycle detail + rules | Task 3 complete + Task 5 lifecycle contracts complete |
| Phase 4: dashboard + insights | Task 5 complete + AI/chart contracts from Task 7 ready |
| Phase 5: polish / secondary surfaces | Prior phases stable + ops visibility in place |

### Legacy Backlog Reclassification

Before any `docs/TODO.md` item is implemented, reclassify it against the current plan:

| Legacy item | New disposition |
| --- | --- |
| Risk alerts / WebSocket | Convert to derived `risk_views` + Review Inbox items; prefer polling/SSE unless Task 0 selects WebSocket. |
| PDF export | Defer until lifecycle/detail and chart schema contracts stabilize. |
| AI date range selector | Rebuild around `insight_runs / insight_artifacts`, not old analysis result filters. |
| Admin operations | Split into `admin/jobs`, `admin/market-data`, `admin/ai`, and `admin/ops` after job/freshness foundations exist. |
| Checklist/dashboard display leftovers | Fold into Timeline, Review Inbox, and Rules pages; do not patch old dashboard-first surfaces. |

### Do Not Start Early

- [ ] Do not expand old `Position / TradeBatch` endpoints.
- [ ] Do not redesign Dashboard as if it will remain the default homepage.
- [ ] Do not bind new pages directly to `frontend/lib/api.ts`.
- [ ] Do not migrate charts before schema-first payloads exist.
- [ ] Do not surface AI markdown blobs where evidence-linked artifacts are expected.
- [ ] Do not build a raw news feed or social sentiment terminal on the homepage.
- [ ] Do not ingest external content without source, timestamp, linking, and copyright-safe storage rules.
- [ ] Do not implement legacy TODO items without reclassifying them against this plan.
