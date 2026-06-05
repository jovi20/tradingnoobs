# Dev P5-P7 Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next `dev` hardening wave: remove current frontend dependency security findings, safely default Timeline Home to snapshot-first, and make auditable Insight artifacts first-class detail/schema UI surfaces.

**Architecture:** Keep `dev` as the integration branch and land each stage as a separate verified commit. P5 updates dependencies without product behavior changes; P6 changes Timeline source policy behind an explicit legacy fallback switch; P7 adds artifact detail routes/pages and consumes existing schema-first chart contracts without redesigning Dashboard or Insights wholesale.

**Tech Stack:** FastAPI, SQLAlchemy, pytest/unittest, Next.js App Router, TypeScript, React Query, Tailwind CSS, Node test runner, npm audit

---

## Current Baseline

- Branch: `dev`
- Remote target: `origin/dev`
- Latest integrated commit when this plan was written: `dbffad7 docs: record dev p0 p4 completion`
- Known untouched local item: `docs/superpowers/demos/`
- P0-P4 completion commits:
  - `5c60523 docs: refresh dev p0 p4 execution plan`
  - `0c103f5 feat: harden timeline snapshot home contract`
  - `d1cbb44 feat: complete truth lifecycle detail cutover`
  - `344de3e feat: harden async job operations`
  - `c626e2c feat: prepare dashboard insights schema contracts`
  - `dbffad7 docs: record dev p0 p4 completion`
- Final P0-P4 verification:
  - `git diff --check`: clean
  - backend tests: `141 passed, 20 warnings`
  - frontend `tsc --noEmit --pretty false`: passed
  - frontend `npm run build`: passed
  - Alembic temp SQLite upgrade reached `5e6f7a8b9cad`

## Execution Rules

- Work on `dev` unless the user explicitly changes the branch target.
- Do not create a PR to `main` unless explicitly requested.
- Do not modify or remove `docs/superpowers/demos/`.
- Use TDD for behavior changes: write failing tests, observe expected failure, implement, then rerun.
- Commit and push each coherent stage boundary to `origin/dev`.
- Restore generated cache noise such as `frontend/tsconfig.tsbuildinfo` before committing.
- Treat `npm audit` as a security gate in P5. If audit findings remain after the planned non-major upgrades, stop and record the remaining advisories before broadening the dependency change.

## Design Decisions

- P5 should prefer the npm-recommended non-major Next fix path first: current audit reports `next` critical and offers `next@14.2.35` as the semver-compatible fix. The npm audit output also reports transitive `lodash`, `picomatch`, and `postcss` findings.
- P6 should make snapshot-only the default Timeline read mode, but keep a deliberate fallback flag named `timeline_legacy_mixed_feed_enabled` for emergency rollback. The older positive flag `timeline_snapshot_only_enabled` can remain supported during migration but must no longer be required for ordinary snapshot-first behavior.
- P7 should make `/insights/{artifact_public_id}` work because Timeline and Lifecycle already link to artifact-specific URLs. Backend should expose artifact-by-id through `/api/v1/insights/artifacts/{artifact_public_id}` with user isolation; frontend should add a page that renders artifact summary, evidence refs, source refs, chart schema metadata, and legacy markdown as read-only fallback.
- Dashboard schema-first UI should stay incremental: show schema/trust/empty-state metadata and keep existing charts/layout intact.

---

### Task 1: P5 Dependency Security Gate

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Test/verify: `frontend`
- Modify docs if findings remain: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

- [x] **Step 1: Capture the baseline audit**

Run:
```bash
cd frontend
npm audit --json
```

Expected current baseline:
```text
metadata.vulnerabilities.total: 4
metadata.vulnerabilities.critical: 1
metadata.vulnerabilities.high: 2
metadata.vulnerabilities.moderate: 1
next fixAvailable.version: 14.2.35
```

- [x] **Step 2: Upgrade Next on the non-major patch line**

Run:
```bash
cd frontend
npm install next@14.2.35
```

Expected:
```text
frontend/package.json updates "next" to "14.2.35" or a compatible pinned 14.2.35 value.
frontend/package-lock.json resolves next and its nested postcss chain to patched versions.
```

