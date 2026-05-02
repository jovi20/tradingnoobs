import { useState } from 'react'
import { TransactionCreate, accountsAPI } from '@/lib/api'
import { Loader2, Plus } from 'lucide-react'

interface TransactionFormProps {
    token: string
    accountId: number | string
    currency: string
    onSuccess: () => void
    onCancel: () => void
}

export function TransactionForm({ token, accountId, currency, onSuccess, onCancel }: TransactionFormProps) {
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [formData, setFormData] = useState<TransactionCreate>({
        type: 'DEPOSIT',
        amount: 0,
        currency: currency,
        date: new Date().toISOString().slice(0, 16), // YYYY-MM-DDTHH:mm
        description: ''
    })

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setIsSubmitting(true)
        try {
            await accountsAPI.createTransaction(token, accountId, formData)
            onSuccess()
        } catch (error) {
            console.error('Failed to create transaction:', error)
            alert('Failed to create transaction')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <label className="text-sm font-medium">类型</label>
                    <select
                        className="w-full p-2 border rounded-md bg-background"
                        value={formData.type}
                        onChange={e => setFormData({ ...formData, type: e.target.value })}
                    >
                        <option value="DEPOSIT">充值 / 入金 (Deposit)</option>
                        <option value="WITHDRAWAL">提取 / 出金 (Withdrawal)</option>
                        <option value="INTEREST">利息收益 (Interest)</option>
                        <option value="FEE">费用 / 税费 (Fee)</option>
                        <option value="TRANSFER_IN">转入 (Transfer In)</option>
                        <option value="TRANSFER_OUT">转出 (Transfer Out)</option>
                    </select>
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">金额</label>
                    <div className="relative">
                        <input
                            type="number"
                            step="0.01"
                            required
                            className="w-full p-2 border rounded-md bg-background pl-8"
                            value={formData.amount}
                            onChange={e => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
                        />
                        <span className="absolute left-3 top-2 text-muted-foreground">$</span>
                    </div>
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium">日期与时间</label>
                <input
                    type="datetime-local"
                    required
                    className="w-full p-2 border rounded-md bg-background"
                    value={formData.date}
                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                />
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium">备注 (可选)</label>
                <input
                    type="text"
                    className="w-full p-2 border rounded-md bg-background"
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                    placeholder="例如：每月入金"
                />
            </div>

            <div className="flex justify-end gap-2 pt-4">
                <button
                    type="button"
                    onClick={onCancel}
                    className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground"
                >
                    取消
                </button>
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
                >
                    {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    添加记录
                </button>
            </div>
        </form>
    )
}
