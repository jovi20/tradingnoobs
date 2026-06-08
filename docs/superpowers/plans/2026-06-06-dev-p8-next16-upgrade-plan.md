# Dev P8 Next 16 Security Upgrade Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the accepted P5 residual frontend audit findings by upgrading the frontend to Next.js 16 and the matching React 19 line without changing product behavior.

**Architecture:** Keep this as a dedicated `dev` hardening stage because it is a semver-major framework migration, not a normal patch. Use the npm audit recommended Next 16 fix path, migrate App Router dynamic params to the async request API shape, keep the current visual/product behavior unchanged, and land verification plus checkpoint docs as separate commits.

**Tech Stack:** Next.js 16, React 19, TypeScript, App Router, React Query, Tailwind CSS, Node test runner, npm audit

---

## Current Baseline

- Branch target: `dev`
- Remote target: `origin/dev`
- Latest P5-P7 completion commit: `347e810 docs: record dev p5 p7 execution plan`
- Current frontend framework dependencies:
  - `next`: `^14.2.35`
  - `react`: `^18.2.0`
  - `react-dom`: `^18.2.0`
  - `@types/react`: `^18`
  - `@types/react-dom`: `^18`
- Accepted residual audit findings from P5:
  - `next` high
  - nested `next/node_modules/postcss` moderate
  - npm reports `fixAvailable.version: 16.2.7` and `isSemVerMajor: true`
- Known untouched local item: `docs/superpowers/demos/`

## Official Upgrade Constraints

- Next.js 16 requires Node.js `20.9.0+`.
- Next.js 16 uses Turbopack by default for `next dev` and `next build`.
- Next.js 16 removes synchronous compatibility for request-time APIs, including `params` and `searchParams` in App Router pages.
- Next.js 16 codemod/manual path upgrades `next`, `react`, `react-dom`, `@types/react`, and `@types/react-dom`.
- Next.js 16 removes the old `next lint` flow in favor of ESLint CLI migration.

## Execution Rules

- Work on `dev` unless the user explicitly changes the branch target.
- Do not create a PR to `main` unless explicitly requested.
- Do not modify or remove `docs/superpowers/demos/`.
- Restore generated cache noise such as `frontend/next-env.d.ts` and `frontend/tsconfig.tsbuildinfo` before committing.
- Treat any product behavior change as out of scope unless a failing migration test requires it.
- If `npm audit` still reports vulnerable Next/PostCSS findings after Next 16, stop and record the new audit state before broadening scope again.

---

### Task 1: Baseline and Compatibility Scan

**Files:**
- Modify: `docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md`
- Test/verify: `frontend`

- [x] **Step 1: Verify runtime and current clean state**

Run:
```bash
node --version
git status --short --branch
```

Expected:
```text
Node version is >=20.9.0.
dev is aligned with origin/dev.
Only docs/superpowers/demos/ may appear as untracked local user content.
```

- [x] **Step 2: Capture pre-upgrade audit**

Run:
```bash
cd frontend
npm audit --json
```

Expected:
```text
metadata.vulnerabilities.total: 2
vulnerabilities.next.fixAvailable.version: 16.2.7
vulnerabilities.next.fixAvailable.isSemVerMajor: true
vulnerabilities.postcss.nodes includes node_modules/next/node_modules/postcss
```

- [x] **Step 3: Capture pre-upgrade frontend verification**

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
Next 14 production build exits 0.
Build output includes /insights/[artifactId].
```

- [x] **Step 4: Confirm dynamic route files requiring async params review**

Run:
```bash
find frontend/app -path '*[*]*' -name page.tsx -print
```

Expected dynamic pages to review:
```text
frontend/app/insights/[artifactId]/page.tsx
frontend/app/positions/[id]/page.tsx
frontend/app/positions/[id]/add-batch/page.tsx
frontend/app/settings/accounts/[id]/page.tsx
```

Execution note:

- `node --version`: `v25.8.1`, satisfying the Next 16 `20.9.0+` requirement.
- `git status --short --branch`: `dev...origin/dev`, with only `docs/superpowers/demos/` untracked.
- `npm audit --json`: 2 vulnerabilities (`next` high, nested `next/node_modules/postcss` moderate), with `next@16.2.7` semver-major fix path.
- Baseline frontend checks passed: 41 Node tests, TypeScript exit 0, and Next 14.2.35 production build exit 0 including `/insights/[artifactId]`.
- Dynamic route scan used `rg --files` because the original `find frontend/app -path '*[*]*' -name page.tsx -print` pattern did not match in this shell; it found the expected route set, with `positions/[id]/add-batch/page.tsx` captured by a nested dynamic route scan.

- [ ] **Step 5: Commit baseline plan progress if this task records new evidence**

Run only if this plan file is updated with observed baseline results:
```bash
git add docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md
git commit -m "docs: record next 16 upgrade baseline"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 2: Upgrade Framework Dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Upgrade Next and React packages**

