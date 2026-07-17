import Link from 'next/link'
import { Briefcase, ChevronRight, Plus, Wallet } from 'lucide-react'

import type { TradingAccountViewModel } from '@/lib/adapters/trading'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface SettingsAccountsOverviewProps {
    accounts: TradingAccountViewModel[]
    onAddAccount: () => void
    accountTypeLabels: Record<string, string>
}

function formatMoney(account: TradingAccountViewModel, value: number | null | undefined): string {
    return `${getCurrencySymbol(account.currency)} ${Number(value || 0).toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`
}

export function SettingsAccountsOverview({
    accounts,
    onAddAccount,
    accountTypeLabels,
}: SettingsAccountsOverviewProps) {
    const activeCount = accounts.filter((account) => account.is_active).length
    const currencies = Array.from(new Set(accounts.map((account) => account.currency))).filter(Boolean)

    return (
        <section className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none">
            <div className="flex flex-col gap-3 border-b border-line p-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="flex items-center gap-2 text-base font-bold">
                        <Wallet className="h-4 w-4" />
                        账户簿
                    </h2>
                    <p className="mt-1 text-xs text-ink-muted">
                        {accounts.length} 个账户 · {activeCount} 个启用 · {currencies.join('、') || '未设置币种'}
                    </p>
                </div>
                <button
                    type="button"
                    onClick={onAddAccount}
                    className="btn btn-secondary justify-center text-sm"
                >
                    <Plus className="mr-2 h-4 w-4" />
                    添加账户
                </button>
            </div>

            <div className="grid gap-3 border-b border-line p-4 sm:grid-cols-3">
                <AccountMetric label="全部账户" value={String(accounts.length)} />
                <AccountMetric label="活跃账户" value={String(activeCount)} />
                <AccountMetric label="币种" value={currencies.length ? currencies.join(' / ') : '暂无'} />
            </div>

            {accounts.length === 0 ? (
                <div className="p-8 text-center text-sm text-ink-muted">
                    暂无账户。添加账户后，交易记录、资金流水和复盘会关联到这里。
                </div>
            ) : (
                <div className="divide-y divide-line">
                    {accounts.map((account) => (
                        <Link
                            key={account.id}
                            href={`/settings/accounts/${account.routeId}`}
                            className="grid gap-3 p-4 transition-colors hover:bg-panel-subtle md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.7fr)_auto]"
                        >
                            <div className="flex min-w-0 items-center gap-3">
                                <div className="rounded-lg bg-panel-subtle p-2 text-ink-soft">
                                    <Briefcase className="h-4 w-4" />
                                </div>
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <p className="truncate text-sm font-semibold">{account.name}</p>
                                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${
                                            account.is_active
                                                ? 'bg-profit/10 text-profit'
                                                : 'bg-panel-subtle text-ink-muted'
                                        }`}>
                                            {account.is_active ? '启用' : '停用'}
                                        </span>
                                    </div>
                                    <p className="mt-1 truncate text-xs text-ink-muted">
                                        {account.broker} · {accountTypeLabels[account.account_type || ''] || account.account_type || '通用'} · {account.currency}
                                    </p>
                                </div>
                            </div>

                            <AccountValue label="日志余额" value={formatMoney(account, account.journal_balance)} />

                            <div className="hidden items-center justify-end text-ink-faint md:flex">
                                <ChevronRight className="h-4 w-4" />
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </section>
    )
}

function AccountMetric({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 truncate text-lg font-black">{value}</p>
        </div>
    )
}

function AccountValue({ label, value }: { label: string; value: string }) {
    return (
        <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-faint">{label}</p>
            <p className="mt-1 truncate font-mono text-sm font-semibold tn-nums">{value}</p>
        </div>
    )
}
