'use client'

import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import {
    Save,
    Key,
    Moon,
    Sun,
    Monitor,
    Server,
    Bot,
    Loader2
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { settingsAPI, UserSettings } from '@/lib/api'

interface LocalSettings extends Partial<UserSettings> {
    binance_api_secret?: string
    llm_api_key?: string
}

export default function SettingsPage() {
    const { token } = useAuth()
    const { theme, setTheme } = useTheme()
    const [settings, setSettings] = useState<LocalSettings>({
        ibkr_host: '',
        ibkr_port: 7497,
        ibkr_client_id: 1,
        binance_api_key: '',
        binance_api_secret: '',
        finnhub_api_key: '',
        llm_api_url: '',
        llm_api_key: '',
        llm_model: 'gpt-4',
    })
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')

    useEffect(() => {
        const fetchSettings = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const data = await settingsAPI.get(token)
                setSettings({
                    ...data,
                    binance_api_secret: '',
                    llm_api_key: '',
                })
            } catch (err) {
                // 使用默认值
            } finally {
                setIsLoading(false)
            }
        }
        fetchSettings()
    }, [token])

    const handleSave = async () => {
        if (!token) return
        setError('')
        setIsSaving(true)
        try {
            await settingsAPI.update(token, {
                theme: theme || 'system',
                ibkr_host: settings.ibkr_host || null,
                ibkr_port: settings.ibkr_port || null,
                ibkr_client_id: settings.ibkr_client_id || null,
                binance_api_key: settings.binance_api_key || null,
                finnhub_api_key: settings.finnhub_api_key || null,
                llm_api_url: settings.llm_api_url || null,
                llm_model: settings.llm_model || null,
            })
            setSaved(true)
            setTimeout(() => setSaved(false), 3000)
        } catch (err: any) {
            setError(err.message || '保存失败')
        } finally {
            setIsSaving(false)
        }
    }

    const updateSetting = (key: keyof LocalSettings, value: string | number | null) => {
        setSettings((prev) => ({ ...prev, [key]: value }))
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6 pb-20 md:pb-6">
            <h1 className="text-2xl font-bold">设置</h1>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Theme */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Moon className="w-5 h-5 text-indigo-500" />
                    <h2 className="text-lg font-semibold">主题</h2>
                </div>
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
            </div>

            {/* IBKR Settings */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="w-5 h-5 text-blue-500" />
                    <h2 className="text-lg font-semibold">IBKR 盈透证券</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">TWS/Gateway 地址</label>
                        <input
                            type="text"
                            value={settings.ibkr_host || ''}
                            onChange={(e) => updateSetting('ibkr_host', e.target.value)}
                            className="input"
                            placeholder="127.0.0.1"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">端口</label>
                            <input
                                type="number"
                                value={settings.ibkr_port || ''}
                                onChange={(e) => updateSetting('ibkr_port', parseInt(e.target.value) || null)}
                                className="input"
                                placeholder="7497"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">Client ID</label>
                            <input
                                type="number"
                                value={settings.ibkr_client_id || ''}
                                onChange={(e) => updateSetting('ibkr_client_id', parseInt(e.target.value) || null)}
                                className="input"
                                placeholder="1"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Binance Settings */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Key className="w-5 h-5 text-amber-500" />
                    <h2 className="text-lg font-semibold">Binance 币安</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">API Key</label>
                        <input
                            type="password"
                            value={settings.binance_api_key || ''}
                            onChange={(e) => updateSetting('binance_api_key', e.target.value)}
                            className="input"
                            placeholder="••••••••"
                        />
                    </div>
                    <p className="text-xs text-slate-500">
                        ⚠️ 建议仅开启「只读」权限，禁用交易和提现功能
                    </p>
                </div>
            </div>

            {/* Market Data */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="w-5 h-5 text-emerald-500" />
                    <h2 className="text-lg font-semibold">行情数据 (Finnhub)</h2>
                </div>
                <div>
                    <label className="block text-sm font-medium mb-2">API Key</label>
                    <input
                        type="password"
                        value={settings.finnhub_api_key || ''}
                        onChange={(e) => updateSetting('finnhub_api_key', e.target.value)}
                        className="input"
                        placeholder="••••••••"
                    />
                    <p className="text-xs text-slate-500 mt-2">
                        免费获取：<a href="https://finnhub.io" target="_blank" rel="noopener" className="text-primary-500 hover:underline">finnhub.io</a>
                    </p>
                </div>
            </div>

            {/* LLM Settings */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Bot className="w-5 h-5 text-purple-500" />
                    <h2 className="text-lg font-semibold">LLM 周报配置</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">API URL</label>
                        <input
                            type="text"
                            value={settings.llm_api_url || ''}
                            onChange={(e) => updateSetting('llm_api_url', e.target.value)}
                            className="input"
                            placeholder="https://api.openai.com/v1"
                        />
                    </div>
                    <div>
                        <label className="block text-sm font-medium mb-2">模型</label>
                        <input
                            type="text"
                            value={settings.llm_model || ''}
                            onChange={(e) => updateSetting('llm_model', e.target.value)}
                            className="input"
                            placeholder="gpt-4"
                        />
                    </div>
                </div>
            </div>

            {/* Save Button */}
            <button
                onClick={handleSave}
                disabled={isSaving}
                className="w-full btn btn-primary py-3 flex items-center justify-center space-x-2"
            >
                {isSaving ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <Save className="w-5 h-5" />
                )}
                <span>{isSaving ? '保存中...' : saved ? '已保存 ✓' : '保存设置'}</span>
            </button>
        </div>
    )
}
