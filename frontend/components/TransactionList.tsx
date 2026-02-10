import { useState } from 'react'
import { Transaction, accountsAPI } from '@/lib/api'
import { Trash2, ArrowUpRight, ArrowDownLeft, ArrowRight } from 'lucide-react'
import { format } from 'date-fns'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface TransactionListProps {
    token: string
    transactions: Transaction[]
    onDelete: (id: number) => void
}

export function TransactionList({ token, transactions, onDelete }: TransactionListProps) {
    const [deletingId, setDeletingId] = useState<number | null>(null)

    const handleDelete = async (id: number) => {
        if (!confirm('确定要删除这条流水吗？账户余额将被冲回。')) return

        setDeletingId(id)
        try {
            await accountsAPI.deleteTransaction(token, id)
            onDelete(id)
        } catch (error) {
            console.error('Failed to delete transaction:', error)
            alert('Failed to delete transaction')
        } finally {
            setDeletingId(null)
        }
    }

    const getTypeLabel = (type: string) => {
        const labels: Record<string, string> = {
            DEPOSIT: '充值 / 入金',
            WITHDRAWAL: '提取 / 出金',
            INTEREST: '利息收益',
            FEE: '手续费 /税费',
            TRANSFER_IN: '转入',
            TRANSFER_OUT: '转出'
        }
        return labels[type] || type
    }

    const getIcon = (type: string) => {
        switch (type) {
            case 'DEPOSIT':
            case 'INTEREST':
            case 'TRANSFER_IN':
                return <ArrowDownLeft className="h-4 w-4 text-green-500" />
            case 'WITHDRAWAL':
            case 'FEE':
            case 'TRANSFER_OUT':
                return <ArrowUpRight className="h-4 w-4 text-red-500" />
            default:
                return <ArrowRight className="h-4 w-4 text-gray-500" />
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
        return <div className="text-center text-gray-500 py-4">No transactions found.</div>
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
                        <div className={`font-mono font-medium ${tx.amount >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {tx.amount > 0 ? '+' : tx.amount < 0 ? '-' : ''}{formatAmount(tx.amount, tx.currency)}
                        </div>
                        <button
                            onClick={() => handleDelete(tx.id)}
                            disabled={deletingId === tx.id}
                            className="text-muted-foreground hover:text-red-500 transition-colors p-1"
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            ))}
        </div>
    )
}