Run:
```bash
cd frontend
npm install next@16.2.7 react@latest react-dom@latest
npm install --save-dev @types/react@latest @types/react-dom@latest
```

Expected:
```text
frontend/package.json resolves next to a 16.x range.
frontend/package.json resolves react and react-dom to a 19.x range.
frontend/package.json resolves @types/react and @types/react-dom to current React 19 compatible ranges.
frontend/package-lock.json is updated.
```

- [ ] **Step 2: Run immediate audit after dependency upgrade**

Run:
```bash
cd frontend
npm audit --json
```

Expected:
```text
metadata.vulnerabilities.total: 0
```

If vulnerabilities remain:
```text
Stop and record package, severity, advisory URL, nodes, and fixAvailable before changing more dependencies.
```

- [ ] **Step 3: Run focused frontend tests after dependency upgrade**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

Expected:
```text
All Node adapter/client tests pass.
```

- [ ] **Step 4: Run TypeScript to expose migration errors**

Run:
```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
TypeScript may fail on App Router dynamic params or React 19 type changes.
Record the exact errors in this plan before implementing Task 3.
```

---

### Task 3: Migrate Dynamic App Router Params

**Files:**
- Modify or split: `frontend/app/insights/[artifactId]/page.tsx`
- Modify or split: `frontend/app/settings/accounts/[id]/page.tsx`
- Inspect: `frontend/app/positions/[id]/page.tsx`
- Inspect: `frontend/app/positions/[id]/add-batch/page.tsx`

**Design:** Pages that currently receive `params` directly in a client component should switch to client-safe `useParams()` only, matching the existing positions pages. This keeps the migration small and avoids splitting large client pages unless Next 16 build output proves a wrapper is necessary.

- [ ] **Step 1: Migrate `/insights/[artifactId]` away from page prop params**

Modify `frontend/app/insights/[artifactId]/page.tsx`:
```tsx
'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Loader2 } from 'lucide-react'

import { InsightArtifactDetailCard } from '@/components/insights/InsightArtifactDetailCard'
import { useAuth } from '@/contexts/AuthContext'
import { useInsightArtifact } from '@/hooks/useInsightArtifact'

export default function InsightArtifactDetailPage() {
    const { token } = useAuth()
    const params = useParams()
    const artifactId = params.artifactId as string
    const query = useInsightArtifact(token, artifactId)

    if (query.isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (query.error || !query.data) {
        return (
            <div className="card p-8 text-center">
                <p className="text-sm text-slate-500">Insight artifact not found.</p>
                <Link href="/insights" className="mt-4 inline-flex text-sm font-semibold text-primary-600">
                    Back to insights
                </Link>
            </div>
        )
    }

    return (
        <div className="space-y-4 pb-20 md:pb-6">
            <Link href="/insights" className="inline-flex items-center gap-2 text-sm font-semibold text-primary-600">
                <ArrowLeft className="h-4 w-4" />
                Back to insights
            </Link>
            <InsightArtifactDetailCard artifact={query.data} />
        </div>
    )
}
```

- [ ] **Step 2: Migrate `/settings/accounts/[id]` away from page prop params**

Modify the import in `frontend/app/settings/accounts/[id]/page.tsx`:
```tsx
import { useRouter, useParams } from 'next/navigation'
```

Modify the component signature and first lines:
```tsx
export default function AccountDetailPage() {
    const params = useParams()
    const id = params.id as string
    const router = useRouter()
    const { token } = useAuth()
```

- [ ] **Step 3: Confirm `/positions/[id]` already uses `useParams()` only**

Run:
```bash
rg -n "params|useParams" 'frontend/app/positions/[id]/page.tsx'
```

Expected:
```text
The page imports useParams from next/navigation and reads params.id inside the client component.
No page prop params are used.
```

- [ ] **Step 4: Confirm `/positions/[id]/add-batch` already uses `useParams()` and `useSearchParams()` only**

Run:
```bash
rg -n "params|searchParams|useParams|useSearchParams" 'frontend/app/positions/[id]/add-batch/page.tsx'
```

Expected:
```text
The page imports useParams and useSearchParams from next/navigation.
No page prop params or page prop searchParams are used.
```

- [ ] **Step 5: Verify dynamic params migration**

