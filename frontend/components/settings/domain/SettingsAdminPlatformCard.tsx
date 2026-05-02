import { Bot, CheckCircle2, Loader2, PlugZap, Server, Shield, XCircle } from 'lucide-react'

import type { SettingsPageState } from '@/lib/adapters/settings'

interface SettingsAdminPlatformCardProps {
    settings: SettingsPageState
    testStatus: 'idle' | 'testing' | 'success' | 'error'
    testMessage: string
    onUpdateSetting: (key: keyof SettingsPageState, value: string | number | null) => void
    onTestLLM: () => Promise<void> | void
}

export function SettingsAdminPlatformCard({
    settings,
    testStatus,
    testMessage,
    onUpdateSetting,
    onTestLLM,
}: SettingsAdminPlatformCardProps) {
    return (
        <div className="card p-6 border-2 border-slate-200 dark:border-slate-700">
            <div className="flex items-center space-x-3 mb-6">
                <Shield className="w-5 h-5 text-slate-900 dark:text-white" />
                <div>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">系统全局配置</h2>
                    <p className="text-xs text-slate-500">仅管理员可见，修改后对所有用户生效</p>
                </div>
            </div>

            <div className="space-y-6">
                <div className="space-y-4">
                    <h3 className="text-sm font-medium text-slate-900 dark:text-slate-200 flex items-center gap-2">
                        <Server className="w-4 h-4 text-slate-900 dark:text-white" />
                        行情数据 (Finnhub)
                    </h3>
                    <div>
                        <label className="block text-xs font-medium mb-1.5 text-slate-500">API Key</label>
                        <input
                            type="password"
                            value={settings.finnhub_api_key_system || ''}
                            onChange={(e) => onUpdateSetting('finnhub_api_key_system', e.target.value)}
                            className="input font-mono"
                            placeholder={settings.finnhub_api_key_masked || '••••••••'}
                        />
                    </div>
                </div>

                <div className="h-px bg-slate-100 dark:bg-slate-700/50" />

                <div className="space-y-4">
                    <h3 className="text-sm font-medium text-slate-900 dark:text-slate-200 flex items-center gap-2">
                        <Bot className="w-4 h-4 text-purple-500" />
                        LLM 周报配置
                    </h3>
                    <div>
                        <label className="block text-xs font-medium mb-1.5 text-slate-500">API URL</label>
                        <input
                            type="text"
                            value={settings.llm_api_url_system || ''}
                            onChange={(e) => onUpdateSetting('llm_api_url_system', e.target.value)}
                            className="input font-mono"
                            placeholder="https://api.openai.com/v1"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium mb-1.5 text-slate-500">API Key</label>
                        <input
                            type="password"
                            value={settings.llm_api_key_system || ''}
                            onChange={(e) => onUpdateSetting('llm_api_key_system', e.target.value)}
                            className="input font-mono"
                            placeholder={settings.llm_api_key_masked || 'sk-...'}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium mb-1.5 text-slate-500">模型 (Model)</label>
                        <input
                            type="text"
                            value={settings.llm_model_system || ''}
                            onChange={(e) => onUpdateSetting('llm_model_system', e.target.value)}
                            className="input font-mono"
                            placeholder="gpt-4"
                        />
                    </div>

                    <div className="flex items-center space-x-4 pt-2">
                        <button
                            onClick={onTestLLM}
                            disabled={testStatus === 'testing'}
                            className="btn bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200"
                        >
                            {testStatus === 'testing' ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    测试中...
                                </>
                            ) : (
                                <>
                                    <PlugZap className="w-4 h-4 mr-2" />
                                    测试连接
                                </>
                            )}
                        </button>

                        {testStatus === 'success' && (
                            <span className="text-slate-900 dark:text-white text-sm flex items-center">
                                <CheckCircle2 className="w-4 h-4 mr-1" />
                                {testMessage}
                            </span>
                        )}

                        {testStatus === 'error' && (
                            <span className="text-slate-900 dark:text-white text-sm flex items-center">
                                <XCircle className="w-4 h-4 mr-1" />
                                {testMessage}
                            </span>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}
