# Trading Noobs Frontend Experience Redesign

> Date: 2026-04-07
> Status: Approved design baseline for implementation planning
> Scope: User-facing frontend experience redesign, information architecture reset, design system foundation, and frontend adaptation strategy for the new platform foundation

---

## 1. Background

Trading Noobs is no longer just a transaction log with a few analytics screens. The backend foundation is moving toward a proper trading truth model, AI workflow platform, chart schema layer, and clearer user/admin boundaries. The frontend should not remain a thin layer on top of early-stage routes and ad hoc DTOs.

This redesign treats the user-facing product as a new-generation experience rather than a visual polish pass.

The redesign assumes the current platform is still in a pre-production stage:

- previous trial data is not considered protected production history
- old frontend conventions do not require long-term compatibility
- the product may hard-cut to a new user-facing information architecture

---

## 2. Design Goals

The redesign should achieve the following:

1. Make the product feel like a decision review workbench rather than a generic trading dashboard.
2. Make the default entry point answer "what happened recently?" before "what is my aggregate state?"
3. Elevate decision quality, execution drift, emotion, and review quality to the same importance level as PnL.
4. Separate user flows from admin flows in both navigation and visual identity.
5. Support fast mobile capture and comfortable desktop analysis without forcing both surfaces into the same density model.
6. Introduce a frontend architecture that can absorb backend contract changes without every page breaking.

---

## 3. Product Positioning

### 3.1 Primary Product Identity

The new frontend should be positioned as:

- a decision review workbench
- a timeline-first trading journal
- an AI-assisted review companion

It should not feel like:

- a broker terminal
- a generic SaaS admin panel
- a content-heavy magazine product

### 3.2 Core User Promise

The product should help a user answer three questions clearly:

1. What have I been doing lately?
2. How good were those decisions and executions?
3. What patterns should I repeat or avoid next?

---

## 4. Experience Principles

### 4.1 Timeline-First

The default home should be the event timeline, not the macro dashboard.

### 4.2 Review-Centric

PnL remains important, but review completion, plan drift, checklist discipline, and emotional context must be first-class signals.

### 4.3 Progressive Disclosure

Users should see concise summaries first and expand only when they need deeper reasoning, AI context, or lifecycle detail.

### 4.4 Thread Continuity

A trade must read as a continuous story from `OPEN` to `AI insight`, not as disconnected records across unrelated pages.

### 4.5 AI as Copilot

AI should appear as contextual analysis, summaries, and prompts for reflection. It should not dominate the main interface as a full-screen chat-first surface.

### 4.6 Mobile Capture, Desktop Analysis

Mobile should optimize for quick recording, lightweight review, and daily follow-up. Desktop should optimize for deep analysis, comparison, and structured review work.

---

## 5. Information Architecture

### 5.1 User Navigation

The user-facing top-level navigation should be:

- `Timeline`
- `Dashboard`
- `Positions`
- `Strategies`
- `Insights`
- `Settings`

### 5.2 Role of Each Section

`Timeline`

- default landing page
- answers "what happened recently?"
- centered on event flow, review prompts, and narrative continuity

`Dashboard`

- macro overview page
- answers "what is my overall state?"
- centered on portfolio, exposure, performance, risk, freshness, and summaries

`Positions`

- inventory and management surface
- answers "what objects are currently active or completed?"

`Strategies`

- discipline and framework surface
- answers "how are my strategies, checklists, and rules performing?"

`Insights`

- AI and analysis surface
- answers "what patterns and summaries has the system detected?"

`Settings`

- user preferences, accounts, connections, and personal configuration

### 5.3 Admin Separation

Admin must not live inside user navigation.

Admin should move to a separate route family and shell, such as:

- `/admin/platform`
- `/admin/users`
- `/admin/jobs`
- `/admin/market-data`
- `/admin/ai`
- `/admin/ops`

This separation is architectural, visual, and mental. The user product should not feel contaminated by operational tooling.

---

## 6. Core Surface Definitions

### 6.1 Timeline Home

Timeline is the primary home screen.

Its job is to present a chronological decision stream made of event cards, review cards, AI summary cards, and context modules.

#### Desktop Structure

- left: stable navigation
- center top: compact weekly summary strip
- center middle: filters and view controls
- center main: event timeline
- right: contextual side rail

#### Mobile Structure

- top: page title plus compact weekly summary
- middle: filter chips plus single-column event stream
- bottom: persistent primary navigation
- side rail content moved into drawers or bottom sheets

