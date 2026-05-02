import Link from 'next/link'
import { Briefcase, Plus, Wallet } from 'lucide-react'

import type { TradingAccountViewModel } from '@/lib/adapters/trading'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface SettingsAccountsOverviewProps {
    accounts: TradingAccountViewModel[]
    onAddAccount: () => void
    accountTypeLabels: Record<string, string>
}

export function SettingsAccountsOverview({
    accounts,
    onAddAccount,
    accountTypeLabels,
}: SettingsAccountsOverviewProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold flex items-center gap-2">
                    <Wallet className="w-5 h-5 text-indigo-500" />
                    实盘账户管理
                </h2>
                <button
                    onClick={onAddAccount}
                    className="text-sm font-medium text-indigo-500 hover:text-indigo-600 flex items-center gap-1"
                >
                    <Plus className="w-4 h-4" />
                    添加账户
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {accounts.length === 0 ? (
                    <div className="col-span-full py-8 text-center bg-slate-50 dark:bg-slate-800/30 rounded-2xl border border-dashed border-slate-200 dark:border-slate-700">
                        <p className="text-slate-500 text-sm">暂无账户，点击右上角添加</p>
                    </div>
                ) : (
                    accounts.map((account) => (
                        <Link
                            key={account.id}
                            href={`/settings/accounts/${account.routeId}`}
                            className="group relative p-5 rounded-2xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 hover:border-indigo-200 dark:hover:border-indigo-900/50 hover:shadow-lg hover:shadow-indigo-500/5 transition-all"
                        >
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2.5 rounded-xl bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400">
                                    <Briefcase className="w-5 h-5" />
                                </div>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase ${account.is_active
                                    ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400'
                                    : 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'
                                    }`}>
                                    {account.is_active ? 'Active' : 'Inactive'}
                                </span>
                            </div>

                            <div className="space-y-1">
                                <h3 className="font-bold text-slate-900 dark:text-white group-hover:text-indigo-500 transition-colors">
                                    {account.name}
                                </h3>
                                <p className="text-xs text-slate-500 flex items-center gap-1">
                                    {account.broker} • {accountTypeLabels[account.account_type || ''] || account.account_type || 'General'}
                                </p>
                            </div>

                            <div className="mt-6 grid grid-cols-3 gap-2 border-t border-slate-100 dark:border-slate-800 pt-4">
                                <div>
                                    <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-0.5">NAV 净值</p>
                                    <p className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                                        {getCurrencySymbol(account.currency)} {Number(account.total_equity ?? account.cash_balance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-0.5">Market Val</p>
                                    <p className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                                        {getCurrencySymbol(account.currency)} {Number(account.market_value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wider mb-0.5">Cash</p>
                                    <p className="font-mono font-bold text-sm text-slate-900 dark:text-white">
                                        {getCurrencySymbol(account.currency)} {Number(account.cash_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                    </p>
                                </div>
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    )
}
