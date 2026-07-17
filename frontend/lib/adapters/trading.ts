import type {
    BatchCreate,
    Position,
    PositionOpenIdentity,
    ReleaseAssetType,
    ReleaseCurrency,
    ReleaseInstrumentType,
    ReleaseMarket,
    TradeBatch,
    TradingAccount,
    TradingPositionTradeEventCreate,
    Transaction,
} from '../api.ts'
import { getEntityRouteId } from '../entityIds.ts'
import { JOURNAL_BETA_RELEASE_CONTRACT } from '../generated/release-contract.ts'

export interface TradeBatchViewModel extends TradeBatch {
    routeId: string
    legacyId: number
}

export interface TransactionViewModel extends Transaction {
    routeId: string
    legacyId: number
}

export interface TradingAccountViewModel extends TradingAccount {
    routeId: string
    legacyId: number
}

export interface PositionViewModel extends Position {
    routeId: string
    legacyId: number
    batches?: TradeBatchViewModel[]
}

export function adaptTradeBatch(batch: TradeBatch): TradeBatchViewModel {
    return {
        ...batch,
        routeId: getEntityRouteId(batch),
        legacyId: batch.id,
    }
}

export function adaptTransaction(transaction: Transaction): TransactionViewModel {
    return {
        ...transaction,
        routeId: getEntityRouteId(transaction),
        legacyId: transaction.id,
    }
}

export function adaptTradingAccount(account: TradingAccount): TradingAccountViewModel {
    return {
        ...account,
        routeId: getEntityRouteId(account),
        legacyId: account.id,
    }
}

export function adaptPosition(position: Position): PositionViewModel {
    return {
        ...position,
        routeId: getEntityRouteId(position),
        legacyId: position.id,
        batches: position.batches?.map(adaptTradeBatch),
    }
}

export function adaptTradingAccounts(accounts: TradingAccount[]): TradingAccountViewModel[] {
    return accounts.map(adaptTradingAccount)
}

export function adaptPositions(positions: Position[]): PositionViewModel[] {
    return positions.map(adaptPosition)
}

const ASCII_IDENTITY_WHITESPACE_AT_EDGES = /^[\t\n\v\f\r ]+|[\t\n\v\f\r ]+$/g
const RELEASE_ASSET_TYPES = JOURNAL_BETA_RELEASE_CONTRACT.instruments.asset_types satisfies readonly ReleaseAssetType[]
const RELEASE_MARKETS = JOURNAL_BETA_RELEASE_CONTRACT.instruments.markets satisfies readonly ReleaseMarket[]
const RELEASE_INSTRUMENT_TYPES = JOURNAL_BETA_RELEASE_CONTRACT.instruments.instrument_types satisfies readonly ReleaseInstrumentType[]
const RELEASE_CURRENCIES = JOURNAL_BETA_RELEASE_CONTRACT.currency.account_base_currencies satisfies readonly ReleaseCurrency[]
const RELEASE_ASSET_TYPE_ALIASES: Readonly<Record<string, ReleaseAssetType>> = (
    JOURNAL_BETA_RELEASE_CONTRACT.instruments.asset_type_aliases
)
const RELEASE_INSTRUMENT_COMBINATIONS = JOURNAL_BETA_RELEASE_CONTRACT.instruments.allowed_combinations
const RELEASE_EXCHANGE_CODE_PATTERN = new RegExp(
    JOURNAL_BETA_RELEASE_CONTRACT.instruments.exchange_code_pattern
)
const RELEASE_SYMBOL_PATTERN = new RegExp(
    JOURNAL_BETA_RELEASE_CONTRACT.instruments.normalized_symbol_pattern
)

export type ReleasePositionIdentityField =
    | 'symbol'
    | 'exchange_code'
    | 'asset_type'
    | 'market'
    | 'instrument_type'
    | 'quote_currency'

export interface ReleasePositionIdentityInput {
    symbol: string
    exchange_code: string
    asset_type: string
    market: string
    instrument_type: string
    quote_currency: string
}