#### Event Types on Timeline

Timeline should support at minimum:

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `REVIEW_COMPLETED`
- `AI_INSIGHT`
- `CHECKLIST_MISS`
- low-frequency system alerts such as data freshness or sync issues

#### Event Card Structure

Each timeline card should contain:

- event header: timestamp, event type, symbol or entity, result signal
- summary line: one-sentence explanation
- metadata row: account, strategy, emotion, confidence, tags
- expandable section: thesis, invalidation, checklist snapshot, drift notes, AI commentary, deep link

Timeline should feel like a decision archive in motion, not a table with cards around it.

### 6.2 Dashboard

Dashboard remains important, but it becomes a macro cockpit rather than the default home.

Its job is to explain aggregate state, not recent events.

It should prioritize:

- equity curve
- drawdown
- realized vs unrealized composition
- exposure and allocation
- strategy health
- account distribution
- risk views
- data freshness
- AI weekly summary

On mobile, Dashboard may become a lighter summary surface instead of a full-density analytical workstation.

### 6.3 Position Detail

Position detail should become a lifecycle thread page rather than a generic details-plus-tabs page.

It should tell the complete story of a trade:

- why it was opened
- what changed over time
- where the plan drifted
- how the result emerged
- what was learned

#### Position Detail Structure

Main thread sections:

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `REVIEW`
- `AI conclusion`

Context rail sections:

- result summary
- execution quality
- discipline and checklist profile
- emotion trajectory
- review verdict
- AI key takeaways

The detail page should optimize for narrative continuity, not field dumping.

### 6.4 Zero-Data Home

New users must not see a blank dashboard or empty analytics panels.

The home screen zero state should use a mixed onboarding model:

- left: step-by-step getting started actions
- right: preview of what the product will eventually show

Suggested onboarding actions:

- add account
- record first trade
- import trade history
- create first strategy

Suggested preview cards:

- example timeline event
- example completed review
- example AI insight

Once the first real event exists, the home page should automatically switch to the real timeline mode.

---

## 7. Visual Direction

### 7.1 Overall Tone

The visual tone should be:

- calm
- precise
- editorial in hierarchy but tool-like in structure
- serious without looking sterile

The redesign should avoid a default startup SaaS look.

### 7.2 Material and Surfaces

The current glassy feel should be replaced with a more grounded surface model:

- paper-like light surfaces
- fine borders
- subtle depth
- disciplined highlights

The interface should feel like a work surface or dossier, not a glowing control center.

### 7.3 Color Strategy

The palette should be light-first and neutral-first.

Suggested direction:

- base backgrounds: warm white, soft mineral gray, muted graphite
- neutral text: charcoal and softened black
- positive: deep green
- negative: brick red
- AI and insight: indigo or deep teal
- caution: amber

Color should communicate state and emphasis, not decorate every region.

### 7.4 Typography

Typography should separate interface language from reflective reading.

Recommended structure:

- UI font: `IBM Plex Sans` with `Noto Sans SC`
- numeric and code font: `IBM Plex Mono`
- selective editorial heading font: `Noto Serif SC` or a similar restrained serif for large narrative headings only

This creates a distinction between:

- operational UI
- analytical data
- reflective narrative content

### 7.5 Motion

Motion should be meaningful and sparse.

Recommended motion patterns:

- page-enter stagger for timeline cards
- subtle expand/collapse for card detail
- drawer and bottom-sheet motion for mobile context
- no constant pulsing or ornamental animation

Motion should reinforce structure and state change.

---

## 8. Responsive Strategy

### 8.1 User Product

The user-facing product should be mobile-first in flow design.

This means:

- fast access to timeline
- easy quick-capture actions
- compact review prompts
- lightweight AI summaries

### 8.2 Deep Analysis and Admin

Deep analysis surfaces and admin surfaces should be desktop-first.

This includes:

- Dashboard
- heavy chart comparison
- rich filtering
- provider and job operations
- admin consoles

This split is intentional and should be explicit in implementation planning.

### 8.3 Layout Rule

Desktop:

- stable left navigation
- central work surface
- optional persistent right context rail

Mobile:

- top summary
- single-column content stream
- drawer- or sheet-based contextual content
- bottom navigation for primary user routes

---

## 9. Design System Scope

This redesign requires a real design system baseline rather than isolated page restyling.

### 9.1 Tokens

Must define:

- colors
- typography
- spacing
- radii
- borders
- shadows
- motion durations
- breakpoints

