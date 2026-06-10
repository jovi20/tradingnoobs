# P9D Chart Schema And Freshness Migration Design

## Goal

Migrate every existing Recharts surface into a shared chart contract and freshness shell so Dashboard, Insights, AI artifacts, and legacy analytics present charts with the same schema, trust metadata, empty-state, and audit cues.

P9D intentionally follows the aggressive path selected by the user: migrate all current Recharts charts in one stage instead of limiting the work to Dashboard allocation.

## Background

P9A made `/timeline` the default decision workspace. P9B made `/dashboard` the macro command center. P9C made `/positions/[id]` a truth lifecycle workbench. Those pages now expose trust cues, but charts still have split contracts:

- `frontend/lib/chartSchemas.ts` defines Dashboard-specific chart payload adaptation.
- `frontend/lib/insightArtifacts.ts` defines a separate `ChartSchema` and partial chart validation for AI artifacts.
- Dashboard allocation, Dashboard equity, MAE/MFE scatter, Portfolio Sankey, and Insights analysis charts render directly with Recharts and display freshness/source inconsistently or not at all.
- Insights has duplicate chart rendering logic in `app/insights/page.tsx` and `components/insights/AnalysisAssistant.tsx`.

P9D closes this gap by making chart identity and trust metadata a first-class frontend contract.

## Selected Direction

Use **aggressive full Recharts migration**.

This direction does not replace Recharts as the renderer. It wraps every Recharts chart in a unified contract frame and moves schema/trust/empty-state logic out of page JSX. Renderer-specific code remains focused and replaceable.

The migration should be broad but not speculative:

- Do migrate all current Recharts usages to the shared chart shell.
- Do unify chart schema, payload, validation, trust summary, and empty-state helpers.
- Do extract duplicated Insights analysis chart logic into one reusable component.
- Do preserve existing visual hierarchy from P9A/P9B/P9C.
- Do not introduce ECharts yet.
- Do not change backend API contracts.
- Do not redesign Insights beyond chart contract hardening.

## Scope

### In Scope

- Create a shared chart contract module.
- Create a reusable `ChartFrame` component that displays title, description, schema badge, freshness/source/status cues, empty states, and optional footer notes.
- Replace split `ChartSchema` definitions with one exported chart contract type.
- Keep Dashboard allocation schema-first adaptation but move it to the shared chart contract layer.
- Wrap these existing Recharts surfaces in `ChartFrame`:
  - Dashboard allocation pie chart.
  - Dashboard equity line chart.
  - MAE/MFE scatter chart.
  - Portfolio Sankey chart.
  - Insights analysis bar charts in `/insights`.
  - Insights analysis bar charts in `AnalysisAssistant`.
- Extract Insights analysis chart data adaptation into pure helpers.
- Reuse the same supported-schema validation for AI artifact cards and artifact detail badges.
- Add tests for chart schema validation, trust labels, empty states, allocation payload adaptation, and Insights analysis chart adaptation.
- Run targeted strict React 19 lint for P9D-touched files.
- Verify Dashboard and Insights in the browser after implementation.

### Out Of Scope

- No backend chart payload changes.
- No ECharts renderer implementation.
- No async job freshness API changes.
- No Timeline page rewrite.
- No Lifecycle detail rewrite.
- No AI artifact payload generation changes.
- No global React 19 lint hardening; keep that for P9E.
- No changes to `docs/superpowers/demos/`.
- No PR creation unless explicitly requested.

## Contract Model

Create `frontend/lib/charts.ts` as the single chart contract layer.

Core types:

```ts
export type SupportedChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'sankey'

export interface ChartSeriesRef {
    field: string
    label: string
    color?: string
}

export interface ChartDimensionRef {
    field: string
    label: string
}

export interface ChartSchema {
    schema_version: 'chart.v1'
    chart_type: SupportedChartType
    series: ChartSeriesRef[]
    dimensions?: ChartDimensionRef[]
    data_path?: string
    options?: Record<string, string | number | boolean | null>
}

export interface ChartTrustMeta {
    as_of?: string
    generated_at?: string
    freshness?: 'FRESH' | 'DELAYED' | 'STALE' | 'DEGRADED' | string
    source?: string
    source_refs?: string[]
    maturity?: string
    value_status?: string
    note?: string
}

export interface ChartEmptyState {
    is_empty: boolean
    reason: string | null
    message?: string
}

export interface ChartPayload<TData = Record<string, unknown>> {
    chart_schema: ChartSchema
    data: TData[]
    empty_state: ChartEmptyState
    trust_meta: ChartTrustMeta
}
```

The frontend may accept string passthrough values for source and freshness because existing backend/AI payloads are not fully normalized yet. UI helpers must still map known freshness values to stable labels and tones.

## Chart Frame

Create `frontend/components/charts/ChartFrame.tsx`.

Responsibilities:

- Render a consistent chart shell using existing `Surface`, `SectionHeader`, and `StatusPill` patterns.
- Show schema badge when a supported schema exists.
- Show `freshness`, `source`, `as of`, and `source_refs` cues when provided.
- Show an explicit empty state if the chart has no data or `empty_state.is_empty` is true.
- Preserve children as the actual renderer area, so Recharts code can remain renderer-specific.
- Support compact mode for cards that already have dense layout.

`ChartFrame` should not know Recharts. Its only job is trust-aware presentation.

## Renderer Migration

### Dashboard Allocation

Keep `AllocationPieChart` as the renderer, but remove its standalone empty-state responsibility when used inside the Dashboard allocation panel. The parent panel should pass a schema-first `DashboardAllocationChartView` into `ChartFrame` and render `AllocationPieChart` as the child renderer.

When schema payloads are missing, existing fallback allocation arrays remain supported. The fallback chart should still get a synthesized local schema/trust object so the visual shell stays consistent.

