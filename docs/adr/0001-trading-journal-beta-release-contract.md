# ADR-0001: Trading Journal Beta Release Contract

Status: Accepted and frozen for `TRADING_JOURNAL_BETA_V1`

Date: 2026-07-17

Machine contract: `backend/app_config/journal_beta_v1.json`

## Decision

The first release is an invite-only trading journal, not a brokerage terminal or a quantitative trading platform. The release uses one deployment currency, USD, and accepts only USD-denominated financial facts. `USDT` is not an alias for USD.

The supported instrument combinations are `STOCK/FUND + SPOT + US` and `CRYPTO + SPOT + CRYPTO`, always quoted in USD. Canonical identity includes asset type, market, exchange code, normalized symbol, instrument type, and quote currency. Identity validation rejects any non-ASCII character in the untrimmed raw token, then trims ASCII whitespace and upper-cases; exchange codes are 1-32 characters and normalized symbols are 1-50 characters, with exact patterns frozen in the machine contract. `EQUITY`, `ETF`, and `SPOT_CRYPTO` are input aliases only and normalize to canonical asset types. The release uses FIFO and `HEDGE_BY_DIRECTION`: one long and one short lifecycle may coexist for the same account and instrument, but two financially open lifecycles on the same side may not. A same-side `OPEN` conflict is a public recovery contract: HTTP 409, code `OPEN_POSITION_EXISTS`, existing lifecycle reference `position_public_id`, and recovery event `ADD`. Archived lifecycles remain readable but reject direct financial writes with HTTP 409 `POSITION_ARCHIVED`.

The legacy `Position.exchange` column is not identity evidence because older writes stored broker or import labels there. The transition bridge therefore defaults to deny: it requires an identity validated from the current request or an exact persisted `journal_identity_v1`; otherwise it returns `LEGACY_INSTRUMENT_IDENTITY_UNPROVEN` without canonical writes. Existing pre-upgrade truth remains readable without being rewritten, but that read-only projection cannot authorize check-open, ADD, or any other financial write. The global legacy `AssetMetadata(symbol)` row is system-owned until an owner-scoped label model exists, so ordinary users cannot create or patch shared name/sector metadata.

Trade commands are `OPEN`, `ADD`, `REDUCE`, and `CLOSE`. The cash surface is opening balance, deposit, withdrawal, interest, account fee, and same-currency cash dividend. Corrections use linked reversal or void facts. Transfers, stock splits, option events, arbitrary manual cash adjustments, cross-zero executions, ordinary backdating, and separate fee events are outside the release.

Each trade event has at most one aggregated, non-negative fee in USD. The fee posts separately as a negative `TRADE_FEE`; realized PnL remains gross. Monetary persistence is `NUMERIC(20,8)` with `ROUND_HALF_EVEN` at the final posting boundary.

Users must provide an IANA timezone. A naive timestamp is interpreted in that timezone, while ambiguous or nonexistent DST times are rejected with 422. Persistent timestamps are UTC-aware.

Financial and Import idempotency uses `(owner_id, versioned operation_scope, SHA256(raw key))`. Raw keys are not retained. Request payloads use versioned canonical JSON plus SHA-256; the same request replays the original versioned response, while a different payload under the same identity returns 409. Financial and Import audit records have no automatic TTL.

## Existing Currency Data

Existing accounts with a null or non-USD currency are never converted automatically and their historical facts are not rewritten. They remain available for reading, export, and archive, but all new financial mutations and Imports are rejected. A Beta release candidate must have zero nonconforming release-scope accounts. Users who need to continue recording create a USD account and preserve the old account as history.

## Import Boundary

The adapter allowlist contains `GENERIC_BOOTSTRAP` and `IBKR_FLEX_XML_V1`.

- Generic CSV/XLSX is a one-time bootstrap and does not trust arbitrary file trade IDs.
- IBKR Flex XML is a local-file adapter. Once JRN-013 through JRN-015 are complete, it must accept duplicate, overlapping, and incremental statements for one immutable source binding using `ibExecID`. The first binding-effective confirm establishes that binding: it either applies at least one effective execution or accepts a zero-execution statement with proven flat-boundary evidence and valid coverage. The latter completes with durable binding/coverage state but no canonical trade fact. It never reads a Flex token or makes a network request.

Both adapters use a 10 MiB file limit, 5,000 rows/executions, a 24-hour preview TTL, and 30-day retention for terminal normalized preview rows. The IBKR adapter additionally limits each owner to two nonterminal sessions and ten uploads per 600 seconds. These source-specific limits do not silently constrain the generic adapter.

Account trade source state is `CLEAN / MANUAL / SOURCE_BOUND`. Source health is an orthogonal `NOT_APPLICABLE / HEALTHY / RECONCILIATION_REQUIRED / SOURCE_DIVERGED` projection whose persistent truth belongs to the source binding. Source completeness is `CURRENT / PENDING_IMPORT`. The complete ImportSession state graph and legal transitions are frozen in the machine contract; later tasks implement those models without renaming the states.

This ADR freezes names, limits, retention, identity, and source states. It does not claim that either new Import implementation exists yet. Until replacement, the three known legacy `/api/positions/import/*` paths are deny-only and absent from OpenAPI; the unsafe in-memory handler is not imported. The frontend has no Import entry, and direct `/positions/import` access renders the framework not-found view. Generic Import is implemented in JRN-011/012; the source-bound IBKR parser and binding are implemented in JRN-013, incremental confirmation in JRN-014, and reconciliation in JRN-015.

## Capability Ceiling

The optional capabilities are `BROKER_SYNC`, `MARKET`, `AI_INSIGHTS`, `PDF_EXPORT`, `RISK_CARDS`, and `OPEN_REGISTRATION`. All are disabled in the journal Beta deployment.

The deployment ceiling is read once from `DEPLOYMENT_CAPABILITY_ALLOWLIST`. A missing value means an empty allowlist; an unknown token fails startup. The business database cannot expand the ceiling. A reserved runtime FeatureFlag may only narrow or roll out a capability already present in the deployment allowlist:

```text
effective_enabled = deployment_allowlist AND runtime_rollout_flag
```

A missing, expired, malformed, or unreadable flag is disabled. Admin cannot enable a capability outside the ceiling. Expanding the deployment allowlist is a release change requiring staging and manual approval.

## Deferred Implementation

- JRN-003 owns invitation records, authentication rate limits, and plaintext secret removal migrations.
- JRN-005/006 own posting vectors and the append-only ledger implementation.
- JRN-007 through JRN-010 own canonical lifecycle writes and corrections.
- JRN-011 through JRN-015 own Import and source-bound implementation.

The broad legacy SQLAlchemy enums remain a storage compatibility superset. Public commands are constrained by the machine contract; this ADR does not rewrite historical rows or prematurely create later source models.
