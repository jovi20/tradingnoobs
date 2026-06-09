# P9A Frontend Workbench Design

## Goal

Turn the current functional Timeline page into the product's primary decision workspace: a balanced Timeline-first home with a stronger design-system foundation, a right-side Review/AI/context rail on desktop, a readable single-column flow on mobile, and no backend contract expansion.

## Background

P8 completed the Next 16 / React 19 upgrade and removed the remaining frontend audit findings. The app already redirects `/` to `/timeline`, and `/timeline` already consumes `useTimelineHomeData`, `TimelineHomeViewModel`, Review Inbox, context rail, and evidence-linked AI sidecar data.

The current frontend is stable but still feels like a functional bridge:

- `frontend/app/timeline/page.tsx` composes several cards directly and uses generic card styling.
- `frontend/components/Navbar.tsx` mixes desktop nav, mobile nav, logo/theme handling, user state, and admin exposure in one file.
- `frontend/app/globals.css` has global `.card` / `.btn` primitives, but page-specific surfaces still vary heavily.
- React 19 lint hardening rules were deferred in P8 because enabling them globally would create broad unrelated cleanup.

## Selected Direction

The selected layout is **A: Balanced Workbench**.

Desktop:

- Top nav remains compact and product-level.
- Main page header explains the current decision state.
- Summary strip sits near the top as a compact status readout.
- Main Timeline column owns the left/center space.
- Review Inbox, AI sidecar, and context rail live in the right column.
- The page should feel like a trading decision desk, not a dashboard clone.

Mobile:

- One-column reading order.
- Summary is compact.
- Review Inbox appears before the full feed when it has items.
- Timeline remains the primary scroll.
- AI/context sections collapse below the feed or into compact disclosure panels.
- Bottom navigation remains available for product switching.

## Scope

### In Scope

- Introduce a small frontend design-system foundation for page frames, surfaces, section headers, metric tiles, pills/badges, and empty/loading/error panels.
- Refactor the Timeline page into focused components instead of keeping most page structure in `app/timeline/page.tsx`.
- Redesign Timeline event cards for progressive disclosure using existing read-model fields: summary, impact, account, tags, emotion, confidence, checklist, thesis excerpt, invalidation excerpt, AI annotation, and trust metadata.
- Redesign Review Inbox presentation as an action rail rather than a generic list.
- Improve navigation shell structure enough to support the new workbench without making admin a normal user-nav item.
- Fix React 19 lint issues in P9A-touched files where practical.
- Keep P9A behavior-compatible with the current `/api/timeline/home` response.

### Out of Scope

- No backend API changes.
- No Dashboard rewrite.
- No lifecycle detail rewrite.
- No chart migration.
- No full-app visual redesign.
- No global React 19 lint hardening for files untouched by P9A.
- No changes to `docs/superpowers/demos/`.

## Visual Direction

Use a **ledger desk / decision journal** aesthetic:

- Typography: keep the current serif app personality, but use cleaner hierarchy and more deliberate numeric styling.
- Color: use slate, paper, ink, amber, emerald, red, and blue accents. Avoid purple-driven generic gradients.
- Surfaces: reduce heavy glass/card hover effects on dense data. Prefer calm layered panels, thin borders, soft shadows, and clear status strips.
- Motion: limited to meaningful hover/focus/active states and small page-load reveal classes if they do not complicate tests or accessibility.
- Density: desktop may be dense, mobile must remain readable.

## Information Architecture

Timeline Workbench order:

1. Page state header
2. Summary strip
3. View filters
4. Main Timeline feed
5. Review Inbox action rail
6. AI sidecar
7. Context rail

Desktop layout:

```text
+--------------------------------------------------------------+
| Product nav                                                   |
+--------------------------------------------------------------+
| Header: "Today / this week decision state"   refresh/actions  |
+--------------------------------------------------------------+
| Summary strip: trades / review rate / equity / alerts         |
+--------------------------------------+-----------------------+
| Filter chips                          | Review Inbox          |
|                                      | AI Sidecar            |
| Timeline event groups                 | Context Rail          |
|                                      |                       |
+--------------------------------------+-----------------------+
```

Mobile layout:

```text
Header
Summary strip
View chips
Review Inbox if non-empty
Timeline feed
AI/context disclosures
Bottom nav
```

## Component Boundaries

### Design System

Create focused components under `frontend/components/ui/`:

- `PageFrame.tsx`: standard page width, header spacing, and responsive content shell.
- `Surface.tsx`: stable surface variants for panels, cards, rails, and soft alerts.
- `SectionHeader.tsx`: reusable title/subtitle/action header.
- `MetricTile.tsx`: compact metric display used by Timeline summary strip.
- `StatusPill.tsx`: generic pill for freshness/source/severity/status.
- `EmptyStatePanel.tsx`: consistent empty/error/loading panels.

