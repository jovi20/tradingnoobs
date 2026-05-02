import { Monitor, Moon, Sun } from 'lucide-react'

import type { SettingsPageState } from '@/lib/adapters/settings'

interface SettingsAppearanceCardProps {
    theme: string | undefined
    setTheme: (value: string) => void
    settings: SettingsPageState
    onUpdateSetting: (key: keyof SettingsPageState, value: string | number | null) => void
    currencyOptions: Array<{ value: string; label: string }>
}

export function SettingsAppearanceCard({
    theme,
    setTheme,
    settings,
    onUpdateSetting,
    currencyOptions,
}: SettingsAppearanceCardProps) {
    return (
        <div className="card p-6">
            <div className="flex items-center space-x-3 mb-4">
                <Moon className="w-5 h-5 text-slate-900 dark:text-white" />
                <h2 className="text-lg font-semibold">外观</h2>
            </div>

            <h3 className="text-sm font-semibold mb-3 text-slate-900 dark:text-slate-200">主题模式</h3>
            <div className="grid grid-cols-3 gap-3">
                {[
                    { value: 'light', label: '日间', icon: Sun },
                    { value: 'dark', label: '夜间', icon: Moon },
                    { value: 'system', label: '跟随系统', icon: Monitor },
                ].map(({ value, label, icon: Icon }) => (
                    <button
                        key={value}
                        onClick={() => setTheme(value)}
                        className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center space-y-2 ${theme === value
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                            }`}
                    >
                        <Icon className={`w-6 h-6 ${theme === value ? 'text-primary-500' : 'text-slate-500'}`} />
                        <span className="text-sm font-medium">{label}</span>
                    </button>
                ))}
            </div>

            <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-semibold mb-3 text-slate-900 dark:text-slate-200">涨跌颜色</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button
                        type="button"
                        onClick={() => onUpdateSetting('up_color', 'GREEN')}
                        className={`p-3 rounded-lg border-2 flex items-center justify-between transition-all ${!settings.up_color || settings.up_color === 'GREEN'
                            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                            }`}
                    >
                        <div className="text-left">
                            <div className="font-medium text-sm">绿涨红跌 (Green Up)</div>
                            <div className="text-xs text-slate-500">国际惯例 / Crypto</div>
                        </div>
                        <div className="flex gap-1">
                            <div className="w-4 h-4 rounded bg-emerald-500"></div>
                            <div className="w-4 h-4 rounded bg-red-500"></div>
                        </div>
                    </button>

                    <button
                        type="button"
                        onClick={() => onUpdateSetting('up_color', 'RED')}
                        className={`p-3 rounded-lg border-2 flex items-center justify-between transition-all ${settings.up_color === 'RED'
                            ? 'border-red-500 bg-red-50 dark:bg-red-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                            }`}
                    >
                        <div className="text-left">
                            <div className="font-medium text-sm">红涨绿跌 (Red Up)</div>
                            <div className="text-xs text-slate-500">A股习惯</div>
                        </div>
                        <div className="flex gap-1">
                            <div className="w-4 h-4 rounded bg-red-500"></div>
                            <div className="w-4 h-4 rounded bg-emerald-500"></div>
                        </div>
                    </button>
                </div>
            </div>

            <div className="mt-6 pt-6 border-t border-slate-100 dark:border-slate-800">
                <h3 className="text-sm font-semibold mb-3 text-slate-900 dark:text-slate-200">显示币种</h3>
                <p className="text-xs text-slate-500 mb-3">Dashboard 图表将统一换算为此币种显示，持仓价格不受影响</p>
                <div className="grid grid-cols-5 gap-2">
                    {currencyOptions.map(({ value, label }) => (
                        <button
                            key={value}
                            type="button"
                            onClick={() => onUpdateSetting('display_currency', value)}
                            className={`p-3 rounded-lg border-2 text-center transition-all ${(settings.display_currency || 'USD') === value
                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                }`}
                        >
                            <div className="font-semibold text-sm">{value}</div>
                            <div className="text-xs text-slate-500 mt-1">{label.split(' - ')[1]}</div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}
