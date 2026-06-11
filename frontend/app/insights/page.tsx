'use client'

import { useEffect, useEffectEvent, useState } from 'react'
import {
    FileText,
    Download,
    TrendingUp,
    TrendingDown,
    Sparkles,
    ChevronDown,
    ChevronUp,
    Loader2,
    Brain,
    BarChart3,
    Smile,
    CheckSquare,
    Target,
    ArrowRight,
    Calendar,
    Clock
} from 'lucide-react'
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { LegacyAnalysisChart } from '@/components/insights/LegacyAnalysisChart'
import { useAuth } from '@/contexts/AuthContext'
import ReactMarkdown from 'react-markdown'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { insightsAPI, WeeklyReport, AISummary, AnalysisType, AnalysisResponse } from '@/lib/api'
import { downloadBlob } from '@/lib/download'
import { useTrendColor } from '@/hooks/useTrendColor'

// ============== 分析维度定义 ==============
const ANALYSIS_OPTIONS: { type: AnalysisType; label: string; icon: any; desc: string }[] = [
    { type: 'holding_period', label: '持仓时间', icon: BarChart3, desc: '分析不同持仓周期的盈亏表现' },
    { type: 'losing_streak', label: '连败模式', icon: TrendingDown, desc: '识别连续亏损的共同特征' },
    { type: 'emotion_pnl', label: '情绪关联', icon: Smile, desc: '分析开仓情绪对盈亏的影响' },
    { type: 'checklist_effect', label: '清单效果', icon: CheckSquare, desc: '对比检查清单执行的效果' },
    { type: 'strategy_health', label: '策略诊断', icon: Target, desc: '评估各策略的胜率与盈亏比' }
]