- [x] **Step 3: Refresh direct PostCSS if the audit still reports the direct devDependency**

Run only if `npm audit --json` still reports direct `postcss` under `vulnerabilities.postcss.nodes` including `node_modules/postcss`:
```bash
cd frontend
npm install --save-dev postcss@^8.5.10
```

Expected:
```text
Direct postcss resolves to >=8.5.10.
```

- [x] **Step 4: Apply safe transitive lockfile fixes if lodash or picomatch remain**

Run only if `npm audit --json` still reports `lodash` or `picomatch` and `fixAvailable` is `true` without semver-major package changes:
```bash
cd frontend
npm audit fix
```

Expected:
```text
package-lock.json updates vulnerable transitive packages without adding a semver-major direct dependency upgrade.
```

- [x] **Step 5: Verify dependency security result**

Run:
```bash
cd frontend
npm audit --json
```

Expected:
```text
metadata.vulnerabilities.total: 0
```

If vulnerabilities remain, stop P5 and record each remaining package, advisory URL, severity, and `fixAvailable` value in the checkpoint before asking for a dependency-risk decision.

Execution note:

- Non-major path applied `next@14.2.35`, `postcss@^8.5.10`, and non-force `npm audit fix`.
- `lodash` and `picomatch` were removed from the audit report.
- Remaining audit entries are `next` high and nested `next/node_modules/postcss` moderate.
- npm reports the only available fix as `next@16.2.7` with `isSemVerMajor: true`.
- Decision: temporarily accept the remaining semver-major-only audit risk, record it in the checkpoint, and continue P6/P7 without expanding P5 into a Next 16 / React migration.

- [ ] **Step 6: Verify frontend behavior after dependency upgrades**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

Expected:
```text
Node tests pass.
TypeScript exits 0.
Next production build exits 0.
```

- [ ] **Step 7: Verify repo hygiene**

Run:
```bash
git diff --check
git status --short
```

Expected:
```text
No whitespace errors.
Only frontend/package.json and frontend/package-lock.json are staged candidates, plus optional checkpoint notes if audit could not reach zero.
docs/superpowers/demos/ remains untracked and untouched.
```

- [ ] **Step 8: Commit and push P5**

Run:
```bash
git add frontend/package.json frontend/package-lock.json docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md
git commit -m "chore: resolve frontend dependency audit findings"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 2: P6 Timeline Snapshot-First Default Policy

**Files:**
- Modify: `backend/routers/timeline.py`
- Create or modify: `backend/services/timeline_source_policy.py`
- Test: `backend/tests/test_timeline_home_router.py`
- Test: `backend/tests/test_timeline_source_policy.py`
- Modify: `frontend/lib/adapters/timeline.ts`
- Modify: `frontend/app/timeline/page.tsx`
- Test: `frontend/tests/timeline-adapter.test.mts`

- [x] **Step 1: Add backend failing tests for snapshot-first default**

Create `backend/tests/test_timeline_source_policy.py` with:
```python
import unittest

from services.timeline_source_policy import get_timeline_source_mode


class TimelineSourcePolicyTests(unittest.TestCase):
    def test_defaults_to_snapshot_first_when_no_legacy_escape_flag_exists(self):
        self.assertEqual(get_timeline_source_mode(legacy_mixed_feed_enabled=False), "SNAPSHOT_ONLY")

    def test_legacy_escape_flag_restores_mixed_feed(self):
        self.assertEqual(get_timeline_source_mode(legacy_mixed_feed_enabled=True), "LEGACY_MIXED")
```

Also add a focused test to `backend/tests/test_timeline_home_router.py`:
```python
def test_timeline_home_defaults_to_snapshot_only_without_feature_flag(self):
    self.session.add(
        DerivedTimelineSnapshot(
            user_id=self.user.id,
            trading_position_public_id="tp-default-snapshot",
            snapshot={
                "event_public_id": "truth-event-default",
                "event_type": "OPENED",
                "occurred_at": "2026-06-05T10:00:00Z",
                "headline": "Opened AAPL",
                "summary": "Snapshot event",
                "symbol": "AAPL",
            },
            refreshed_at=datetime.now(timezone.utc),
        )
    )
    self.session.add(
        Position(
            user_id=self.user.id,
            public_id="legacy-pos-default-hidden",
            symbol="MSFT",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
        )
    )
    self.session.commit()

    response = self.client.get("/api/timeline/home")

    self.assertEqual(response.status_code, 200)
    payload = response.json()
    headlines = [
        item["headline"]
        for group in payload["data"]["timeline"]["groups"]
        for item in group["items"]
    ]
    self.assertIn("Opened AAPL", headlines)
    self.assertNotIn("MSFT", " ".join(headlines))