### 9.2 Primitive Components

Must define:

- buttons
- inputs
- selects
- badges
- tabs
- cards
- drawers
- bottom sheets
- empty states
- loading skeletons
- warnings and freshness banners

### 9.3 Domain Components

Must define:

- timeline event card
- review card
- AI insight card
- lifecycle thread block
- dashboard metric card
- chart container
- filter bar

### 9.4 State Patterns

Every major page must consistently support:

- zero state
- loading state
- empty-but-configured state
- stale data state
- error state

---

## 10. Frontend Architecture Strategy

The redesigned frontend must not bind pages directly to raw backend DTOs.

### 10.1 Required Layering

Recommended structure:

- `app/` for routing and page shells
- `features/` for product-domain modules
- `components/primitives/` for low-level UI elements
- `components/system/` for shells and structural UI
- `components/domain/` for trading-specific components
- `lib/contracts/` for adapters, mappers, and schema-aligned view models

### 10.2 Adapter Requirement

The frontend must introduce a contract adaptation layer between API responses and view components.

This layer should:

- normalize backend payloads
- map raw DTOs into stable page view models
- absorb backend naming changes such as `Position -> TradingPosition`
- support future chart schema migration

This is mandatory because the platform foundation redesign will continue changing core domain contracts.

### 10.3 Route Families

The route tree should evolve toward:

- user routes
- admin routes
- shared shells

Suggested direction:

- `app/(user)/timeline`
- `app/(user)/dashboard`
- `app/(user)/positions`
- `app/(user)/strategies`
- `app/(user)/insights`
- `app/(user)/settings`
- `app/(admin)/admin/...`

---

## 11. Implementation Phasing

### Phase 1: Shell and Design System

Deliver:

- new navigation shell
- user/admin route separation
- token system
- typography system
- primitive components
- state components
- initial API adapter layer

Outcome:

- the new product skeleton exists before major page migration begins

### Phase 2: Timeline-First User Core

Deliver:

- new timeline home
- zero-data mixed onboarding home
- lifecycle-style position detail page
- quick-capture and review entry points
- mobile navigation and context drawers

Outcome:

- the primary user experience becomes real and coherent

### Phase 3: Dashboard and Insights

Deliver:

- new dashboard
- insights surface
- chart container system
- chart schema adaptation
- freshness and risk context modules

Outcome:

- the system gains an understandable macro view and analysis layer

### Phase 4: Secondary Product Surfaces

Deliver:

- redesigned positions index
- redesigned strategies surface
- redesigned settings
- admin-facing shell alignment
- motion and polish pass

Outcome:

- the rest of the application catches up to the new product language

---

## 12. Frozen Decisions for Planning

The following decisions should be treated as frozen before writing the implementation plan:

- default home is `Timeline`, not `Dashboard`
- `Dashboard` remains a first-class page but is not the default landing surface
- zero-data home uses a mixed onboarding-plus-preview model
- user-facing product is mobile-first in flow design
- deep analysis and admin surfaces are desktop-first
- position detail is lifecycle-thread based, not tab-dump based
- AI is a sidecar intelligence layer, not the main interface center
- frontend must use an adapter or view-model layer rather than direct page binding to raw backend payloads
- user and admin experiences must live in separate shells and route families

---

## 13. Out of Scope for This Design

The following are intentionally not specified in full detail here:

- final chart schema JSON structure
- exact backend endpoint payloads
- animation implementation details
- component library choice beyond the desired architecture direction
- full admin information architecture

These belong in the implementation plan or later technical specs.

---

## 14. Success Criteria

The redesign should be considered successful when:

- a new user immediately understands what the product is for
- an active user can open the app and understand recent trading behavior from the home screen
- a completed trade reads as a coherent lifecycle story
- the dashboard feels like a macro cockpit, not a duplicated homepage
- mobile capture flows feel fast and natural
- desktop analysis feels structured and calm
- backend contract changes can be absorbed by adapters instead of forcing page-by-page breakage

---

## 15. Summary

This redesign redefines the frontend from a page collection into a coherent product system.

The center of gravity moves:

- from dashboard-first to timeline-first
- from PnL-only to decision-quality-aware
- from raw pages to structured surfaces
- from ad hoc styling to a deliberate design system
- from direct DTO coupling to adaptable frontend contracts

The product should feel like a serious, reflective, decision review environment built for traders who want to improve how they think, not just record what they did.
