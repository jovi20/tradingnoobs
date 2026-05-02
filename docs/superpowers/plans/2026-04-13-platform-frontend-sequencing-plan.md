# Platform Foundation & Frontend Redesign Sequencing Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align backend platform foundation delivery with the patched frontend redesign so the new timeline-first product can ship without rework on stale DTOs or deprecated trading semantics.

**Architecture:** Backend owns truth models, user-facing read contracts, and trust metadata. Frontend starts in parallel on shell, design system, and adapters, then migrates Timeline, Lifecycle Detail, Dashboard, and Insights only after the matching backend gates are complete.

**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Alembic, Redis, Next.js App Router, TypeScript, Tailwind CSS, ECharts

---

### Dev Branch Checkpoint

**Status:** Required before the next implementation slice.

**Purpose:** Keep `main` as the original baseline and make `dev` reviewable in stages instead of as one large unbounded diff.

- [ ] Record the current `dev` diff summary before more feature work.
- [ ] Run the available backend and frontend adapter tests, or record why a suite is blocked.
- [ ] Create a stage boundary commit for the current platform/frontend contract work.
- [ ] Use `git diff main...dev --stat` for high-level comparison before user evaluation.
- [ ] Use focused diffs by area for review: backend schema/auth/config, truth model, timeline/lifecycle APIs, frontend adapters/pages.

**Review Commands:**

```bash
git status --short
git diff main...dev --stat
git diff main...dev -- docs/superpowers
git diff main...dev -- backend
git diff main...dev -- frontend
```

---

### Task 1: Freeze the shared contract surface

**Status:** Contract freeze completed on `dev` branch. Implementation alignment is still partial where bridge paths are explicitly called out below.

**Outputs:**
- `TradingPosition / PositionEvent / AccountLedgerEntry / public_id / FIFO`
- User-facing meta fields: `as_of / freshness / source / maturity / value_status`
- Home contracts: `timeline feed`, `review inbox`, `context rail`
- Detail contracts: `lifecycle thread`, `evidence list`, `AI sidecar references`
- Frozen docs:
  `docs/superpowers/specs/2026-04-13-user-trust-metadata-contract.md`
  `docs/superpowers/specs/2026-04-13-timeline-review-inbox-contract.md`
  `docs/superpowers/specs/2026-04-13-lifecycle-detail-contract.md`

- [x] Freeze names and enums before schema work spreads.
- [x] Freeze the user-facing trust metadata envelope.
- [x] Freeze homepage event types and Review Inbox item shape.
- [x] Freeze lifecycle detail node types and evidence link requirements.
- [x] Record the backend gates that unlock each frontend phase.

**Exit Criteria:**
- Frontend can build adapters and trust components without guessing field shapes.
- Backend can refactor internals without breaking page contracts.

### Task 2: Ship Package 0 and Package 1 first

**Status:** Mostly done. Alembic/public_id/auth/config landed; A1/A3 tracking and observability conventions are still incomplete.

**Scope:**
- Stage 0 freeze items
- `A1`, `A2`, `A3`
- `B1`, `B2`, `B3`
- `H1`, `H4`

- [ ] Create the multi-schema baseline and schema naming guardrails from `A1`.
- [x] Make Alembic the only schema path.
- [ ] Record the expand/migrate/contract and backfill templates from `A3`.
- [x] Introduce `public_id` and auth/session tables.
- [ ] Freeze logging and error-code conventions.
- [x] Build migration and test baseline before truth-model cutover.

**Exit Criteria:**
- No more `create_all()`-driven schema drift.
- Frontend routing can assume `public_id`.
- Core changes are testable and observable.

### Task 3: Move the trading truth model before page migrations

**Status:** Bridge landed. Initial truth schema/read models and legacy sync exist, but hard cutover is not complete.

**Scope:**
- `C1`, `C2`, `C3`, `C4`, `C5`
- `D1`, `D2`, `D3`

- [ ] Replace `Position / TradeBatch` as the primary write/read semantics with `TradingPosition / PositionEvent`.
- [x] Introduce `AccountLedgerEntry` with migration, legacy realized PnL bridge, transaction cash bridge, and lifecycle `cash_effects` consumption.
- [ ] Make account cash balance/read models derive from `AccountLedgerEntry` instead of direct balance mutation.
- [ ] Centralize FIFO, fee, FX, and realized/unrealized rules after ledger cash truth exists.
- [x] Promote decision-quality fields into first-class event data.
- [ ] Put outbox, job model, and idempotency in place before derived refresh depends on them.

**Exit Criteria:**
- Frontend no longer depends on old DTO names or moving-average cost math.
- Timeline, Review Inbox, and lifecycle pages have the minimum story data they need.

