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
            reason: '价格、数量和盈亏已由审计生命周期（TradingPosition / PositionEvent）接管。',
        }
    }

    return {
        canMutate: true,
        label: '编辑',
        reason: '尚未建立审计生命周期，暂时保留旧批次的迁移编辑入口。',
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
            label: '审计记录受保护',
            reason: 'TradingPosition 已成为审计依据，修正应通过撤销或调整流程完成。',
        }
    }

    return {
        canDelete: true,
        label: '删除',
        reason: '尚未建立审计生命周期，暂时保留旧版持仓的迁移删除入口。',
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
            label: '审计事件已就绪',
            reason: '审计生命周期（TradingPosition / PositionEvent）可用，日常加仓和平仓必须写入审计事件。',
        }
    }

    if (migrationFallbackRequested) {
        return {
            canWriteLegacyFallback: true,
            label: '已启用迁移模式',
            reason: '审计生命周期暂不可用，本次将明确写入旧版批次；完成后需要重新同步审计生命周期。',
        }
    }

    return {
        canWriteLegacyFallback: false,
        label: '审计生命周期不可用',
        reason: '日常加仓和平仓需要审计生命周期；旧版批次写入仅限明确启用的迁移模式，不能静默执行。',
    }
}

export function adaptTransactions(transactions: Transaction[]): TransactionViewModel[] {
    return transactions.map(adaptTransaction)
}
