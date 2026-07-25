import { useState } from 'react'
import { accountsAPI } from '@/lib/api'
import { TransactionViewModel } from '@/lib/adapters/trading'
import { RotateCcw, ArrowUpRight, ArrowDownLeft, ArrowRight } from 'lucide-react'
import { format } from 'date-fns'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface TransactionListProps {
    token: string
    transactions: TransactionViewModel[]
    onChanged: () => void
}

export function TransactionList({ token, transactions, onChanged }: TransactionListProps) {
    const [reversingId, setReversingId] = useState<string | null>(null)
    const [retryKeys, setRetryKeys] = useState<Record<string, string>>({})

    const handleReverse = async (id: string) => {
        const reason = prompt('请输入冲正原因')
        if (!reason?.trim()) return
        const key = retryKeys[id] || crypto.randomUUID()
        setRetryKeys((current) => ({ ...current, [id]: key }))

        setReversingId(id)
        try {
            await accountsAPI.reverseTransaction(
                token,
                id,
                { occurred_at: new Date().toISOString(), reason: reason.trim() },
                key,
            )
            setRetryKeys((current) => {
                const next = { ...current }
                delete next[id]
                return next
            })
            onChanged()
        } catch (error) {
            console.error('Failed to reverse transaction:', error)
            alert('冲正流水失败，请稍后重试')
        } finally {
            setReversingId(null)
        }
    }

    const getTypeLabel = (type: string) => {
        const labels: Record<string, string> = {
            DEPOSIT: '入金',
            WITHDRAWAL: '出金',
            INTEREST: '利息',
            FEE: '手续费或税费',
        }
        return labels[type] || type
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'DEPOSIT':
            case 'INTEREST':
                return <ArrowDownLeft className="h-4 w-4 text-profit" />
            case 'WITHDRAWAL':
            case 'FEE':
                return <ArrowUpRight className="h-4 w-4 text-loss" />
            default:
                return <ArrowRight className="h-4 w-4 text-ink-muted" />
        }
    }

    const formatAmount = (amount: number, currency: string) => {
        const symbol = getCurrencySymbol(currency)
        // Format number with commas
        const value = Math.abs(amount).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })
        return `${symbol}${value}`
    }

    if (transactions.length === 0) {
        return <div className="text-center text-ink-muted py-4">暂无资金流水</div>
    }

    return (
        <div className="space-y-2">
            {transactions.map(tx => (
                <div key={tx.id} className="flex items-center justify-between p-3 border rounded-lg bg-card hover:bg-accent/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full bg-secondary`}>
                            {getIcon(tx.type)}
                        </div>
                        <div>
                            <div className="font-medium flex items-center gap-2">
                                {getTypeLabel(tx.type)}
                                <span className="text-xs text-muted-foreground font-normal">
                                    {format(new Date(tx.date), 'yyyy-MM-dd HH:mm')}
                                </span>
                            </div>
                            {tx.description && (
                                <div className="text-sm text-muted-foreground">{tx.description}</div>
                            )}
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <div className={`font-mono font-medium tn-nums ${tx.amount >= 0 ? 'text-profit' : 'text-loss'}`}>
                            {tx.amount > 0 ? '+' : tx.amount < 0 ? '-' : ''}{formatAmount(tx.amount, tx.currency)}
                        </div>
                        <button
                            type="button"
                            onClick={() => handleReverse(tx.routeId)}
                            disabled={
                                reversingId === tx.routeId
                                || Boolean(tx.reverses_transaction_public_id)
                                || Boolean(tx.reversed_by_transaction_public_id)
                            }
                            aria-label={`冲正${getTypeLabel(tx.type)}流水`}
                            title="冲正流水"
                            className="text-muted-foreground hover:text-loss transition-colors p-1"
                        >
                            <RotateCcw className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
}