```

- [x] **Step 2: Run backend tests to verify RED**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_timeline_source_policy.py backend/tests/test_timeline_home_router.py -q
```

Expected:
```text
Fails because services.timeline_source_policy does not exist or Timeline still defaults to mixed legacy feed.
```

- [x] **Step 3: Implement minimal backend source policy**

Create `backend/services/timeline_source_policy.py`:
```python
from __future__ import annotations


TimelineSourceMode = str


def get_timeline_source_mode(*, legacy_mixed_feed_enabled: bool) -> TimelineSourceMode:
    return "LEGACY_MIXED" if legacy_mixed_feed_enabled else "SNAPSHOT_ONLY"
```

Modify `backend/routers/timeline.py`:
```python
from services.timeline_source_policy import get_timeline_source_mode
```

Replace the existing `snapshot_only_enabled = get_feature_flag_enabled(...)` decision with:
```python
legacy_mixed_feed_enabled = get_feature_flag_enabled(
    db,
    "timeline_legacy_mixed_feed_enabled",
    actor_key=current_user.public_id,
)
snapshot_only_enabled = (
    get_timeline_source_mode(legacy_mixed_feed_enabled=legacy_mixed_feed_enabled) == "SNAPSHOT_ONLY"
)
```

Keep the older `timeline_snapshot_only_enabled` tests only if they are explicitly rewritten as legacy compatibility tests; new default behavior must not require that flag.

- [x] **Step 4: Run backend tests to verify GREEN**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_timeline_source_policy.py backend/tests/test_timeline_home_router.py -q
```

Expected:
```text
All selected tests pass.
```

- [x] **Step 5: Add frontend failing test for snapshot-first source badge copy**

Modify `frontend/tests/timeline-adapter.test.mts`:
```ts
import { getTimelineSourceModeLabel } from '../lib/adapters/timeline.ts'

test('timeline source mode labels snapshot-first default clearly', () => {
  assert.equal(getTimelineSourceModeLabel('SNAPSHOT_ONLY'), 'Snapshot-first')
  assert.equal(getTimelineSourceModeLabel('LEGACY_MIXED'), 'Legacy mixed fallback')
})
```

- [x] **Step 6: Run frontend test to verify RED**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/timeline-adapter.test.mts
```

Expected:
```text
Fails because getTimelineSourceModeLabel is not exported.
```

- [x] **Step 7: Implement minimal frontend copy**

Modify `frontend/lib/adapters/timeline.ts`:
```ts
export type TimelineSourceMode = 'SNAPSHOT_ONLY' | 'LEGACY_MIXED'

export function getTimelineSourceModeLabel(mode: TimelineSourceMode) {
    if (mode === 'LEGACY_MIXED') return 'Legacy mixed fallback'
    return 'Snapshot-first'
}
```

Modify `frontend/app/timeline/page.tsx` only if the backend response exposes mode metadata in this slice. If mode metadata is not added to the API response, do not invent page state; keep this adapter helper as the copy contract for a later metadata display slice.

- [x] **Step 8: Verify P6**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_timeline_source_policy.py backend/tests/test_timeline_home_router.py backend/tests/test_derived_timeline_read_service.py -q
cd frontend
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

Expected:
```text
Backend selected tests pass.
Frontend Node tests pass.
TypeScript exits 0.
Build exits 0.
```

Execution note:

- RED observed for missing `services.timeline_source_policy`, default mixed feed still surfacing `MSFT`, and missing frontend `getTimelineSourceModeLabel` export.
- GREEN observed with `timeline_legacy_mixed_feed_enabled` as the explicit mixed-feed rollback flag.
- Existing legacy mixed-feed router tests now opt into `timeline_legacy_mixed_feed_enabled`; default tests no longer require `timeline_snapshot_only_enabled`.