export type NormalizedReleasePositionIdentity = Omit<PositionOpenIdentity, 'account_id' | 'direction'>

export type ReleasePositionIdentityNormalizationResult =
    | { ok: true; identity: NormalizedReleasePositionIdentity }
    | {
        ok: false
        field: ReleasePositionIdentityField
        reason: 'REQUIRED' | 'NON_ASCII' | 'INVALID' | 'INVALID_COMBINATION'
    }

function isAllowedToken<T extends string>(value: string, allowed: readonly T[]): value is T {
    return allowed.some(candidate => candidate === value)
}

function canonicalizeReleaseAssetType(value: string): ReleaseAssetType | null {
    if (isAllowedToken(value, RELEASE_ASSET_TYPES)) return value
    return RELEASE_ASSET_TYPE_ALIASES[value] ?? null
}

export function isAsciiIdentityInput(value: string): boolean {
    return /^[\x00-\x7F]*$/.test(value)
}

export function normalizeAsciiIdentityInput(value: string): string {
    if (!isAsciiIdentityInput(value)) {
        throw new TypeError('Identity input must be ASCII before normalization')
    }
    return value.replace(ASCII_IDENTITY_WHITESPACE_AT_EDGES, '').toUpperCase()
}

export function normalizeExchangeCodeInput(value: string): string {
    return normalizeAsciiIdentityInput(value)
}

export const isAsciiExchangeCodeInput = isAsciiIdentityInput

export function normalizeSymbolInput(value: string): string {
    return normalizeAsciiIdentityInput(value)
}

export function isValidExchangeCodeInput(value: string): boolean {
    if (!isAsciiIdentityInput(value)) return false
    return RELEASE_EXCHANGE_CODE_PATTERN.test(normalizeExchangeCodeInput(value))
}

export function isValidSymbolInput(value: string): boolean {
    if (!isAsciiIdentityInput(value)) return false
    return RELEASE_SYMBOL_PATTERN.test(normalizeSymbolInput(value))
}

export function normalizeReleasePositionIdentityInput(
    input: ReleasePositionIdentityInput
): ReleasePositionIdentityNormalizationResult {
    const rawTokens: Array<[ReleasePositionIdentityField, string]> = [
        ['symbol', input.symbol],
        ['exchange_code', input.exchange_code],
        ['asset_type', input.asset_type],
        ['market', input.market],
        ['instrument_type', input.instrument_type],
        ['quote_currency', input.quote_currency],
    ]

    // Contract order is deliberate: reject every raw non-ASCII token before trimming or uppercasing any token.
    for (const [field, rawValue] of rawTokens) {
        if (!isAsciiIdentityInput(rawValue)) {
            return { ok: false, field, reason: 'NON_ASCII' }
        }
    }

    const symbol = normalizeSymbolInput(input.symbol)
    const exchangeCode = normalizeExchangeCodeInput(input.exchange_code)
    const rawNormalizedAssetType = normalizeAsciiIdentityInput(input.asset_type)
    const market = normalizeAsciiIdentityInput(input.market)
    const instrumentType = normalizeAsciiIdentityInput(input.instrument_type)
    const quoteCurrency = normalizeAsciiIdentityInput(input.quote_currency)

    const normalizedTokens: Array<[ReleasePositionIdentityField, string]> = [
        ['symbol', symbol],
        ['exchange_code', exchangeCode],
        ['asset_type', rawNormalizedAssetType],
        ['market', market],
        ['instrument_type', instrumentType],
        ['quote_currency', quoteCurrency],
    ]
    for (const [field, normalizedValue] of normalizedTokens) {
        if (!normalizedValue) {
            return { ok: false, field, reason: 'REQUIRED' }
        }
    }

    if (!RELEASE_SYMBOL_PATTERN.test(symbol)) {
        return { ok: false, field: 'symbol', reason: 'INVALID' }
    }
    if (!RELEASE_EXCHANGE_CODE_PATTERN.test(exchangeCode)) {
        return { ok: false, field: 'exchange_code', reason: 'INVALID' }
    }
    const assetType = canonicalizeReleaseAssetType(rawNormalizedAssetType)
    if (!assetType) {
        return { ok: false, field: 'asset_type', reason: 'INVALID' }
    }
    if (!isAllowedToken(market, RELEASE_MARKETS)) {
        return { ok: false, field: 'market', reason: 'INVALID' }
    }
    if (!isAllowedToken(instrumentType, RELEASE_INSTRUMENT_TYPES)) {
        return { ok: false, field: 'instrument_type', reason: 'INVALID' }
    }
    if (!isAllowedToken(quoteCurrency, RELEASE_CURRENCIES)) {
        return { ok: false, field: 'quote_currency', reason: 'INVALID' }
    }

    const validCombination = RELEASE_INSTRUMENT_COMBINATIONS.some(combination => (
        combination.asset_type === assetType
        && combination.market === market
        && combination.instrument_type === instrumentType
    ))
    if (!validCombination) {
        return { ok: false, field: 'market', reason: 'INVALID_COMBINATION' }
    }

    return {
        ok: true,
        identity: {
            symbol,
            exchange_code: exchangeCode,
            asset_type: assetType,
            market,
            instrument_type: instrumentType,
            quote_currency: quoteCurrency,
        },
    }
}

