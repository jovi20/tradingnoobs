# ADR-0002: Journal Accounting Posting Contract

Status: Accepted, frozen, and implemented by JRN-006

Date: 2026-07-25

Machine contract: `backend/app_config/journal_accounting_v1.json`

Golden vectors: `backend/tests/fixtures/jrn005_accounting_golden_vectors_v1.json`

## Decision

JRN-005 froze the accounting semantics. JRN-006 implements them through Alembic revision `c3d4e5f6a7b8`; the append-only ledger and ledger replay are now authoritative for journal balance.

All inputs and calculations use `Decimal`. Intermediate results are not quantized. Every persisted posting is quantized once to `0.00000001` with `ROUND_HALF_EVEN`. Export retains the persisted eight-decimal value.

The journal balance is the sum of signed postings:

```text
opening balance
+ deposits - withdrawals
+ interest
+ cash dividends received - paid in lieu
+ realized gross PnL
- trade fees - account fees
+ exact compensating reversals
```

Trade notional never enters the journal balance. `realized_pnl_net` is position attribution, not a ledger posting:

```text
realized_pnl_net
= realized_pnl_gross
- close_event_fee
- consumed_FIFO_opening_fee
```

Posting `realized_pnl_net` in addition to `REALIZED_GROSS` and `TRADE_FEE` would double count fees and is forbidden.

## Posting Matrix

| Source fact | Posting kind | Signed amount | Zero policy |
|---|---|---:|---|
| OPEN / ADD | `TRADE_FEE` | `-fee` | omit |
| REDUCE / CLOSE | `REALIZED_GROSS` | long: `(exit-entry)*qty`; short: `(entry-exit)*qty` | emit |
| REDUCE / CLOSE | `TRADE_FEE` | `-fee` | omit |
| Opening balance | `OPENING_BALANCE` | positive magnitude | zero may be omitted |
| Deposit | `DEPOSIT` | positive magnitude | reject zero command |
| Withdrawal | `WITHDRAWAL` | negative magnitude | reject zero command |
| Interest | `INTEREST` | positive magnitude | reject zero command |
| Account fee | `ACCOUNT_FEE` | negative magnitude | reject zero command |
| Dividend received | `CASH_DIVIDEND` | positive magnitude | reject zero command |
| Dividend paid in lieu | `CASH_DIVIDEND` | negative magnitude | reject zero command |
| Reversal / void | same kind as original | exact negative of each original posting | emit as needed |

Each posting is unique by `(source_fact_public_id, posting_kind)`. A trade event has at most one aggregated fee, so one event can legitimately own both `REALIZED_GROSS` and `TRADE_FEE` without a collision. Replay returns an identical existing posting; a different amount under the same key is `409 POSTING_FACT_CONFLICT`.

## FIFO Fees

Each OPEN or ADD creates a FIFO lot carrying its quantized fee posting as fee basis. Consumption allocates fee by quantity and quantizes each allocation to eight decimals. The final consumption of a lot takes its exact remaining fee basis. This makes the allocations sum exactly to the posted opening fee, including indivisible cases such as one dollar across three units.

Long and short positions for the same account and instrument are separate `HEDGE_BY_DIRECTION` lifecycles. Lots, sequence numbers, PnL, fees, reversals, and aggregates never net across sides.

## Fee Inputs

Manual and canonical commands accept zero or one non-negative aggregated fee in account currency. Multiple components return `422 MULTIPLE_FEE_COMPONENTS_UNSUPPORTED`; a negative manual fee returns `422 INVALID_FEE_AMOUNT`; another currency returns `422 FEE_CURRENCY_MISMATCH`.

The IBKR adapter normalizes either signed representation of a nonzero commission to `abs(commission)` as the fee magnitude. This rule does not enable the adapter by itself: JRN-013 must first retain official field documentation and redacted real fixtures proving commission sign and currency semantics for the frozen Flex Query template. Missing evidence keeps the adapter disabled.

## Ordering And Corrections

Position facts sort by `(event_time_utc, sequence_no)`. `sequence_no` is monotonic under the position row lock. Manual commands cannot backdate; Import preserves original row order for equal timestamps and rejects financially significant ambiguity with `UNSUPPORTED_ORDER_CONFLICT`.

Reversal and void never update or delete an original fact or posting. They append one exact compensating posting for every posting produced by the reversed fact, then replay FIFO attribution from immutable facts. Product authorization and lifecycle conflict rules remain owned by JRN-009/JRN-010.

## Implementation Status

JRN-006 introduces explicit posting kinds, `(source_fact_public_id, posting_kind)` uniqueness, ORM plus SQLite/PostgreSQL append-only guards, deterministic replay, accounting-health quarantine, audited compensation, and a ledger-derived journal balance. It writes realized gross and trade fees separately; realized net remains position attribution only.

Migration preview and the reconciliation command do not silently rewrite divergent accounting facts. Duplicate legacy posting keys, unresolved net postings, owner-graph mismatches, currency mismatches, and account-currency amount mismatches are assigned unique `LEGACY_UNRESOLVED` facts, receive reconciliation cases, and mark the account `ACCOUNTING_RECONCILIATION_REQUIRED`. Such accounts remain read-only for financial mutations and are excluded from trusted aggregate balances until invariants pass.

JRN-007/JRN-008 add canonical account/position locking, durable financial-command idempotency, and fully transactional truth-native writers. JRN-009/JRN-010 add immutable cash and product-complete trade reversal/void commands.