- [ ] **Step 9: Commit and push P6**

Run:
```bash
git add backend/routers/timeline.py backend/services/timeline_source_policy.py backend/tests/test_timeline_source_policy.py backend/tests/test_timeline_home_router.py frontend/lib/adapters/timeline.ts frontend/tests/timeline-adapter.test.mts frontend/app/timeline/page.tsx
git commit -m "feat: default timeline home to snapshot source"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 3: P7 Insight Artifact Detail API

**Files:**
- Modify: `backend/services/insight_artifact_service.py`
- Modify: `backend/routers/insight_artifacts.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_insight_artifacts_api.py`
- Test: `backend/tests/test_insight_artifact_service.py`
- Modify: `frontend/lib/insightArtifactClient.ts`
- Create: `frontend/hooks/useInsightArtifact.ts`
- Test: `frontend/tests/insight-artifact-client.test.mts`

- [ ] **Step 1: Add backend failing tests for artifact-by-id read**

Modify `backend/tests/test_insight_artifact_service.py`:
```python
def test_get_artifact_by_public_id_is_user_scoped(self):
    service = InsightArtifactService(self.db)
    run = service.start_run(
        user_id=self.user.id,
        run_type="analysis.strategy_health",
        prompt_version="v1",
        input_refs=["analysis:strategy_health"],
    )
    artifact = service.add_artifact(
        run_public_id=run.public_id,
        artifact_type="analysis_card",
        title="Strategy health",
        summary="Average loss needs work.",
        content_markdown="# Legacy body",
        payload={"linked_surface": "insights"},
        evidence_refs=["analysis:strategy_health"],
        chart_schema={"schema_version": "chart.v1", "chart_type": "bar", "series": [{"field": "avg_pnl", "label": "Average PnL"}]},
        trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": ["dataset:positions"]},
    )
    service.complete_run(run_public_id=run.public_id)

    payload = service.get_artifact(user_id=self.user.id, artifact_public_id=artifact.public_id)

    self.assertEqual(payload["public_id"], artifact.public_id)
    self.assertEqual(payload["run"]["public_id"], run.public_id)
    self.assertEqual(payload["summary"], "Average loss needs work.")
```

Modify `backend/tests/test_insight_artifacts_api.py`:
```python
def test_get_insight_artifact_detail(self):
    service = InsightArtifactService(self.db)
    run = service.start_run(user_id=self.user.id, run_type="analysis.strategy_health", prompt_version="v1", input_refs=[])
    artifact = service.add_artifact(
        run_public_id=run.public_id,
        artifact_type="analysis_card",
        title="Strategy health",
        summary="Average loss needs work.",
        content_markdown=None,
        payload={"linked_surface": "insights"},
        evidence_refs=["analysis:strategy_health"],
        chart_schema=None,
        trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": ["dataset:positions"]},
    )
    service.complete_run(run_public_id=run.public_id)

    response = self.client.get(f"/api/v1/insights/artifacts/{artifact.public_id}")

    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.json()["public_id"], artifact.public_id)
```

- [ ] **Step 2: Run backend tests to verify RED**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_insight_artifact_service.py backend/tests/test_insight_artifacts_api.py -q
```

Expected:
```text
Fails because get_artifact and /api/v1/insights/artifacts/{artifact_public_id} do not exist.
```

- [ ] **Step 3: Implement backend artifact detail**

Modify `backend/services/insight_artifact_service.py`:
```python
    def get_artifact(self, *, user_id: int, artifact_public_id: str) -> dict:
        artifact = (
            self.db.query(InsightArtifact)
            .join(InsightRun)
            .filter(InsightRun.user_id == user_id, InsightArtifact.public_id == artifact_public_id)
            .one()
        )
        payload = self._artifact_dict(artifact)
        payload["run"] = {
            "public_id": artifact.run.public_id,
            "run_type": artifact.run.run_type,
            "status": artifact.run.status,
            "prompt_version": artifact.run.prompt_version,
            "input_refs": artifact.run.input_refs or [],
            "started_at": artifact.run.started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": artifact.run.completed_at.isoformat().replace("+00:00", "Z") if artifact.run.completed_at else None,
            "error_code": artifact.run.error_code,
            "error_message": artifact.run.error_message,
        }
        return payload
```

