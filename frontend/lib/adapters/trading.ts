import type {
    Position,
    TradeBatch,
    TradingAccount,
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

export function adaptTransactions(transactions: Transaction[]): TransactionViewModel[] {
    return transactions.map(adaptTransaction)
}
