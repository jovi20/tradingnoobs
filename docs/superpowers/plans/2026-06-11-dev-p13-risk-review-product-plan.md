# P13 Risk Review Product Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-class portfolio risk monitor that turns truth/ledger data into daily-loss warnings, concentration alerts, and actionable Dashboard / Timeline / Review Inbox surfaces.

**Architecture:** Keep risk computation in a dedicated backend service instead of growing Dashboard route logic. The service produces a stable risk read model consumed by `/api/risk/summary`, Dashboard, and Timeline/Review Inbox; V1 uses in-app polling-compatible alert cards rather than WebSocket/SSE so the product value lands before realtime transport complexity.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, existing truth trading models, existing ledger read model, Next.js 16, React 19, TypeScript, Node test runner.

---

## Scope And Defaults

P13 ships product risk visibility, not broker-grade VaR.

Default V1 thresholds:
- Daily loss warning: equity change <= `-3%`.
- Daily loss critical: equity change <= `-5%`.
- Single-symbol concentration warning: exposure >= `35%` of gross portfolio value.
- Single-symbol concentration critical: exposure >= `50%` of gross portfolio value.
- Drawdown warning: max drawdown >= `12%`.
- Drawdown critical: max drawdown >= `25%`.

Data source rule:
- Prefer `TradingPosition`, `PositionEvent`, and `AccountLedgerEntry`.
- Use legacy `Position` only where Dashboard still uses it for open-position valuation.
- Risk alerts must include trust metadata explaining whether values are final, estimated, or degraded.

## Files Likely To Touch

Backend:
- Create: `backend/services/risk_alert_service.py`
- Create: `backend/routers/risk.py`
- Modify: `backend/main.py`
- Modify: `backend/schemas.py`
- Modify: `backend/routers/dashboard.py`
- Modify: `backend/routers/timeline.py`
- Test: `backend/tests/test_risk_alert_service.py`
- Test: `backend/tests/test_risk_router.py`
- Test: `backend/tests/test_timeline_home_router.py`
- Test: `backend/tests/test_openapi_contracts.py`

Frontend:
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/lib/read-models.ts`
- Modify: `frontend/lib/adapters/dashboard.ts`
- Modify: `frontend/lib/adapters/timeline-workbench.ts`
- Modify: `frontend/components/dashboard/workbench/DashboardRiskRail.tsx`
- Modify: `frontend/components/timeline/workbench/ReviewInboxPanel.tsx`
- Create: `frontend/components/risk/RiskAlertStack.tsx`
- Test: `frontend/tests/dashboard-adapter.test.mts`
- Test: `frontend/tests/timeline-workbench.test.mts`
- Create: `frontend/tests/risk-alerts.test.mts`

Docs:
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p13-risk-review-product-plan.md`

## Risk Contract

Backend response shape for `GET /api/risk/summary`:

```json
{
  "as_of": "2026-06-11T10:30:00Z",
  "base_currency": "USD",
  "portfolio": {
    "gross_exposure": 100000.0,
    "net_liquidation_value": 86000.0,
    "daily_pnl": -3200.0,
    "daily_pnl_percent": -3.72,
    "max_drawdown": 0.13
  },
  "alerts": [
    {
      "public_id": "risk:daily_loss:2026-06-11",
      "kind": "DAILY_LOSS_LIMIT",
      "severity": "WARNING",
      "summary": "今日亏损已达到 -3.72%",
      "reason": "Daily equity change crossed the -3% warning threshold.",
      "recommended_action": {
        "kind": "OPEN_DASHBOARD",
        "label": "查看组合风险",
        "href": "/dashboard"
      },
      "source_refs": ["daily_snapshot:2026-06-10", "dashboard:stats"],
      "trust": {
        "freshness": "FRESH",
        "source": "DERIVED",
        "value_status": "ESTIMATED"
      }
    }
  ],
  "trust": {
    "freshness": "FRESH",
    "source": "DERIVED",
    "source_refs": ["TradingPosition", "AccountLedgerEntry", "DailySnapshot"]
  }
}
```

## Task 1: Add Risk Read Model Service

**Goal:** compute deterministic risk summary and alerts without touching UI.

- [ ] Write failing unit tests in `backend/tests/test_risk_alert_service.py`:
  - `test_daily_loss_warning_crosses_three_percent_threshold`
  - `test_daily_loss_critical_crosses_five_percent_threshold`
  - `test_symbol_concentration_alert_uses_gross_exposure`
  - `test_no_alerts_for_empty_portfolio_returns_fresh_empty_summary`