Modify `backend/routers/insight_artifacts.py`:
```python
artifact_router = APIRouter(prefix="/api/v1/insights/artifacts", tags=["Insight Artifacts"])


@artifact_router.get("/{artifact_public_id}")
def get_insight_artifact(
    artifact_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InsightArtifactService(db).get_artifact(
            user_id=current_user.id,
            artifact_public_id=artifact_public_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Insight artifact not found") from exc
```

Modify `backend/main.py` after the existing insight run router include:
```python
app.include_router(insight_artifacts.router)
app.include_router(insight_artifacts.artifact_router)
```

- [ ] **Step 4: Verify backend GREEN**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_insight_artifact_service.py backend/tests/test_insight_artifacts_api.py -q
```

Expected:
```text
All selected tests pass.
```

- [ ] **Step 5: Add frontend client failing test**

Create `frontend/tests/insight-artifact-client.test.mts`:
```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  insightArtifactDetailPath,
  insightArtifactsAPI,
} from '../lib/insightArtifactClient.ts'

test('insight artifact client builds artifact detail path', () => {
  assert.equal(insightArtifactDetailPath('artifact-1'), '/api/v1/insights/artifacts/artifact-1')
})

test('insight artifact client fetches artifact detail', async () => {
  const originalFetch = globalThis.fetch
  const calls: string[] = []
  globalThis.fetch = async (input: RequestInfo | URL) => {
    calls.push(String(input))
    return new Response(JSON.stringify({ public_id: 'artifact-1', run: { public_id: 'run-1' } }), { status: 200 })
  }

  try {
    const result = await insightArtifactsAPI.getArtifact('token-1', 'artifact-1')
    assert.equal(result.public_id, 'artifact-1')
    assert.match(calls[0], /\/api\/v1\/insights\/artifacts\/artifact-1$/)
  } finally {
    globalThis.fetch = originalFetch
  }
})
```

- [ ] **Step 6: Run frontend client test to verify RED**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/insight-artifact-client.test.mts
```

Expected:
```text
Fails because insightArtifactDetailPath and getArtifact are not exported.
```

- [ ] **Step 7: Implement frontend client and hook**

Modify `frontend/lib/insightArtifacts.ts`:
```ts
export interface InsightArtifactDetail extends InsightArtifact {
    run: Omit<InsightRun, 'artifacts'>
}
```

Modify `frontend/lib/insightArtifactClient.ts`:
```ts
import type { InsightArtifactDetail, InsightRun } from '@/lib/insightArtifacts'

export const insightArtifactDetailPath = (artifactPublicId: string) =>
    `/api/v1/insights/artifacts/${artifactPublicId}` as const

export const insightArtifactsAPI = {
    listRuns: (token: string) => fetchInsightArtifact<InsightRun[]>(insightRunsPath, token),
    getRun: (token: string, runPublicId: string) =>
        fetchInsightArtifact<InsightRun>(insightRunDetailPath(runPublicId), token),
    getArtifact: (token: string, artifactPublicId: string) =>
        fetchInsightArtifact<InsightArtifactDetail>(insightArtifactDetailPath(artifactPublicId), token),
}
```

Create `frontend/hooks/useInsightArtifact.ts`:
```ts
import { useQuery } from '@tanstack/react-query'

import { insightArtifactsAPI } from '@/lib/insightArtifactClient'
import type { InsightArtifactDetail } from '@/lib/insightArtifacts'

export function useInsightArtifact(token: string | null, artifactPublicId: string | null) {
    return useQuery<InsightArtifactDetail, Error>({
        queryKey: ['insights', 'artifacts', artifactPublicId, token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            if (!artifactPublicId) throw new Error('No artifact id')
            return insightArtifactsAPI.getArtifact(token, artifactPublicId)
        },
        enabled: !!token && !!artifactPublicId,
        staleTime: 30 * 1000,
    })
}
```

