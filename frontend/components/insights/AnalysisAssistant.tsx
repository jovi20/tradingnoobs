
'use client'

import { useState } from 'react'
import {
    Brain,
    Loader2,
    BarChart3,
    TrendingDown,
    Smile,
    CheckSquare,
    Target,
    ArrowRight
} from 'lucide-react'
import { LegacyAnalysisChart } from '@/components/insights/LegacyAnalysisChart'
import { insightsAPI, AnalysisType, AnalysisResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'
import ReactMarkdown from 'react-markdown'

const ANALYSIS_OPTIONS: { type: AnalysisType; label: string; icon: any; desc: string }[] = [
    {
        type: 'holding_period',
        label: '持仓时间分析',
        icon: BarChart3,
        desc: '分析不同持仓周期的盈亏表现，寻找最佳持仓时长。'
    },
    {
        type: 'losing_streak',
        label: '连败模式分析',
        icon: TrendingDown,
        desc: '识别连续亏损的共同特征，提供止损建议。'
    },
    {
        type: 'emotion_pnl',
        label: '情绪-绩效关联',
        icon: Smile,
        desc: '分析开仓情绪对最终盈亏的影响。'
    },
    {
        type: 'checklist_effect',
        label: '检查清单效果',
        icon: CheckSquare,
        desc: '对比执行检查清单与未执行的交易表现。'
    },
    {
        type: 'strategy_health',
        label: '策略表现诊断',
        icon: Target,
        desc: '综合评估各策略的胜率与盈亏比趋势。'
    }
]

export default function AnalysisAssistant() {
    const { token } = useAuth()
    const [selectedType, setSelectedType] = useState<AnalysisType | null>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [result, setResult] = useState<AnalysisResponse | null>(null)
    const [error, setError] = useState('')

    const handleAnalyze = async (type: AnalysisType) => {
        if (!token) return
        setSelectedType(type)
        setIsLoading(true)
        setError('')
        setResult(null)

        try {
            const data = await insightsAPI.analyze(token, { analysis_type: type })
            setResult(data)
        } catch (err: any) {
            setError(err.message || '分析失败')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="card !p-0 overflow-hidden border border-indigo-100 dark:border-indigo-900/30">
            {/* Header */}
            <div className="p-6 bg-gradient-to-r from-indigo-500/5 to-purple-500/5 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                        <Brain className="w-5 h-5 text-white" />
                    </div>
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">AI 分析助手</h2>
                        <p className="text-sm text-slate-500">
                            选择一个维度，AI 将为您诊断交易习惯并提供改进建议
                        </p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left: Options */}
                <div className="space-y-3">
                    {ANALYSIS_OPTIONS.map((opt) => {
                        const Icon = opt.icon
                        const isSelected = selectedType === opt.type
                        return (
                            <button
                                key={opt.type}
                                onClick={() => handleAnalyze(opt.type)}
                                disabled={isLoading}
                                className={`w-full text-left p-3 rounded-xl transition-all border
                                    ${isSelected
                                        ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-500 ring-1 ring-indigo-500'
                                        : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700'}
                                `}
                            >
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center space-x-3">
                                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-indigo-500 text-white' : 'bg-slate-100 dark:bg-slate-700 text-slate-500'}`}>
                                            <Icon className="w-4 h-4" />
                                        </div>
                                        <div>
                                            <div className={`font-medium ${isSelected ? 'text-indigo-700 dark:text-indigo-300' : 'text-slate-700 dark:text-slate-300'}`}>
                                                {opt.label}
                                            </div>
                                            <div className="text-xs text-slate-400 line-clamp-1">{opt.desc}</div>
                                        </div>
                                    </div>
                                    {isSelected && isLoading && <Loader2 className="w-4 h-4 animate-spin text-indigo-500" />}
                                    {isSelected && !isLoading && <ArrowRight className="w-4 h-4 text-indigo-500" />}
                                </div>
                            </button>
                        )
                    })}
                </div>

                {/* Right: Results */}
                <div className="lg:col-span-2 bg-slate-50 dark:bg-slate-900/50 rounded-2xl p-6 min-h-[400px]">
                    {!selectedType ? (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400">
                            <Brain className="w-12 h-12 mb-4 opacity-20" />
                            <p>请点击左侧选项开始分析</p>
                        </div>
                    ) : isLoading ? (
                        <div className="h-full flex flex-col items-center justify-center text-indigo-500">
                            <Loader2 className="w-10 h-10 animate-spin mb-4" />
                            <p className="font-medium">AI 正在分析您的交易数据...</p>
                            <p className="text-xs text-slate-400 mt-2">通常需要 10-20 秒</p>
                        </div>
                    ) : error ? (
                        <div className="h-full flex items-center justify-center text-red-500 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/30">
                            <p>{error}</p>
                        </div>
                    ) : result ? (
                        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                            {/* Chart Section */}
                            <div>
                                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-2">数据可视化</h3>
                                <div className="bg-white dark:bg-slate-800 rounded-xl p-4 shadow-sm border border-slate-100 dark:border-slate-700">
                                    <LegacyAnalysisChart result={result} />
                                </div>
                            </div>

                            {/* AI Insights Section */}
                            <div>
                                <h3 className="text-sm font-bold uppercase tracking-wider text-indigo-500 mb-2 flex items-center gap-2">
                                    <Sparkles className="w-4 h-4" />
                                    AI 深度诊断
                                </h3>
                                <div className="bg-white dark:bg-slate-800 rounded-xl p-6 shadow-sm border border-slate-100 dark:border-slate-700 prose prose-sm dark:prose-invert max-w-none break-words whitespace-pre-wrap">
                                    <ReactMarkdown>{result.ai_insights || '暂无分析结论'}</ReactMarkdown>
                                </div>
                            </div>
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    )
}

function Sparkles(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
            <path d="M5 3v4" />
            <path d="M9 3v4" />
            <path d="M2 7h4" />
            <path d="M2 11h4" />
        </svg>
    )
}
