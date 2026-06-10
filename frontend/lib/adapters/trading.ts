import type {
    BatchCreate,
    Position,
    TradeBatch,
    TradingAccount,
    TradingPositionTradeEventCreate,
    Transaction,
} from '../api.ts'
import { getEntityRouteId } from '../entityIds.ts'

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

export function getLegacyBatchMutationState(hasTruthLifecycle: boolean): {
    canMutate: boolean
    label: string
    reason: string
} {
    if (hasTruthLifecycle) {
        return {
            canMutate: false,
            label: '迁移只读',
            reason: '价格、数量和 PnL 已由 TradingPosition / PositionEvent truth path 接管。',
        }
    }

    return {
        canMutate: true,
        label: '编辑',
        reason: '尚未解析到 truth lifecycle，保留 legacy batch 迁移编辑入口。',
    }
}

export function getLegacyPositionDeleteState(hasTruthLifecycle: boolean): {
    canDelete: boolean
    label: string
    reason: string
} {
    if (hasTruthLifecycle) {
        return {
            canDelete: false,
            label: 'Truth 受保护',
            reason: 'TradingPosition 已成为审计真相，删除需要走后续 reversal / adjustment 流程。',
        }
    }

    return {
        canDelete: true,
        label: '删除',
        reason: '尚未解析到 truth lifecycle，保留 legacy position 迁移删除入口。',
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
            label: 'Legacy review migration',
            reason: hasLegacyReview
                ? '复盘正文仍来自 legacy Position.trade_review；新的结构化叙事请写入 truth narrative 或 evidence-linked artifact。'
                : 'truth lifecycle 已接管详情主叙事，且 legacy Position.trade_review 为空。',
        }
    }

    return {
        shouldDisplay: hasLegacyReview,
        isMigrationOnly: false,
        label: '交易复盘',
        reason: '尚未解析到 truth lifecycle，继续展示 legacy Position.trade_review。',
    }
}

export function getTruthFirstWriteFallbackState(
    hasTruthLifecycle: boolean,
    migrationFallbackRequested: boolean
): {
    canWriteLegacyFallback: boolean
    label: string
    reason: string
} {
    if (hasTruthLifecycle) {
        return {
            canWriteLegacyFallback: false,
            label: 'Truth write path ready',
            reason: 'TradingPosition / PositionEvent truth path is available; ordinary writes must use the truth event route.',
        }
    }

    if (migrationFallbackRequested) {
        return {
            canWriteLegacyFallback: true,
            label: 'Migration fallback enabled',
            reason: 'Truth lifecycle 暂不可用，本次将显式使用 legacy batch migration fallback；完成后需要重新同步 truth lifecycle。',
        }
    }

    return {
        canWriteLegacyFallback: false,
        label: 'Truth lifecycle unavailable',
        reason: '普通加仓/平仓需要 TradingPosition truth lifecycle；legacy batch 写入已降级为 migration fallback，不能静默作为普通路径执行。',
    }
}

export function adaptTransactions(transactions: Transaction[]): TransactionViewModel[] {
    return transactions.map(adaptTransaction)
}