- [ ] **Step 8: Verify P7 API/client**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_insight_artifact_service.py backend/tests/test_insight_artifacts_api.py -q
cd frontend
node --experimental-strip-types --test tests/insight-artifact-client.test.mts tests/insight-artifact-presentation.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
Selected backend tests pass.
Selected frontend tests pass.
TypeScript exits 0.
```

- [ ] **Step 9: Commit and push P7 API/client**

Run:
```bash
git add backend/services/insight_artifact_service.py backend/routers/insight_artifacts.py backend/main.py backend/tests/test_insight_artifact_service.py backend/tests/test_insight_artifacts_api.py frontend/lib/insightArtifacts.ts frontend/lib/insightArtifactClient.ts frontend/hooks/useInsightArtifact.ts frontend/tests/insight-artifact-client.test.mts
git commit -m "feat: expose auditable insight artifact details"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 4: P7 Insight Artifact Detail Page and Dashboard Schema UI

**Files:**
- Create: `frontend/app/insights/[artifactId]/page.tsx`
- Create: `frontend/components/insights/InsightArtifactDetailCard.tsx`
- Modify: `frontend/components/insights/EvidenceLinkedInsightSidecar.tsx`
- Modify: `frontend/components/dashboard/domain/DashboardAllocationPanel.tsx`
- Test: `frontend/tests/insight-artifact-presentation.test.mts`
- Test: `frontend/tests/dashboard-adapter.test.mts`

- [ ] **Step 1: Add frontend failing tests for detail view model**

Modify `frontend/tests/insight-artifact-presentation.test.mts`:
```ts
import { buildInsightArtifactDetailView } from '../lib/insightArtifacts.ts'

test('insight artifact detail view keeps summary primary and legacy markdown read-only', () => {
  const view = buildInsightArtifactDetailView({
    public_id: 'artifact-1',
    artifact_type: 'analysis_card',
    title: 'Strategy health',
    summary: 'Average loss still needs work.',
    content_markdown: '# Legacy markdown',
    payload: { linked_surface: 'insights' },
    evidence_refs: ['analysis:strategy_health'],
    chart_schema: { schema_version: 'chart.v1', chart_type: 'bar', series: [{ field: 'avg_pnl', label: 'Average PnL' }] },
    trust_meta: { freshness: 'FRESH', source: 'AI_GENERATED', source_refs: ['dataset:positions'] },
    run: {
      public_id: 'run-1',
      run_type: 'analysis.strategy_health',
      status: 'COMPLETED',
      prompt_version: 'v1',
      input_refs: ['analysis:strategy_health'],
      started_at: '2026-06-05T00:00:00Z',
      completed_at: '2026-06-05T00:01:00Z',
      error_code: null,
      error_message: null,
    },
  })

  assert.equal(view.primaryContent, 'Average loss still needs work.')
  assert.equal(view.legacyReadOnlyContent, '# Legacy markdown')
  assert.equal(view.chartBadge, 'chart.v1 · bar')
  assert.deepEqual(view.evidenceRefs, ['analysis:strategy_health'])
  assert.deepEqual(view.sourceRefs, ['dataset:positions'])
})
```

- [ ] **Step 2: Run test to verify RED**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/insight-artifact-presentation.test.mts
```

Expected:
```text
Fails because buildInsightArtifactDetailView is not exported.
```

- [ ] **Step 3: Implement detail view model**

Modify `frontend/lib/insightArtifacts.ts`:
```ts
export function buildInsightArtifactDetailView(artifact: InsightArtifactDetail) {
    return {
        title: artifact.title,
        artifactType: artifact.artifact_type,
        runType: artifact.run.run_type,
        primaryContent: artifact.summary,
        legacyReadOnlyContent: artifact.content_markdown,
        evidenceRefs: artifact.evidence_refs ?? [],
        sourceRefs: artifact.trust_meta.source_refs ?? [],
        chartBadge: assertSupportedChartSchema(artifact.chart_schema)
            ? `${artifact.chart_schema?.schema_version} · ${artifact.chart_schema?.chart_type}`
            : null,
        trustMeta: artifact.trust_meta,
        createdAt: artifact.created_at,
    }
}
```

- [ ] **Step 4: Create detail component and page**

Create `frontend/components/insights/InsightArtifactDetailCard.tsx`:
```tsx
import { ShieldCheck, Sparkles } from 'lucide-react'