These components should be presentational and typed. They should not import business adapters or API clients.

### Timeline Workbench

Create focused components under `frontend/components/timeline/workbench/`:

- `TimelineWorkbench.tsx`: top-level page composition for loaded data.
- `TimelineWorkbenchHeader.tsx`: page title, as-of trust label, refresh action.
- `TimelineViewTabs.tsx`: filter chips for `TimelineView`.
- `TimelineFeedPanel.tsx`: grouped feed rendering and empty state.
- `TimelineEventCardV2.tsx`: redesigned event card with progressive disclosure.
- `ReviewInboxPanel.tsx`: right-rail review actions.
- `TimelineDecisionRail.tsx`: desktop rail and mobile disclosure composition.

Keep existing `frontend/components/timeline/*` components available during migration. P9A may replace their use in `/timeline`, but should not remove old components unless no references remain and verification proves clean.

### Navigation

Split `Navbar.tsx` responsibilities:

- Keep `Navbar.tsx` as the public export used by `app/layout.tsx`.
- Move nav item definitions and active-state helpers into `frontend/lib/navigation.ts`.
- Create `frontend/components/navigation/ProductTopNav.tsx`.
- Create `frontend/components/navigation/MobileBottomNav.tsx`.
- Admin route access should be visually separated from user product nav. For P9A, it can remain accessible to admins as a small ops/admin link, but it should not look like a normal primary user product surface.

## Data Flow

No backend change:

```text
GET /api/timeline/home
  -> frontend/lib/api.ts existing client
  -> useTimelineHomeData(token, view)
  -> adaptTimelineHome(response)
  -> TimelineWorkbench
  -> TimelineFeedPanel / ReviewInboxPanel / TimelineDecisionRail
```

New pure helper module:

- `frontend/lib/adapters/timeline-workbench.ts`

Responsibilities:

- Format metric tiles for the summary strip.
- Format event timestamps and compact meta labels.
- Format event impact labels and tones.
- Decide mobile/desktop section order in a testable way where useful.
- Provide severity/tone mapping for the new UI without embedding business decisions in JSX.

## React 19 Lint Strategy

Do not re-enable deferred React 19 lint rules globally in P9A. Instead:

- Remove `setState` in effects from files P9A touches where it is straightforward.
- Avoid `Date.now()` or other impure calls in render for new/touched Timeline components.
- Run targeted ESLint commands with `react-hooks/purity` and `react-hooks/set-state-in-effect` turned on for P9A-touched files.
- Keep global config deferral until a future dedicated lint-hardening stage can address the whole app.

## Testing Strategy

Use TDD where behavior changes are testable:

- Add `frontend/tests/timeline-workbench.test.mts` for pure Timeline formatting/order helpers.
- Add `frontend/tests/navigation.test.mts` for nav item visibility and active-state helper behavior.
- Keep existing Timeline adapter tests passing.

Use compile/build verification for presentational components:

- `node --experimental-strip-types --test tests/timeline-adapter.test.mts tests/timeline-workbench.test.mts tests/navigation.test.mts`
- `./node_modules/.bin/tsc --noEmit --pretty false`
- `npm run lint`
- targeted React 19 strict lint on P9A-touched files
- `npm run build`

Use browser/manual visual verification after implementation:

- Desktop `/timeline`: balanced two-column workbench.
- Mobile `/timeline`: one-column order with Review Inbox before Timeline when actionable.
- Empty/loading/error states.
- Dark mode should remain legible, but P9A should not become a dark-mode-first redesign.

## Acceptance Criteria

- `/` still redirects to `/timeline`.
- `/timeline` keeps using the existing Timeline Home API/hook.
- The Timeline page uses the balanced workbench layout.
- Review Inbox is visible as a first-class action rail on desktop.
- Mobile view remains one-column and does not hide primary Timeline content.
- New UI primitives are under `frontend/components/ui/` and do not depend on business APIs.
- Timeline-specific workbench components are under `frontend/components/timeline/workbench/`.
- P9A-touched files pass targeted React 19 strict lint rules.
- Full frontend verification passes.
- Backend smoke remains green after frontend work.

## Risks And Controls

- Risk: design-system work expands into full-app redesign.
  Control: only update surfaces used by nav and Timeline in P9A.

- Risk: Timeline page becomes visually better but still hard to test.
  Control: move formatting and tone decisions into tested pure helpers.

- Risk: React 19 lint work expands across the repo.
  Control: targeted strict lint for touched files only; leave global rule deferral documented.

- Risk: mobile rail content becomes buried.
  Control: Review Inbox appears before the feed when actionable; AI/context can follow as secondary disclosure.

## Follow-Up Stages

- P9B: Lifecycle detail hard cutover and detail-page visual pass.
- P9C: Dashboard macro view redesign after chart schema and freshness contracts are stable.
- P9D: Global React 19 lint hardening and removal of deferred config overrides.