export default function InsightsPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const insightRunsQuery = useInsightRuns(token)

    // 周报状态
    const [reports, setReports] = useState<WeeklyReport[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isGenerating, setIsGenerating] = useState(false)
    const [expandedReport, setExpandedReport] = useState<number | null>(null)
    const [exportingReportId, setExportingReportId] = useState<number | null>(null)
    const [exportErrors, setExportErrors] = useState<Record<number, string>>({})
    const [error, setError] = useState('')

    // 随笔摘要状态
    const [dailySummary, setDailySummary] = useState<AISummary | null>(null)
    const [isLoadingSummary, setIsLoadingSummary] = useState(true)
    const [isGeneratingSummary, setIsGeneratingSummary] = useState(false)
    const [summaryError, setSummaryError] = useState('')

    // AI 分析助手状态
    const [selectedAnalysis, setSelectedAnalysis] = useState<AnalysisType | null>(null)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [analysisResultsMap, setAnalysisResultsMap] = useState<Partial<Record<AnalysisType, AnalysisResponse>>>({})
    const [analysisError, setAnalysisError] = useState('')

    // ============== 数据获取 ==============
    const fetchReports = async () => {
        if (!token) return
        try {
            setIsLoading(true)
            const data = await insightsAPI.list(token)
            setReports(data)
            if (data.length > 0) setExpandedReport(data[0].id)
        } catch (err) { console.error(err) }
        finally { setIsLoading(false) }
    }

    const fetchDailySummary = async () => {
        if (!token) return
        try {
            setIsLoadingSummary(true)
            const summary = await insightsAPI.getTodaySummary(token)
            setDailySummary(summary)
        } catch (err) { console.error(err) }
        finally { setIsLoadingSummary(false) }
    }

    const fetchPersistedAnalyses = async () => {
        if (!token) return
        const promises = ANALYSIS_OPTIONS.map(async (opt) => {
            try {
                const res = await insightsAPI.getLatestAnalysis(token, opt.type)
                if (res) {
                    setAnalysisResultsMap(prev => ({ ...prev, [opt.type]: res }))
                }
            } catch (err) {
                console.warn(`Failed to fetch analysis for ${opt.type}`, err)
            }
        })
        await Promise.all(promises)
    }

    const loadInitialInsightData = useEffectEvent(() => {
        fetchReports()
        fetchDailySummary()
        fetchPersistedAnalyses()
    })

    useEffect(() => {
        if (!token) return
        const loadTimer = window.setTimeout(() => {
            loadInitialInsightData()
        }, 0)
        return () => window.clearTimeout(loadTimer)
    }, [token])

    // ============== 操作处理 ==============
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
        } finally { setIsGenerating(false) }
    }

    const handleExportReport = async (reportId: number) => {
        if (!token) return
        setExportingReportId(reportId)
        setExportErrors(prev => ({ ...prev, [reportId]: '' }))

        try {
            const { blob, filename } = await insightsAPI.exportWeeklyReportPdf(token, reportId)
            downloadBlob(filename, blob)
        } catch (err: any) {
            setExportErrors(prev => ({ ...prev, [reportId]: err.message || '导出 PDF 失败' }))
        } finally {
            setExportingReportId(prev => prev === reportId ? null : prev)
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
        } finally { setIsGeneratingSummary(false) }
    }

    const handleSelectAnalysis = (type: AnalysisType) => {
        setSelectedAnalysis(type)
        setAnalysisError('')
    }

    const handleRunAnalysis = async () => {
        if (!token || !selectedAnalysis) return
        setIsAnalyzing(true)
        setAnalysisError('')
        try {
            const data = await insightsAPI.analyze(token, { analysis_type: selectedAnalysis })
            setAnalysisResultsMap(prev => ({ ...prev, [selectedAnalysis]: data }))
        } catch (err: any) {
            setAnalysisError(err.message || '分析失败')
        } finally { setIsAnalyzing(false) }
    }

    // ============== 工具函数 ==============
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return `${date.getMonth() + 1}月${date.getDate()}日`
    }

    const hasGeneratedInsightToday = reports.some(report => {
        const reportDate = new Date(report.created_at)
        const today = new Date()
        return reportDate.toDateString() === today.toDateString()
    })

    // ============== Loading Screen ==============
    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            </div>
        )
    }

    // ============== 主渲染 ==============
    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* ====== Hero Header ====== */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 via-purple-600 to-violet-700 p-6 md:p-8 text-white shadow-xl shadow-indigo-500/10">
                {/* 背景装饰 */}
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute -top-20 -right-20 w-60 h-60 rounded-full border-2 border-white/30" />
                    <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full border-2 border-white/20" />
                    <div className="absolute top-1/2 right-1/4 w-20 h-20 rounded-full bg-white/10" />
                </div>

                <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center border border-white/20">
                            <Brain className="w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold tracking-tight">AI 洞察</h1>
                            <p className="text-sm text-white/70 mt-0.5">交易行为分析 · 智能诊断 · 深度复盘</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        {!dailySummary && !isLoadingSummary && (
                            <button
                                onClick={handleGenerateSummary}
                                disabled={isGeneratingSummary}
                                className="group px-5 py-2.5 rounded-xl font-medium text-sm transition-all bg-white/15 backdrop-blur-sm border border-white/20 hover:bg-white/25 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isGeneratingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />}
                                <span>{isGeneratingSummary ? '生成中...' : '生成摘要'}</span>
                            </button>
                        )}
                        <button
                            onClick={handleGenerateReport}
                            disabled={isGenerating || hasGeneratedInsightToday}
                            className="group px-5 py-2.5 rounded-xl font-medium text-sm transition-all bg-white text-indigo-700 hover:bg-white/90 hover:shadow-lg active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-indigo-500 group-hover:rotate-12 transition-transform" />}
                            <span>{isGenerating ? '分析中...' : hasGeneratedInsightToday ? '今日已生成' : '生成周报'}</span>
                        </button>
                    </div>
                </div>
            </div>

            <EvidenceLinkedInsightSidecar
                title="Auditable Insight Artifacts"
                runs={insightRunsQuery.data}
                isLoading={insightRunsQuery.isLoading}
                error={insightRunsQuery.error ? insightRunsQuery.error.message : null}
                limit={5}
                onRefresh={() => insightRunsQuery.refetch()}
            />

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600 text-sm">
                    {error}
                </div>
            )}

            {/* ====== 双栏主体 ====== */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

                {/* ====== 左侧主内容区 (3/5) ====== */}
                <div className="lg:col-span-3 space-y-6">

                    {/* --- 随笔摘要 --- */}
                    <div className="card overflow-hidden">
                        <div className="px-5 pt-5 pb-4 border-b border-slate-100 dark:border-slate-800">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-500 flex items-center justify-center shadow-sm">
                                    <Brain className="w-4 h-4 text-white" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-sm">随笔摘要</h3>
                                    <p className="text-xs text-slate-400">近一周随笔 + 持仓变动摘要</p>
                                </div>
                            </div>
                        </div>
                        <div className="p-5">
                            {summaryError && (
                                <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-600 text-sm mb-4">{summaryError}</div>
                            )}
                            {isLoadingSummary ? (
                                <div className="flex items-center justify-center py-10">
                                    <Loader2 className="w-5 h-5 animate-spin text-violet-500" />
                                </div>
                            ) : dailySummary ? (
                                <div>
                                    <LegacyInsightText label="旧版随笔摘要" content={dailySummary.content} />
                                    <p className="text-[11px] text-slate-400 mt-4 flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        生成于 {new Date(dailySummary.created_at).toLocaleString('zh-CN')}
                                    </p>
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <Brain className="w-10 h-10 text-slate-200 dark:text-slate-700 mx-auto mb-3" />
                                    <p className="text-sm text-slate-400">点击顶部「生成摘要」按钮</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* --- AI 分析助手 (内联) --- */}
                    <div className="card !p-0 overflow-hidden border border-indigo-100 dark:border-indigo-900/30">
                        {/* 标题 */}
                        <div className="px-5 py-4 bg-gradient-to-r from-indigo-500/5 to-purple-500/5 border-b border-slate-100 dark:border-slate-800">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                                    <Brain className="w-4 h-4 text-white" />
                                </div>
                                <div>
                                    <h2 className="font-bold text-sm">AI 分析助手</h2>
                                    <p className="text-xs text-slate-400">选择维度，AI 诊断交易习惯并提供改进建议</p>
                                </div>
                            </div>
                        </div>

                        {/* 水平 Tab 栏 */}
                        <div className="px-5 pt-4 pb-2 overflow-x-auto">
                            <div className="flex gap-2 min-w-max">
                                {ANALYSIS_OPTIONS.map((opt) => {
                                    const Icon = opt.icon
                                    const isSelected = selectedAnalysis === opt.type
                                    return (
                                        <button
                                            key={opt.type}
                                            onClick={() => handleSelectAnalysis(opt.type)}
                                            disabled={isAnalyzing}
                                            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all whitespace-nowrap border
                                                ${isSelected
                                                    ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-500 text-indigo-700 dark:text-indigo-300 ring-1 ring-indigo-500'
                                                    : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-indigo-300 dark:hover:border-indigo-700'}
                                                disabled:opacity-50 disabled:cursor-not-allowed
                                            `}
                                        >
                                            <Icon className="w-3.5 h-3.5" />
                                            {opt.label}
                                            {isSelected && isAnalyzing && <Loader2 className="w-3.5 h-3.5 animate-spin ml-1" />}
                                            {isSelected && !isAnalyzing && analysisResultsMap[opt.type] && (
                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 ml-1" title="已缓存" />
                                            )}
                                        </button>
                                    )
                                })}
                            </div>
                        </div>

                        {/* 分析结果区 */}
                        <div className="p-5 min-h-[300px]">
                            {(() => {
                                const cachedResult = selectedAnalysis ? analysisResultsMap[selectedAnalysis] : null

                                if (!selectedAnalysis) return (
                                    <div className="h-full flex flex-col items-center justify-center py-12 text-slate-400">
                                        <Brain className="w-12 h-12 mb-3 opacity-15" />
                                        <p className="text-sm">请选择一个分析维度开始</p>
                                    </div>
                                )

                                if (isAnalyzing) return (
                                    <div className="h-full flex flex-col items-center justify-center py-12 text-indigo-500">
                                        <Loader2 className="w-10 h-10 animate-spin mb-4" />
                                        <p className="font-medium text-sm">AI 正在分析您的交易数据...</p>
                                        <p className="text-xs text-slate-400 mt-1">通常需要 10-20 秒</p>
                                    </div>
                                )

                                if (analysisError) return (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-center py-8 text-red-500 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/30">
                                            <p className="text-sm">{analysisError}</p>
                                        </div>
                                        <div className="flex justify-center">
                                            <button onClick={handleRunAnalysis} className="px-5 py-2.5 rounded-xl font-medium text-sm bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 transition-all flex items-center gap-2">
                                                <Sparkles className="w-4 h-4" /> 重试
                                            </button>
                                        </div>
                                    </div>
                                )

                                if (cachedResult) return (
                                    <div className="space-y-5">
                                        {/* 操作栏 */}
                                        <div className="flex items-center justify-between">
                                            <p className="text-[11px] text-slate-400 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                生成于 {new Date(cachedResult.created_at).toLocaleString('zh-CN')}
                                            </p>
                                            <button
                                                onClick={handleRunAnalysis}
                                                disabled={isAnalyzing}
                                                className="px-4 py-1.5 rounded-lg text-xs font-medium bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 transition-all flex items-center gap-1.5 border border-indigo-200 dark:border-indigo-800"
                                            >
                                                <Sparkles className="w-3 h-3" /> 重新生成
                                            </button>
                                        </div>
                                        {/* 图表 */}
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">数据可视化</h3>
                                            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-4 border border-slate-100 dark:border-slate-800">
                                                <LegacyAnalysisChart result={cachedResult} compact />
                                            </div>
                                        </div>
                                        {/* AI 诊断文字 */}
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-500 mb-3 flex items-center gap-1.5">
                                                <Sparkles className="w-3.5 h-3.5" /> AI 深度诊断
                                            </h3>
                                            <LegacyInsightText label="旧版分析正文" content={cachedResult.ai_insights || '暂无分析结论'} />
                                        </div>
                                    </div>
                                )

                                // 选中了维度但无缓存 → 显示生成按钮
                                return (
                                    <div className="h-full flex flex-col items-center justify-center py-12">
                                        <Brain className="w-12 h-12 text-slate-200 dark:text-slate-700 mb-4" />
                                        <p className="text-sm text-slate-400 mb-1">
                                            {ANALYSIS_OPTIONS.find(o => o.type === selectedAnalysis)?.desc}
                                        </p>
                                        <button
                                            onClick={handleRunAnalysis}
                                            disabled={isAnalyzing}
                                            className="mt-4 px-6 py-2.5 rounded-xl font-medium text-sm bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 transition-all flex items-center gap-2 shadow-lg shadow-indigo-500/20"
                                        >
                                            <Sparkles className="w-4 h-4" /> 生成分析
                                        </button>
                                    </div>
                                )
                            })()}
                        </div>
                    </div>
                </div>

                {/* ====== 右侧周报栏 (2/5) ====== */}
                <div className="lg:col-span-2">
                    <div className="lg:sticky lg:top-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-base font-bold flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-indigo-500" />
                                周报历史
                            </h2>
                            <span className="text-xs text-slate-400">{reports.length} 份报告</span>
                        </div>

                        {reports.length === 0 ? (
                            <div className="card p-8 text-center">
                                <FileText className="w-12 h-12 text-slate-200 dark:text-slate-700 mx-auto mb-3" />
                                <p className="text-sm text-slate-400 mb-4">暂无周报洞察</p>
                                <button
                                    onClick={handleGenerateReport}
                                    disabled={isGenerating}
                                    className="btn btn-primary inline-flex items-center gap-2 text-sm"
                                >
                                    <Sparkles className="w-4 h-4" />
                                    <span>生成第一份</span>
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-3 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1 scrollbar-thin">
                                {reports.map((report) => {
                                    const isExpanded = expandedReport === report.id
                                    const isExporting = exportingReportId === report.id
                                    const exportError = exportErrors[report.id]
                                    return (
                                        <div key={report.id} className="card overflow-hidden">
                                            {/* 报告头部 */}
                                            <div
                                                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                            >
                                                <button
                                                    onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                                    className="min-w-0 flex flex-1 items-center gap-3 text-left"
                                                >
                                                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shrink-0">
                                                        <FileText className="w-4 h-4 text-white" />
                                                    </div>
                                                    <div className="min-w-0">
                                                        <h3 className="font-semibold text-sm">
                                                            {formatDate(report.week_start)} - {formatDate(report.week_end)}
                                                        </h3>
                                                        <p className="text-[11px] text-slate-400">
                                                            {new Date(report.created_at).toLocaleDateString('zh-CN')}
                                                        </p>
                                                    </div>
                                                </button>
                                                <div className="flex items-center gap-2">
                                                    <button
                                                        onClick={() => handleExportReport(report.id)}
                                                        disabled={isExporting}
                                                        className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 shadow-sm transition-all hover:border-indigo-200 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-indigo-500/50 dark:hover:text-indigo-300"
                                                    >
                                                        {isExporting
                                                            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                            : <Download className="w-3.5 h-3.5" />
                                                        }
                                                        <span>PDF</span>
                                                    </button>
                                                    <button
                                                        onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                                        className="rounded-full p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800 dark:hover:text-slate-200"
                                                        aria-label={isExpanded ? '收起周报' : '展开周报'}
                                                    >
                                                        {isExpanded
                                                            ? <ChevronUp className="w-4 h-4 shrink-0" />
                                                            : <ChevronDown className="w-4 h-4 shrink-0" />
                                                        }
                                                    </button>
                                                </div>
                                            </div>
                                            {exportError && (
                                                <div className="mx-4 mb-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-[11px] font-medium text-rose-600 dark:border-rose-900/60 dark:bg-rose-950/30 dark:text-rose-300">
                                                    {exportError}
                                                </div>
                                            )}

                                            {/* 展开的报告内容 */}
                                            {isExpanded && (
                                                <div className="px-4 pb-4 space-y-3 border-t border-slate-100 dark:border-slate-800 pt-3">
                                                    {report.trades_summary && (
                                                        <ReportSection
                                                            icon={<TrendingUp className="w-3.5 h-3.5 text-blue-500" />}
                                                            title="交易回顾"
                                                            content={report.trades_summary}
                                                            bgClass="bg-blue-50 dark:bg-blue-900/10"
                                                        />
                                                    )}
                                                    {report.munger_evaluation && (
                                                        <ReportSection
                                                            icon={<Sparkles className="w-3.5 h-3.5 text-amber-500" />}
                                                            title="芒格视角"
                                                            content={report.munger_evaluation}
                                                            bgClass="bg-amber-50 dark:bg-amber-900/10"
                                                        />
                                                    )}
                                                    {report.suggestions && (
                                                        <ReportSection
                                                            icon={<TrendingUp className="w-3.5 h-3.5 text-emerald-500" />}
                                                            title="改进建议"
                                                            content={report.suggestions}
                                                            bgClass="bg-emerald-50 dark:bg-emerald-900/10"
                                                        />
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}

// ============== 子组件 ==============

function ReportSection({ icon, title, content, bgClass }: {
    icon: React.ReactNode
    title: string
    content: string
    bgClass: string
}) {
    return (
        <div className={`p-3 ${bgClass} rounded-xl`}>
            <h4 className="font-medium text-xs mb-2 flex items-center gap-1.5">
                {icon}
                <span>{title}</span>
            </h4>
            <div className="prose prose-xs dark:prose-invert max-w-none text-slate-600 dark:text-slate-400 text-[13px] leading-relaxed">
                <LegacyInsightText label={`旧版${title}`} content={content} compact />
            </div>
        </div>
    )
}

function LegacyInsightText({
    label,
    content,
    compact = false,
}: {
    label: string
    content: string
    compact?: boolean
}) {
    return (
        <div className={`rounded-xl border border-amber-200/70 bg-amber-50/80 dark:border-amber-500/20 dark:bg-amber-500/10 ${compact ? 'p-2.5' : 'p-4'}`}>
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-amber-700 dark:text-amber-200">
                Legacy unlinked output · {label}
            </p>
            <p className="mt-1 text-xs leading-5 text-amber-800 dark:text-amber-100">
                仅作历史读取；新的 AI 展示以 auditable artifacts、evidence refs 和 trust meta 为准。
            </p>
            <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-700 dark:text-slate-200">
                {content}
            </pre>
        </div>
    )
}