import { buildInsightArtifactDetailView, type InsightArtifactDetail } from '@/lib/insightArtifacts'

export function InsightArtifactDetailCard({ artifact }: { artifact: InsightArtifactDetail }) {
    const view = buildInsightArtifactDetailView(artifact)
    return (
        <div className="card p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{view.artifactType}</p>
            <h1 className="mt-2 text-2xl font-bold">{view.title}</h1>
            <p className="mt-2 text-sm text-slate-500">{view.runType}</p>
            <p className="mt-5 text-base leading-7 text-slate-700 dark:text-slate-200">{view.primaryContent}</p>
            {view.chartBadge && (
                <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    {view.chartBadge}
                </div>
            )}
            {view.evidenceRefs.length > 0 && (
                <div className="mt-5 flex flex-wrap gap-2">
                    {view.evidenceRefs.map((ref) => (
                        <span key={ref} className="rounded-full border border-slate-200 px-2.5 py-1 text-xs text-slate-500 dark:border-slate-700">{ref}</span>
                    ))}
                </div>
            )}
            {view.sourceRefs.length > 0 && (
                <p className="mt-4 text-xs text-slate-400">source refs: {view.sourceRefs.join(', ')}</p>
            )}
            {view.legacyReadOnlyContent && (
                <div className="mt-6 rounded-xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-500/20 dark:bg-amber-500/10">
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-700 dark:text-amber-200">
                        Legacy read-only markdown
                    </p>
                    <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-700 dark:text-slate-200">
                        {view.legacyReadOnlyContent}
                    </pre>
                </div>
            )}
        </div>
    )
}
```

Create `frontend/app/insights/[artifactId]/page.tsx`:
```tsx
'use client'

import Link from 'next/link'
import { Loader2 } from 'lucide-react'

import { InsightArtifactDetailCard } from '@/components/insights/InsightArtifactDetailCard'
import { useAuth } from '@/contexts/AuthContext'
import { useInsightArtifact } from '@/hooks/useInsightArtifact'

export default function InsightArtifactDetailPage({ params }: { params: { artifactId: string } }) {
    const { token } = useAuth()
    const query = useInsightArtifact(token, params.artifactId)

    if (query.isLoading) {
        return <div className="flex items-center justify-center py-20"><Loader2 className="h-8 w-8 animate-spin text-primary-500" /></div>
    }

    if (query.error || !query.data) {
        return (
            <div className="card p-8 text-center">
                <p className="text-sm text-slate-500">Insight artifact not found.</p>
                <Link href="/insights" className="mt-4 inline-flex text-sm font-semibold text-primary-600">Back to insights</Link>
            </div>
        )
    }

    return (
        <div className="space-y-4 pb-20 md:pb-6">
            <Link href="/insights" className="text-sm font-semibold text-primary-600">Back to insights</Link>
            <InsightArtifactDetailCard artifact={query.data} />
        </div>
    )
}
```

- [ ] **Step 5: Add dashboard schema metadata test**

Modify `frontend/tests/dashboard-adapter.test.mts`:
```ts
import { getDashboardAllocationChart } from '../lib/adapters/dashboard.ts'

test('dashboard allocation chart exposes trust and empty state from schema payload', () => {
  const stats = {
    core_type_allocation: [],
    market_allocation: [],
    risk_level_allocation: [],
    chart_payloads: {
      core_type: {
        chart_schema: { schema_version: 'chart.v1', chart_type: 'bar', data_path: 'core_type_allocation', series: [{ field: 'value', label: 'Value' }] },
        data: [],
        empty_state: { is_empty: true, reason: 'NO_ALLOCATION_DATA' },
        trust_meta: { freshness: 'FRESH', source: 'DASHBOARD_DERIVED_READ_MODEL', source_refs: ['dashboard:stats'] },
      },
    },
  }

  const chart = getDashboardAllocationChart(stats, 'CORE_TYPE')
  assert.equal(chart.isEmpty, true)
  assert.equal(chart.emptyState.reason, 'NO_ALLOCATION_DATA')
  assert.equal(chart.trustMeta.source, 'DASHBOARD_DERIVED_READ_MODEL')
})
```

- [ ] **Step 6: Show dashboard schema/trust metadata without changing chart layout**

Modify `frontend/components/dashboard/domain/DashboardAllocationPanel.tsx` props:
```ts
import type { DashboardAllocationChartView } from '@/lib/chartSchemas'

