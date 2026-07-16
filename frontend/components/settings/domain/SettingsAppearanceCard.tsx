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
                <Moon className="w-5 h-5 text-ink" />
                <h2 className="text-lg font-semibold">外观</h2>
            </div>

            <h3 className="text-sm font-semibold mb-3 text-ink">主题模式</h3>
            <div className="grid grid-cols-3 gap-3">
                {[
                    { value: 'light', label: '日间', icon: Sun },
                    { value: 'dark', label: '夜间', icon: Moon },
                    { value: 'system', label: '跟随系统', icon: Monitor },
                ].map(({ value, label, icon: Icon }) => (
                    <button
                        key={value}
                        onClick={() => setTheme(value)}
                        className={`p-4 rounded-md border-2 transition-colors flex flex-col items-center space-y-2 ${theme === value
                            ? 'border-ink bg-panel-subtle'
                            : 'border-line hover:border-line-strong'
                            }`}
                    >
                        <Icon className={`w-6 h-6 ${theme === value ? 'text-ink' : 'text-ink-muted'}`} />
                        <span className="text-sm font-medium">{label}</span>
                    </button>
                ))}
            </div>

            <div className="mt-6 pt-6 border-t border-line">
                <h3 className="text-sm font-semibold mb-3 text-ink">涨跌颜色</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <button
                        type="button"
                        onClick={() => onUpdateSetting('up_color', 'GREEN')}
                        className={`p-3 rounded-lg border-2 flex items-center justify-between transition-colors ${!settings.up_color || settings.up_color === 'GREEN'
                            ? 'border-profit bg-profit/10'
                            : 'border-line hover:border-line-strong'
                            }`}
                    >
                        <div className="text-left">
                            <div className="font-medium text-sm">绿涨红跌</div>
                            <div className="text-xs text-ink-muted">国际市场 / 加密资产</div>
                        </div>
                        <div className="flex gap-1">
                            <div className="w-4 h-4 rounded bg-profit"></div>
                            <div className="w-4 h-4 rounded bg-loss"></div>
                        </div>
                    </button>

                    <button
                        type="button"
                        onClick={() => onUpdateSetting('up_color', 'RED')}
                        className={`p-3 rounded-lg border-2 flex items-center justify-between transition-colors ${settings.up_color === 'RED'
                            ? 'border-loss bg-loss/10'
                            : 'border-line hover:border-line-strong'
                            }`}
                    >
                        <div className="text-left">
                            <div className="font-medium text-sm">红涨绿跌</div>
                            <div className="text-xs text-ink-muted">A股习惯</div>
                        </div>
                        <div className="flex gap-1">
                            <div className="w-4 h-4 rounded bg-loss"></div>
                            <div className="w-4 h-4 rounded bg-profit"></div>
                        </div>
                    </button>
                </div>
            </div>

            <div className="mt-6 pt-6 border-t border-line">
                <h3 className="text-sm font-semibold mb-3 text-ink">显示币种</h3>
                <p className="text-xs text-ink-muted mb-3">资产看板图表将统一换算为此币种显示，持仓价格不受影响</p>
                <div className="grid grid-cols-5 gap-2">
                    {currencyOptions.map(({ value, label }) => (
                        <button
                            key={value}
                            type="button"
                            onClick={() => onUpdateSetting('display_currency', value)}
                            className={`p-3 rounded-md border-2 text-center transition-colors ${(settings.display_currency || 'USD') === value
                                ? 'border-ink bg-panel-subtle'
                                : 'border-line hover:border-line-strong'
                                }`}
                        >
                            <div className="font-semibold text-sm">{value}</div>
                            <div className="text-xs text-ink-muted mt-1">{label.split(' - ')[1]}</div>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}
