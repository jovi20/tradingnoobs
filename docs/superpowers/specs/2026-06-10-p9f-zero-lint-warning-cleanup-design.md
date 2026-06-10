# P9F Zero Lint Warning Cleanup Design

## Goal

Bring frontend lint from `0 errors / 3 warnings` to `0 errors / 0 warnings` after P9E enabled React 19 strict hooks lint globally.

## Background

P9E removed the global React 19 strict hook lint deferral and left only three normal lint warnings:

- `frontend/app/login/page.tsx`: logo rendered with `<img>`.
- `frontend/app/register/page.tsx`: logo rendered with `<img>`.
- `frontend/hooks/useDashboardData.ts`: debug effect omits `allPositionsQuery.error` from dependencies.

## Selected Direction

Use the smallest behavior-preserving cleanup.

- Replace the two auth-page logo `<img>` elements with `next/image` using explicit `width` and `height`.
- Preserve the current theme-aware logo source and hover rotation classes.
- Add the missing `allPositionsQuery.error` dependency to the Dashboard debug effect.
- Do not redesign login/register pages.
- Do not refactor Dashboard query behavior.
- Do not touch `docs/superpowers/demos/`.

## Verification

Use lint as the RED/GREEN test:

```bash
cd frontend
npm run lint
```

RED before implementation: exits 0 with 3 warnings.

GREEN after implementation: exits 0 with 0 warnings.

Run the normal completion checks:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

`npm run build` may require escalation because Turbopack has previously hit sandbox process/port restrictions.

## Acceptance Criteria

- `npm run lint` reports no warnings.
- React 19 strict lint still reports no errors or warnings.
- Tests, TypeScript, and build pass.
- Work is committed and pushed to `origin/dev`.