### Dashboard Equity

Wrap the equity line chart inside `ChartFrame` with a local line schema:

- chart type: `line`
- dimension: `date`
- series: `pnl_percent`
- freshness/source: local derived frontend trust until backend chart payload exists

The period selector and hero metrics stay outside the chart frame because they are page controls, not chart trust metadata.

### MAE/MFE Scatter

Move derived scatter point adaptation into a pure helper:

- input: `Position[]`
- output: `{ id, symbol, mae, mfe, pnl, pnlPercent }[]`
- empty reason: `NO_MAE_MFE_POINTS`

Wrap the scatter renderer in `ChartFrame`. Remove `useMemo` unless the existing file still needs it after helper extraction.

### Portfolio Sankey

Wrap the Sankey renderer in `ChartFrame` with a local sankey schema. Keep current interaction behavior and mobile label behavior. If the data has no nodes, return a visible `ChartFrame` empty state instead of `null`.

### Insights Analysis Charts

Create one reusable chart component for legacy analysis responses:

```text
frontend/components/insights/LegacyAnalysisChart.tsx
frontend/lib/adapters/insight-charts.ts
frontend/tests/insight-charts.test.mts
```

The adapter should convert current `AnalysisResponse.raw_data` variants into one bar-chart view model:

- grouped `raw_data.stats`
- checklist comparison using `checklist_completed` and `checklist_ignored`
- unsupported or empty data returns explicit empty state

Both `/insights` and `AnalysisAssistant` should render the same component instead of duplicating Recharts logic.

## AI Artifact Integration

Move chart schema validation from `frontend/lib/insightArtifacts.ts` into `frontend/lib/charts.ts`.

`insightArtifacts.ts` should import the shared `ChartSchema`, `ChartTrustMeta`, and `assertSupportedChartSchema`. Artifact cards and detail views should continue showing chart badges, but the badge must come from shared helpers so Dashboard and Insights agree on supported chart types and schema labels.

## Freshness And Trust Display

Use shared helpers:

- `assertSupportedChartSchema(schema)`
- `getChartSchemaBadge(schema)`
- `getChartFreshnessTone(trust)`
- `formatChartTrustLabel(trust)`
- `buildChartEmptyState(payload, fallbackReason)`
- `hasChartData(data, emptyState)`

Known freshness values map to tones:

- `FRESH`: positive
- `DELAYED`: warning
- `STALE`: warning
- `DEGRADED`: danger
- missing/unknown: neutral

Do not hide missing trust. If trust metadata is absent, `ChartFrame` should show `local view` or `unversioned chart` copy instead of pretending the chart is fully audited.

## React 19 Lint Strategy

Do not enable strict React rules globally in P9D.

For P9D-touched files:

- Move chart data derivation into pure helpers.
- Avoid adding state in effects.
- Avoid render-time browser globals.
- Avoid `useMemo` / `useCallback` unless already necessary for behavior.
- Keep component props simple and serializable where practical.

## Testing Strategy

Use TDD for pure contract behavior:

- Extend `frontend/tests/chart-schemas.test.mts` or create `frontend/tests/charts.test.mts` for shared schema validation, badge labels, freshness tones, trust labels, and empty states.
- Keep Dashboard allocation payload tests but import from the shared chart module.
- Add `frontend/tests/insight-charts.test.mts` for grouped stats, checklist comparison, unsupported raw data, and empty states.
- Add or update Dashboard adapter tests if fallback schema/trust changes.

Use compile/build verification for UI:

- `node --experimental-strip-types --test tests/charts.test.mts`
- `node --experimental-strip-types --test tests/insight-charts.test.mts`
- `node --experimental-strip-types --test tests/*.test.mts`
- `./node_modules/.bin/tsc --noEmit --pretty false`
- `npm run lint`
- Targeted strict lint on P9D-touched files with `react-hooks/purity:error` and `react-hooks/set-state-in-effect:error`
- `npm run build`

Use browser verification after implementation:

- Desktop `/dashboard`: equity chart, allocation chart, freshness/schema cues, and empty-state behavior remain understandable.
- Mobile `/dashboard`: chart frames do not break vertical flow.
- Desktop `/insights`: legacy analysis chart uses the shared frame and no duplicate chart renderer path remains in the page.
- AI artifact sidecar still shows chart schema badges for supported artifact charts.

## Acceptance Criteria

- All current Recharts usages are wrapped by `ChartFrame` or routed through a shared chart component.
- There is one canonical frontend `ChartSchema` definition.
- Dashboard allocation still prefers schema-first payloads and keeps legacy fallback data working.
- Insights analysis charts render through one shared component in both usage sites.
- Chart trust metadata and empty-state copy are visible and consistent.
- P9D-touched files pass targeted React 19 strict lint.
- Full frontend tests, TypeScript, lint, build, and browser smoke pass.

## Risks And Controls

- Risk: aggressive migration creates a wide diff across Dashboard and Insights.
  Control: keep renderer behavior unchanged and move only contract/frame concerns.
- Risk: old API data lacks full trust metadata.
  Control: synthesize clearly labeled local chart trust instead of pretending backend freshness exists.
- Risk: Insights legacy chart logic is tangled with page state.
  Control: extract a pure adapter first and migrate both render sites to one component.
- Risk: Recharts behavior changes during wrapper migration.
  Control: preserve renderer internals and use browser smoke on Dashboard and Insights.

## Future Work

- P9E: remove global React 19 strict lint deferrals.
- Later chart phase: add ECharts renderer from the same chart contract.
- Later backend phase: expose schema-first payloads for Dashboard equity, MAE/MFE, Sankey, and Insights legacy analyses instead of frontend-synthesized local schemas.
