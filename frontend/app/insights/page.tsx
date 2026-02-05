'use client'

import { useState, useEffect } from 'react'
import {
    FileText,
    Calendar,
    TrendingUp,
    TrendingDown,
    Sparkles,
    ChevronDown,
    ChevronUp,
    Loader2,
    Brain
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { insightsAPI, WeeklyReport, AISummary } from '@/lib/api'
import ReactMarkdown from 'react-markdown'

export default function ReportsPage() {
    const { token } = useAuth()
    const [reports, setReports] = useState<WeeklyReport[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isGenerating, setIsGenerating] = useState(false)
    const [expandedReport, setExpandedReport] = useState<number | null>(null)
    const [error, setError] = useState('')

    // Daily Summary states
    const [dailySummary, setDailySummary] = useState<AISummary | null>(null)
    const [isLoadingSummary, setIsLoadingSummary] = useState(true)
    const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
    const [summaryError, setSummaryError] = useState('')

    const fetchReports = async () => {
        if (!token) return
        try {
            setIsLoading(true)
            const data = await insightsAPI.list(token)
            setReports(data)
            if (data.length > 0) {
                setExpandedReport(data[0].id)
            }
        } catch (err) {
            console.error(err)
        } finally {
            setIsLoading(false)
        }
    }

    const fetchDailySummary = async () => {
        if (!token) return
        try {
            setIsLoadingSummary(true)
            const summary = await insightsAPI.getTodaySummary(token)
            setDailySummary(summary)
        } catch (err) {
            console.error(err)
        } finally {
            setIsLoadingSummary(false)
        }
    }

    useEffect(() => {
        fetchReports()
        fetchDailySummary()
    }, [token])

    const handleGenerateReport = async () => {
        if (!token) return
        setError('')
        setIsGenerating(true)
        try {
            const newReport = await insightsAPI.generateCurrentWeek(token)
            setReports([newReport, ...reports])
            setExpandedReport(newReport.id)
        } catch (err: any) {
            setError(err.message || '生成洞察失败，请确保已配置 LLM API')
        } finally {
            setIsGenerating(false)
        }
    }

    const handleGenerateSummary = async () => {
        if (!token) return
        setSummaryError('')
        setIsGeneratingSummary(true)
        try {
            const summary = await insightsAPI.generateSummary(token)
            setDailySummary(summary)
        } catch (err: any) {
            setSummaryError(err.message || '生成总结失败')
        } finally {
            setIsGeneratingSummary(false)
        }
    }

    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return `${date.getMonth() + 1}月${date.getDate()}日`
    }

    // Check if insight already generated today
    const hasGeneratedInsightToday = reports.some(report => {
        const reportDate = new Date(report.created_at)
        const today = new Date()
        return reportDate.toDateString() === today.toDateString()
    })


    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h1 className="text-2xl font-bold">AI 洞察</h1>
                <div className="flex gap-3 w-full sm:w-auto">
                    {!dailySummary && !isLoadingSummary && (
                        <button
                            onClick={handleGenerateSummary}
                            disabled={isGeneratingSummary}
                            className={`
                            relative group overflow-hidden px-6 py-3 rounded-xl font-medium transition-all
                            ${isGeneratingSummary
                                    ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                                    : 'bg-indigo-600 dark:bg-indigo-500 text-white hover:shadow-lg hover:shadow-indigo-500/20 active:scale-95'}
                            flex items-center justify-center space-x-2 flex-1 sm:flex-none
                        `}
                        >
                            {isGeneratingSummary ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Sparkles className="w-5 h-5 text-white/80 group-hover:rotate-12 transition-transform" />
                            )}
                            <span>{isGeneratingSummary ? '生成中...' : 'Summary'}</span>
                        </button>
                    )}
                    <button
                        onClick={handleGenerateReport}
                        disabled={isGenerating || hasGeneratedInsightToday}
                        className={`
                        relative group overflow-hidden px-6 py-3 rounded-xl font-medium transition-all
                        ${isGenerating || hasGeneratedInsightToday
                                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed'
                                : 'bg-slate-900 dark:bg-white text-white dark:text-slate-900 hover:shadow-lg hover:shadow-primary-500/20 active:scale-95'}
                        flex items-center justify-center space-x-2 flex-1 sm:flex-none
                    `}
                    >
                        {!isGenerating && !hasGeneratedInsightToday && (
                            <div className="absolute inset-0 bg-gradient-to-r from-primary-500/10 to-accent-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                        )}
                        {isGenerating ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Sparkles className="w-5 h-5 text-primary-400 group-hover:rotate-12 transition-transform" />
                        )}
                        <span>{isGenerating ? '正在深度分析中...' : hasGeneratedInsightToday ? '今日已生成' : 'Insight'}</span>
                    </button>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Daily Summary Card */}
            <div className="card overflow-hidden">
                <div className="p-6 bg-gradient-to-r from-violet-500/10 to-purple-500/10">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center">
                                <Brain className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h3 className="font-semibold">随笔摘要</h3>
                                <p className="text-sm text-slate-500">近一周随笔 + 持仓变动摘要</p>
                            </div>
                        </div>
                    </div>

                    {summaryError && (
                        <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 text-sm mb-4">
                            {summaryError}
                        </div>
                    )}

                    {isLoadingSummary ? (
                        <div className="flex items-center justify-center py-8">
                            <Loader2 className="w-6 h-6 animate-spin text-violet-500" />
                        </div>
                    ) : dailySummary ? (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                            <ReactMarkdown>{dailySummary.content}</ReactMarkdown>
                            <p className="text-xs text-slate-400 mt-4">
                                生成于 {new Date(dailySummary.created_at).toLocaleString('zh-CN')}
                            </p>
                        </div>
                    ) : (
                        <p className="text-slate-500 text-center py-4">
                            点击顶部 Summary 按钮生成摘要
                        </p>
                    )}
                </div>
            </div>

            {/* Reports List */}
            {reports.length === 0 ? (
                <div className="card p-12 text-center">
                    <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500 mb-4">暂无周报洞察</p>
                    <p className="text-sm text-slate-400 mb-6">
                        点击上方按钮生成本周的 AI 交易洞察
                    </p>
                    <button
                        onClick={handleGenerateReport}
                        disabled={isGenerating}
                        className="btn btn-primary inline-flex items-center space-x-2"
                    >
                        <Sparkles className="w-5 h-5" />
                        <span>生成第一份洞察</span>
                    </button>
                </div>
            ) : (
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold">周报历史</h2>
                    {reports.map((report) => {
                        const isExpanded = expandedReport === report.id

                        return (
                            <div key={report.id} className="card overflow-hidden">
                                {/* Header */}
                                <button
                                    onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                    className="w-full p-6 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                >
                                    <div className="flex items-center space-x-4">
                                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                                            <FileText className="w-6 h-6 text-white" />
                                        </div>
                                        <div className="text-left">
                                            <h3 className="font-semibold">
                                                {formatDate(report.week_start)} - {formatDate(report.week_end)}
                                            </h3>
                                            <p className="text-sm text-slate-500">
                                                生成于 {new Date(report.created_at).toLocaleString('zh-CN')}
                                            </p>
                                        </div>
                                    </div>
                                    {isExpanded ? (
                                        <ChevronUp className="w-5 h-5 text-slate-400" />
                                    ) : (
                                        <ChevronDown className="w-5 h-5 text-slate-400" />
                                    )}
                                </button>

                                {/* Content */}
                                {isExpanded && (
                                    <div className="px-6 pb-6 space-y-4">
                                        {/* Trades Summary */}
                                        {report.trades_summary && (
                                            <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-xl">
                                                <h4 className="font-medium mb-2 flex items-center space-x-2">
                                                    <TrendingUp className="w-4 h-4 text-primary-500" />
                                                    <span>交易回顾</span>
                                                </h4>
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-slate-600 dark:text-slate-400">
                                                    <ReactMarkdown>{report.trades_summary}</ReactMarkdown>
                                                </div>
                                            </div>
                                        )}

                                        {/* Munger Evaluation */}
                                        {report.munger_evaluation && (
                                            <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-xl">
                                                <h4 className="font-medium mb-2 flex items-center space-x-2">
                                                    <Sparkles className="w-4 h-4 text-amber-500" />
                                                    <span>芒格视角评估</span>
                                                </h4>
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-slate-600 dark:text-slate-400">
                                                    <ReactMarkdown>{report.munger_evaluation}</ReactMarkdown>
                                                </div>
                                            </div>
                                        )}

                                        {/* Suggestions */}
                                        {report.suggestions && (
                                            <div className="p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl">
                                                <h4 className="font-medium mb-2 flex items-center space-x-2">
                                                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                                                    <span>改进建议</span>
                                                </h4>
                                                <div className="prose prose-sm dark:prose-invert max-w-none text-slate-600 dark:text-slate-400">
                                                    <ReactMarkdown>{report.suggestions}</ReactMarkdown>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