- [ ] Run targeted test and confirm RED:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_risk_alert_service.py
```

Expected: import failure for `services.risk_alert_service`.

- [ ] Create `backend/services/risk_alert_service.py` with:
  - `RiskAlertSeverity = Literal["INFO", "NOTICE", "WARNING", "CRITICAL"]`
  - `RiskAlertKind = Literal["DAILY_LOSS_LIMIT", "CONCENTRATION", "DRAWDOWN", "DATA_STALE"]`
  - `RiskThresholds` dataclass containing the default thresholds listed above.
  - `build_portfolio_risk_summary(db, user_id, as_of=None, thresholds=None)`.
  - Pure helpers for daily loss percent, concentration, and drawdown classification.
- [ ] Run targeted test and confirm GREEN.
- [ ] Commit:

```bash
git add backend/services/risk_alert_service.py backend/tests/test_risk_alert_service.py
git commit -m "feat: add portfolio risk alert service"
```

## Task 2: Add Risk API Contract

**Goal:** expose risk summary through a stable endpoint and OpenAPI snapshot.

- [ ] Add Pydantic models in `backend/schemas.py`:
  - `RiskRecommendedAction`
  - `RiskTrustMeta`
  - `RiskAlert`
  - `RiskPortfolioSummary`
  - `RiskSummaryResponse`
- [ ] Create `backend/routers/risk.py` with `GET /api/risk/summary`.
- [ ] Register the router in `backend/main.py`.
- [ ] Add `backend/tests/test_risk_router.py` covering:
  - authenticated user can fetch `alerts` and `portfolio`.
  - unauthenticated request returns `401`.
  - response includes stable `trust.source_refs`.
- [ ] Extend `backend/tests/test_openapi_contracts.py` to assert `/api/risk/summary` exists.
- [ ] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_risk_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

- [ ] Commit:

```bash
git add backend/routers/risk.py backend/main.py backend/schemas.py backend/tests/test_risk_router.py backend/tests/test_openapi_contracts.py
git commit -m "feat: expose portfolio risk summary api"
```

## Task 3: Feed Risk Alerts Into Dashboard

**Goal:** Dashboard shows a concrete risk stack instead of only ratio tiles.

- [ ] Extend `DashboardStats` in `backend/schemas.py` with `risk_summary: Optional[RiskSummaryResponse]`.
- [ ] In `backend/routers/dashboard.py`, call `build_portfolio_risk_summary(...)` after portfolio totals are calculated and attach it to the response.
- [ ] Add backend regression in `backend/tests/test_risk_router.py` or `backend/tests/test_router_platform_config_usage.py` verifying `/api/dashboard/stats` contains `risk_summary.alerts`.
- [ ] Extend frontend `DashboardStats` in `frontend/lib/api.ts` and read-model types in `frontend/lib/read-models.ts`.
- [ ] Update `frontend/lib/adapters/dashboard.ts` so `adaptDashboardPageData(...)` returns `riskAlerts` and a stronger `riskPosture` when a critical risk alert exists.
- [ ] Create `frontend/components/risk/RiskAlertStack.tsx`.
- [ ] Render `RiskAlertStack` inside `frontend/components/dashboard/workbench/DashboardRiskRail.tsx`.
- [ ] Add frontend tests:
  - `frontend/tests/dashboard-adapter.test.mts` covers critical alert overriding posture.
  - `frontend/tests/risk-alerts.test.mts` covers severity labels and href mapping.
- [ ] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts tests/risk-alerts.test.mts
```

- [ ] Commit:

```bash
git add backend/routers/dashboard.py backend/schemas.py backend/tests/test_risk_router.py frontend/lib/api.ts frontend/lib/read-models.ts frontend/lib/adapters/dashboard.ts frontend/components/risk/RiskAlertStack.tsx frontend/components/dashboard/workbench/DashboardRiskRail.tsx frontend/tests/dashboard-adapter.test.mts frontend/tests/risk-alerts.test.mts
git commit -m "feat: surface risk alerts on dashboard"
```

## Task 4: Feed Risk Alerts Into Timeline And Review Inbox

**Goal:** risk warnings become action cards in the user's default time-flow surface.

- [ ] Extend `ReviewInboxKindEnum` in `backend/schemas.py` with:
  - `DAILY_LOSS_LIMIT`
  - `PORTFOLIO_CONCENTRATION`
  - `DRAWDOWN_ALERT`
- [ ] Extend `RecommendedActionKindEnum` with `OPEN_DASHBOARD`.
- [ ] In `backend/routers/timeline.py`, append risk alerts from `build_portfolio_risk_summary(...)` into `ReviewInbox.items`.
- [ ] Increment `SummaryBar.priority_alert_count` with critical and warning risk items.
- [ ] Add tests in `backend/tests/test_timeline_home_router.py`:
  - daily loss alert appears in review inbox.
  - `view=EXCEPTION` includes risk alert timeline event or inbox count.
  - no risk alert is produced for zero portfolio.
- [ ] Update `frontend/lib/adapters/timeline-workbench.ts` tone mapping for new risk kinds.
- [ ] Update `frontend/components/timeline/workbench/ReviewInboxPanel.tsx` labels to show risk-specific copy.
- [ ] Add frontend regression in `frontend/tests/timeline-workbench.test.mts`.
- [ ] Run:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
cd ../frontend
node --experimental-strip-types --test tests/timeline-workbench.test.mts
```

- [ ] Commit:

```bash
git add backend/routers/timeline.py backend/schemas.py backend/tests/test_timeline_home_router.py frontend/lib/adapters/timeline-workbench.ts frontend/components/timeline/workbench/ReviewInboxPanel.tsx frontend/tests/timeline-workbench.test.mts
git commit -m "feat: add risk action cards to timeline"
```

## Task 5: P13 Completion Gate

- [ ] Backend risk tests pass.
- [ ] Timeline and dashboard targeted tests pass.
- [ ] Full backend tests pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend lint passes.
- [ ] Frontend Node tests pass.
- [ ] Browser smoke covers authenticated `/dashboard` and `/timeline`.
- [ ] `docs/TODO.md` marks P13 completed and P14 as the next planned lane.

Final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```

## Stop Conditions

- Stop before adding WebSocket or SSE transport; V1 alert delivery is API/read-model based.
- Stop before making risk thresholds user-editable; default thresholds are enough for P13.
- Stop before claiming broker-grade risk or margin accuracy.
- Stop if risk math requires external market data beyond currently available Dashboard valuation.