interface DashboardAllocationPanelProps {
    allocationDimension: 'CORE_TYPE' | 'MARKET' | 'RISK'
    onChangeDimension: (value: 'CORE_TYPE' | 'MARKET' | 'RISK') => void
    data: AssetAllocation[]
    chart?: DashboardAllocationChartView
}
```

Render below the title:
```tsx
{chart?.schema && (
    <p className="text-[11px] text-slate-400">
        {chart.schema.schema_version} · {chart.schema.chart_type}
        {chart.trustMeta.source ? ` · ${chart.trustMeta.source}` : ''}
    </p>
)}
```

Modify `frontend/app/dashboard/page.tsx` call:
```tsx
<DashboardAllocationPanel
    allocationDimension={allocationDimension}
    onChangeDimension={setAllocationDimension}
    data={getDashboardAllocationData(stats, allocationDimension)}
    chart={getDashboardAllocationChart(stats, allocationDimension)}
/>
```

- [ ] **Step 7: Verify P7 UI**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

Expected:
```text
Frontend Node tests pass.
TypeScript exits 0.
Build exits 0 and includes /insights/[artifactId].
```

- [ ] **Step 8: Commit and push P7 UI**

Run:
```bash
git add frontend/app/insights/[artifactId]/page.tsx frontend/components/insights/InsightArtifactDetailCard.tsx frontend/components/insights/EvidenceLinkedInsightSidecar.tsx frontend/components/dashboard/domain/DashboardAllocationPanel.tsx frontend/app/dashboard/page.tsx frontend/lib/insightArtifacts.ts frontend/tests/insight-artifact-presentation.test.mts frontend/tests/dashboard-adapter.test.mts
git commit -m "feat: add auditable insight artifact detail UI"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 5: Final P5-P7 Verification and Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-05-dev-p5-p7-execution-plan.md`
- Modify: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

- [ ] **Step 1: Run final verification**

Run:
```bash
git diff --check
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests -q
cd frontend
npm audit --json
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
PYTHONPATH=backend DATABASE_URL=sqlite:////private/tmp/tradingnoobs_dev_p5_p7_final.db /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

Expected:
```text
git diff --check exits 0.
Backend tests pass.
npm audit reports 0 vulnerabilities or the checkpoint records each accepted remaining advisory.
Frontend Node tests pass.
TypeScript exits 0.
Build exits 0.
Alembic reaches head.
```

- [ ] **Step 2: Update checkpoint and this plan**

Record:
```text
P5 dependency security commit SHA and audit result.
P6 Timeline snapshot-first default commit SHA and fallback flag name.
P7 Insight artifact detail/API/UI commit SHAs.
Exact final verification commands and results.
Remaining migration-only paths.
docs/superpowers/demos/ untouched status.
```

- [ ] **Step 3: Commit and push final docs**

Run:
```bash
git add docs/superpowers/plans/2026-06-05-dev-p5-p7-execution-plan.md docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md
git commit -m "docs: record dev p5 p7 execution plan"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

## Known External References

- Next.js security update notice from npm install output points to `https://nextjs.org/blog/security-update-2025-12-11`; current npm audit recommends `next@14.2.35` as the non-major fix path for this app.
- Current npm audit advisory URLs include GitHub advisories for `next`, `postcss`, `lodash`, and `picomatch`; the P5 task must use live `npm audit --json` output as the source of truth at execution time.

## Self-Review Notes

- Scope is split into independently testable stage commits: dependency security, Timeline source default, artifact detail API/client, artifact/detail/schema UI, and final docs.
- No step requires touching `docs/superpowers/demos/`.
- Timeline default change has an explicit rollback flag: `timeline_legacy_mixed_feed_enabled`.
- Insight artifact detail route matches existing Timeline/Lifecycle href shape `/insights/{artifact_public_id}`.
- Dashboard schema-first work is intentionally limited to metadata display and existing adapter consumption, not a dashboard redesign.