export function buildTruthTradeEventFromBatchForm(
    batch: BatchCreate,
    position: Pick<Position, 'total_quantity' | 'asset_metadata'>
): TradingPositionTradeEventCreate {
    const quantity = Number(batch.quantity)
    const openQuantity = Number(position.total_quantity || 0)
    const isFullExit = batch.type === 'EXIT' && Math.abs(quantity - openQuantity) < 0.00000001
    const event: TradingPositionTradeEventCreate = {
        event_type: batch.type === 'ENTRY' ? 'ADD' : (isFullExit ? 'CLOSE' : 'REDUCE'),
        quantity,
        price: Number(batch.price),
        currency: position.asset_metadata?.currency || 'USD',
        occurred_at: batch.time,
    }

    if (batch.reason) event.reason = batch.reason
    if (batch.emotion) event.emotion = batch.emotion
    if (batch.confidence) event.confidence = batch.confidence

    return event
}

export function getLegacyBatchMutationState(_hasTruthLifecycle: boolean): {
    canMutate: boolean
    label: string
    reason: string
} {
    return {
        canMutate: false,
        label: '迁移只读',
        reason: '旧版批次在普通产品入口中只读；价格、数量和盈亏修正必须走审计事件。',
    }
}

export function getLegacyPositionDeleteState(_hasTruthLifecycle: boolean): {
    canDelete: boolean
    label: string
    reason: string
} {
    return {
        canDelete: false,
        label: '审计记录受保护',
        reason: '旧版持仓不能从普通产品入口硬删除；修正应通过审计撤销、作废或归档流程完成。',
    }
}

export function getLegacyReviewDisplayState(
    hasTruthLifecycle: boolean,
    hasLegacyReview: boolean
): {
    shouldDisplay: boolean
    isMigrationOnly: boolean
    label: string
    reason: string
} {
    if (hasTruthLifecycle) {
        return {
            shouldDisplay: hasLegacyReview,
            isMigrationOnly: true,
            label: '旧版复盘迁移记录',
            reason: hasLegacyReview
                ? '这段复盘来自旧版 Position.trade_review，仅作为迁移参考；新的结构化叙事请写入审计事件。'
                : '审计生命周期已接管详情叙事，且旧版 Position.trade_review 为空。',
        }
    }

    return {
        shouldDisplay: hasLegacyReview,
        isMigrationOnly: false,
        label: '交易复盘',
        reason: '尚未建立审计生命周期，当前继续展示旧版复盘记录。',
    }
}

export function adaptTransactions(transactions: Transaction[]): TransactionViewModel[] {
    return transactions.map(adaptTransaction)
}