### Task 4: Let frontend start in parallel, but only on stable surfaces

**Status:** In progress. Timeline-first shell and adapter layer have landed, but some pages still lean on legacy API shapes.

**Frontend may start now:**
- user/admin shell split
- navigation
- token system
- typography and number system
- primitive components
- freshness / source / sample-size UI
- adapter skeleton and mock view models

**Frontend must wait:**
- Timeline + Review Inbox waits for `Task 5`
- Lifecycle Detail waits for `Task 5` plus decision-quality data
- Dashboard + Insights waits for `Task 5` plus `Task 7`

- [x] Avoid new work on `frontend/app/page.tsx` as the product's long-term home.
- [ ] Avoid expanding `frontend/lib/api.ts` as the permanent DTO contract layer.
- [x] Land reusable trust and UI primitives before page rewrites.

**Exit Criteria:**
- The visual and system layer can move without baking in obsolete backend shapes.

### Task 5: Deliver user-facing read models before the new homepage

**Status:** Bridge landed / partial. Timeline and lifecycle contracts are live; current Timeline is legacy-derived and current Lifecycle evidence/ledger/AI sidecar are not final.

**Scope:**
- `I1`, `I2`, `I3`
- `E1`, `E2`
- `F1`, `F2`, `F4`

- [x] Publish the user-facing meta envelope.
- [x] Land a legacy-derived `timeline + review inbox` bridge for the new homepage.
- [ ] Build the final truth-backed `timeline + review inbox` read model from `TradingPosition / PositionEvent / InsightArtifact`.
- [x] Land a truth lifecycle bridge preview for single-position detail.
- [ ] Build the final `lifecycle detail + evidence` read model with ledger cash effects and AI artifact sidecar.
- [x] Tighten `/api/trading-positions/{position_public_id}/lifecycle` to public_id-only for ordinary user paths.
- [x] Implement bridge-level `cursor` / `limit` support for `/api/timeline/home`.
- [ ] Split market orchestration and stabilize provider mapping.
- [ ] Move expensive dashboard and detail reads into derived/materialized paths.

**Exit Criteria:**
- Frontend Phase 2 can ship the new homepage.
- Frontend Phase 3 can ship lifecycle detail without stitching raw endpoints.
- Dashboard and charts can consume schema-first payloads.

### Task 6: Ship pages in product order, not current code order

**Status:** In progress. Timeline is the default home through bridge data; lifecycle detail is only partially migrated.

**Page order:**
1. Timeline + Review Inbox
2. Lifecycle Detail + Rules & Checklist
3. Dashboard + Insights
4. Settings and admin polish

- [x] Make the Timeline route the default landing surface using bridge data.
- [ ] Ship the truth-backed homepage as the final default landing surface.
- [x] Let single-trade detail load `TradingPosition.public_id` lifecycle directly and render truth lifecycle as the primary narrative when available.
- [ ] Finish single-trade hard cutover by moving edit/review/batch operations from legacy `Position / TradeBatch` to truth events or labeling them as migration tools.
- [x] Keep Dashboard as macro view, not the default home.
- [ ] Keep AI as evidence-linked sidecar across surfaces.

**Exit Criteria:**
- Product center of gravity shifts from dashboard-first to timeline/review-first.
- Users can move from capture to review to learn without page-model mismatch.

### Task 7: Hold the AI and chart migrations until their contracts are real

**Status:** Not started.

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

| Frontend phase | Backend gate | Current state |
| --- | --- | --- |
| Phase 1: shell / nav / design system / trust layer | Task 1 contract freeze complete | Landed |
| Phase 2: timeline + review inbox | Task 3 core truth complete + Task 5 final timeline read model complete | Bridge route landed; final truth-backed read model pending |
| Phase 3: lifecycle detail + rules | Task 3 complete + Task 5 final lifecycle read model complete | Truth preview landed; final evidence/ledger/AI sidecar pending |
| Phase 4: dashboard + insights | Task 5 complete + AI/chart contracts from Task 7 ready | Pending |
| Phase 5: polish / secondary surfaces | Prior phases stable + ops visibility in place | Pending |

### Do Not Start Early

- [ ] Do not expand old `Position / TradeBatch` endpoints beyond explicitly labeled migration or bridge paths.
- [x] Do not redesign Dashboard as if it will remain the default homepage.
- [ ] Do not bind new pages directly to `frontend/lib/api.ts`.
- [x] Do not migrate charts before schema-first payloads exist.
- [ ] Do not surface AI markdown blobs where evidence-linked artifacts are expected.