Run:
```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

Expected:
```text
TypeScript exits 0.
Next build exits 0.
Build output includes /insights/[artifactId], /positions/[id], /positions/[id]/add-batch, and /settings/accounts/[id].
No dynamic page reads `params` from page props inside a client component.
```

---

### Task 4: Replace Removed `next lint` Script

**Files:**
- Modify: `frontend/package.json`
- Optional create: `frontend/eslint.config.mjs`

- [ ] **Step 1: Verify whether `next lint` is unavailable**

Run:
```bash
cd frontend
npm run lint
```

Expected on Next 16:
```text
The command fails because next lint is removed or deprecated.
```

- [ ] **Step 2: Install ESLint CLI only if lint script must remain supported**

Run only if the team wants `npm run lint` preserved:
```bash
cd frontend
npm install --save-dev eslint eslint-config-next
```

Expected:
```text
frontend/package.json devDependencies include eslint and eslint-config-next.
frontend/package-lock.json is updated.
```

- [ ] **Step 3: Add flat ESLint config if needed**

Create `frontend/eslint.config.mjs` only if `npm run lint` cannot work without it:
```js
import nextVitals from 'eslint-config-next/core-web-vitals'

export default [
    ...nextVitals,
]
```

Modify `frontend/package.json`:
```json
"lint": "eslint ."
```

- [ ] **Step 4: Verify lint script if changed**

Run:
```bash
cd frontend
npm run lint
```

Expected:
```text
Lint exits 0, or any lint findings are fixed in this task before commit.
```

If preserving `npm run lint` requires a large lint cleanup:
```text
Stop and record the lint findings. Do not mix broad lint cleanup into the framework upgrade unless the user approves.
```

---

### Task 5: Full Frontend Verification and Stage Commit

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify dynamic route files from Task 3 if needed
- Modify lint files from Task 4 if needed
- Modify: `docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md`

- [ ] **Step 1: Run full frontend verification**

Run:
```bash
cd frontend
npm audit --json
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

Expected:
```text
npm audit reports 0 vulnerabilities.
Frontend Node tests pass.
TypeScript exits 0.
Next production build exits 0.
Build output includes /insights/[artifactId].
```

- [ ] **Step 2: Restore generated noise**

Run:
```bash
git restore frontend/next-env.d.ts frontend/tsconfig.tsbuildinfo
```

Expected:
```text
Generated Next/TypeScript files are not modified unless intentionally required by the migration.
```

- [ ] **Step 3: Verify repo hygiene**

Run:
```bash
git diff --check
git status --short
```

Expected:
```text
No whitespace errors.
Only P8 dependency/migration/docs files are staged candidates.
docs/superpowers/demos/ remains untracked and untouched.
```

- [ ] **Step 4: Commit and push P8 framework upgrade**

Run:
```bash
git add frontend/package.json frontend/package-lock.json frontend/app/insights/[artifactId]/page.tsx frontend/app/settings/accounts/[id]/page.tsx frontend/eslint.config.mjs docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md
git commit -m "chore: upgrade frontend to next 16"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
If optional files were not created, omit them from git add rather than creating placeholders.
```

---

### Task 6: Backend Smoke and Final Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md`
- Modify: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

- [ ] **Step 1: Run backend smoke after frontend framework upgrade**

Run:
```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
```

Expected:
```text
Backend tests pass.
```

- [ ] **Step 2: Run Alembic smoke**

Run from repo root:
```bash
DATABASE_URL=sqlite:////private/tmp/tradingnoobs_dev_p8_next16_final.db ./.venv313/bin/alembic -c backend/alembic.ini upgrade head
```

Expected:
```text
Alembic reaches 5e6f7a8b9cad.
```

- [ ] **Step 3: Update checkpoint docs**

Record in this plan and `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`:
```text
P8 dependency upgrade commit SHA.
Final next/react/react-dom/@types versions.
Final npm audit result.
Frontend test/tsc/build results.
Backend smoke and Alembic results.
Whether lint script was migrated, removed, or intentionally deferred.
docs/superpowers/demos/ untouched status.
```

- [ ] **Step 4: Commit and push final P8 docs**

Run:
```bash
git add docs/superpowers/plans/2026-06-06-dev-p8-next16-upgrade-plan.md docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md
git commit -m "docs: record dev p8 next 16 upgrade"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

## Known External References

- Next.js 16 upgrade guide: `https://nextjs.org/docs/app/guides/upgrading/version-16`
- Next.js 16 release blog: `https://nextjs.org/blog/next-16`

## Self-Review Notes

- This plan keeps the Next 16 migration separate from P5-P7 product work.
- The most likely code migration is App Router async `params` for client pages that currently receive `params` as props.
- Existing pages using `useParams()` / `useSearchParams()` should be verified but do not need wrapper churn unless Next 16 type/build output requires it.
- The current app has no custom webpack config in `frontend/next.config.js`, so the default Turbopack build path should be tried first.
- The stale `next lint` script is a known Next 16 migration surface; if lint migration creates broad findings, stop and keep that cleanup separate.
- No step requires touching `docs/superpowers/demos/`.
