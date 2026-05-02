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

export function adaptTransactions(transactions: Transaction[]): TransactionViewModel[] {
    return transactions.map(adaptTransaction)
}
