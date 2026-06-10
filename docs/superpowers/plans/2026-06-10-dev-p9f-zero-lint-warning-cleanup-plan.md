# P9F Zero Lint Warning Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the final three frontend lint warnings so lint exits cleanly with zero warnings.

**Architecture:** Keep changes surgical. Auth pages switch existing logo rendering to `next/image`; Dashboard hook keeps its debug effect but declares the full dependency list.

**Tech Stack:** Next.js 16, React 19, TypeScript, ESLint CLI, Node test runner.

---

### Task 1: Baseline And Planning

**Files:**
- Create: `docs/superpowers/specs/2026-06-10-p9f-zero-lint-warning-cleanup-design.md`
- Create: `docs/superpowers/plans/2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md`

- [x] **Step 1: Run lint RED baseline**

Run:

```bash
cd frontend
npm run lint
```

Expected: exits 0 with 3 warnings from login image, register image, and `useDashboardData` dependencies.

- [x] **Step 2: Write P9F design and implementation plan**

Create the P9F design and plan documents.

- [x] **Step 3: Commit planning docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-10-p9f-zero-lint-warning-cleanup-design.md docs/superpowers/plans/2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md
git commit -m "docs: plan p9f zero lint warning cleanup"
```

### Task 2: Auth Logo Image Warnings

**Files:**
- Modify: `frontend/app/login/page.tsx`
- Modify: `frontend/app/register/page.tsx`

- [x] **Step 1: Replace login logo `<img>` with `Image`**

Add `import Image from 'next/image'` and replace the logo with:

```tsx
<Image
    src={theme === 'dark' || resolvedTheme === 'dark' ? '/logo-white.png' : '/logo-black.png'}
    alt="Trading Noobs Logo"
    width={80}
    height={80}
    priority
    className="w-full h-full object-contain rotate-6 group-hover:rotate-12 transition-transform duration-500"
/>
```

- [x] **Step 2: Replace register logo `<img>` with `Image`**

Use the same `Image` import and logo component shape in `frontend/app/register/page.tsx`.

- [x] **Step 3: Run targeted lint for auth pages**

Run:

```bash
cd frontend
./node_modules/.bin/eslint app/login/page.tsx app/register/page.tsx
```

Expected: exits 0 with no warnings.

- [x] **Step 4: Commit auth image cleanup**

Run:

```bash
git add frontend/app/login/page.tsx frontend/app/register/page.tsx
git commit -m "fix: use optimized auth logos"
```

### Task 3: Dashboard Hook Dependency Warning

**Files:**
- Modify: `frontend/hooks/useDashboardData.ts`

- [x] **Step 1: Add the missing dependency**

Add `allPositionsQuery.error` to the debug effect dependency array.

- [x] **Step 2: Run targeted lint for Dashboard hook**

Run:

```bash
cd frontend
./node_modules/.bin/eslint hooks/useDashboardData.ts
```

Expected: exits 0 with no warnings.

- [x] **Step 3: Commit Dashboard hook cleanup**

Run:

```bash
git add frontend/hooks/useDashboardData.ts
git commit -m "fix: complete dashboard debug effect deps"
```

### Task 4: Full Verification And Push

**Files:**
- Modify: `docs/superpowers/plans/2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md`

- [x] **Step 1: Run full lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: exits 0 with 0 warnings.

- [x] **Step 2: Run global strict lint**

Run:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: exits 0 with 0 warnings.

- [x] **Step 3: Run tests and TypeScript**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: both commands exit 0.

- [x] **Step 4: Run build**

Run:

```bash
cd frontend
npm run build
```

Expected: exits 0. If sandbox restrictions block Turbopack, rerun with approval and record the reason.

- [x] **Step 5: Restore generated files if needed**

Run:

```bash
git status --short
```

Expected: only `docs/superpowers/demos/` remains untracked. If `frontend/next-env.d.ts` or `frontend/tsconfig.tsbuildinfo` changed, restore only those generated files.

- [x] **Step 6: Record verification results and commit plan closeout**

Update this plan's `Verification Results`, then run:

```bash
git add docs/superpowers/plans/2026-06-10-dev-p9f-zero-lint-warning-cleanup-plan.md
git commit -m "docs: close p9f zero lint warning cleanup"
```

- [x] **Step 7: Push `dev`**

Run:

```bash
git push origin dev
```

Expected: push succeeds. Do not create a PR.

## Verification Results

- RED baseline `npm run lint`: exited 0 with 3 warnings from `app/login/page.tsx`, `app/register/page.tsx`, and `hooks/useDashboardData.ts`.
- Auth targeted lint: `./node_modules/.bin/eslint app/login/page.tsx app/register/page.tsx` exited 0 with no output.
- Dashboard hook targeted lint: `./node_modules/.bin/eslint hooks/useDashboardData.ts` exited 0 with no output.
- Full lint: `npm run lint` exited 0 with no output, confirming 0 warnings.
- Global strict lint: `./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 0 with no output.
- Frontend tests: `node --experimental-strip-types --test tests/*.test.mts` exited 0; 78 tests passed.
- TypeScript: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Sandboxed build: `npm run build` exited 1 because Turbopack could not create a process / bind a port while processing `app/globals.css`.
- Escalated build: `npm run build` exited 0 on Next 16.2.7; routes included `/login`, `/register`, `/dashboard`, `/timeline`, and `/`.
- Generated files `frontend/next-env.d.ts` and `frontend/tsconfig.tsbuildinfo` were restored after build.
- Push: `git push origin dev` succeeded, updating `origin/dev` to P9F.

## Final Acceptance Checklist

- [x] Planning docs committed.
- [x] Auth logo warnings removed.
- [x] Dashboard hook dependency warning removed.
- [x] Full lint exits 0 with 0 warnings.
- [x] Strict lint exits 0 with 0 warnings.
- [x] Tests, TypeScript, and build pass.
- [x] Work is committed and pushed to `origin/dev`.
