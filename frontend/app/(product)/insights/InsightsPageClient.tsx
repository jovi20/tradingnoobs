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
import { useEffectiveCapabilities } from '@/contexts/EffectiveCapabilitiesContext'
import ReactMarkdown from 'react-markdown'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { insightsAPI, WeeklyReport, AISummary, AnalysisType, AnalysisResponse, AnalysisHistoryItem } from '@/lib/api'
import { formatAnalysisDateRangeLabel, getDefaultAnalysisDateRange, validateAnalysisDateRange } from '@/lib/adapters/analysis'
import { downloadBlob } from '@/lib/download'
import { isEffectiveCapabilityEnabled } from '@/lib/effective-capabilities'
import { useTrendColor } from '@/hooks/useTrendColor'

// ============== 分析维度定义 ==============
const ANALYSIS_OPTIONS: { type: AnalysisType; label: string; icon: any; desc: string }[] = [
    { type: 'holding_period', label: '持仓时间', icon: BarChart3, desc: '分析不同持仓周期的盈亏表现' },
    { type: 'losing_streak', label: '连败模式', icon: TrendingDown, desc: '识别连续亏损的共同特征' },
    { type: 'emotion_pnl', label: '情绪关联', icon: Smile, desc: '分析开仓情绪对盈亏的影响' },
    { type: 'checklist_effect', label: '清单效果', icon: CheckSquare, desc: '对比检查清单执行的效果' },
    { type: 'strategy_health', label: '策略诊断', icon: Target, desc: '评估各策略的胜率与盈亏比' }
]

export default function InsightsPageClient() {
    const { token } = useAuth()
    const effectiveCapabilities = useEffectiveCapabilities()
    const canExportPdf = isEffectiveCapabilityEnabled(effectiveCapabilities, 'PDF_EXPORT')
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
    const [analysisDateRange, setAnalysisDateRange] = useState(() => getDefaultAnalysisDateRange())
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [analysisResultsMap, setAnalysisResultsMap] = useState<Partial<Record<AnalysisType, AnalysisResponse>>>({})
    const [analysisResultRangeLabelsMap, setAnalysisResultRangeLabelsMap] = useState<Partial<Record<AnalysisType, string>>>({})
    const [analysisHistory, setAnalysisHistory] = useState<AnalysisHistoryItem[]>([])
    const [isLoadingAnalysisHistory, setIsLoadingAnalysisHistory] = useState(true)
    const [analysisHistoryError, setAnalysisHistoryError] = useState('')
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

    const fetchAnalysisHistory = async () => {
        if (!token) return
        setAnalysisHistoryError('')
        try {
            setIsLoadingAnalysisHistory(true)
            const history = await insightsAPI.listAnalysisHistory(token, { limit: 5 })
            setAnalysisHistory(history)
        } catch (err: any) {
            setAnalysisHistoryError(err.message || '加载分析历史失败')
        } finally {
            setIsLoadingAnalysisHistory(false)
        }
    }

    const loadInitialInsightData = useEffectEvent(() => {
        fetchReports()
        fetchDailySummary()
        fetchPersistedAnalyses()
        fetchAnalysisHistory()
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
        const rangeError = validateAnalysisDateRange(analysisDateRange.startDate, analysisDateRange.endDate)
        if (rangeError) {
            setAnalysisError(rangeError)
            return
        }

        const rangeLabel = formatAnalysisDateRangeLabel(analysisDateRange.startDate, analysisDateRange.endDate)
        setIsAnalyzing(true)
        setAnalysisError('')
        try {
            const data = await insightsAPI.analyze(token, {
                analysis_type: selectedAnalysis,
                start_date: analysisDateRange.startDate,
                end_date: analysisDateRange.endDate,
            })
            setAnalysisResultsMap(prev => ({ ...prev, [selectedAnalysis]: data }))
            setAnalysisResultRangeLabelsMap(prev => ({ ...prev, [selectedAnalysis]: rangeLabel }))
            fetchAnalysisHistory()
        } catch (err: any) {
            setAnalysisError(err.message || '分析失败')
        } finally { setIsAnalyzing(false) }
    }

    // ============== 工具函数 ==============
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return `${date.getMonth() + 1}月${date.getDate()}日`
    }

    const getAnalysisOptionLabel = (type: string) =>
        ANALYSIS_OPTIONS.find(option => option.type === type)?.label || type

    const formatHistoryDateRange = (item: AnalysisHistoryItem) =>
        item.date_range ? item.date_range.label.replace(' to ', ' 至 ') : '未记录范围'

    const hasGeneratedInsightToday = reports.some(report => {
        const reportDate = new Date(report.created_at)
        const today = new Date()
        return reportDate.toDateString() === today.toDateString()
    })

    // ============== Loading Screen ==============
    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    // ============== 主渲染 ==============
    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* ====== Hero Header ====== */}
            <div className="relative overflow-hidden rounded-lg bg-ink p-6 md:p-8 text-canvas">
                {/* 背景装饰 */}
                <div className="absolute inset-0 opacity-10">
                    <div className="absolute -top-20 -right-20 w-60 h-60 rounded-full border-2 border-canvas/30" />
                    <div className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full border-2 border-canvas/20" />
                    <div className="absolute top-1/2 right-1/4 w-20 h-20 rounded-full bg-canvas/10" />
                </div>

                <div className="relative flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-lg bg-canvas/15 flex items-center justify-center border border-canvas/20">
                            <Brain className="w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold tracking-tight">AI 洞察</h1>
                            <p className="text-sm text-canvas/70 mt-0.5">交易行为分析 · 智能诊断 · 深度复盘</p>
                        </div>
                    </div>

                    <div className="flex gap-3">
                        {!dailySummary && !isLoadingSummary && (
                            <button
                                onClick={handleGenerateSummary}
                                disabled={isGeneratingSummary}
                                className="group px-5 py-2.5 rounded-md font-medium text-sm transition-colors bg-canvas/15 border border-canvas/20 hover:bg-canvas/25 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {isGeneratingSummary ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 group-hover:rotate-12 transition-transform" />}
                                <span>{isGeneratingSummary ? '生成中...' : '生成摘要'}</span>
                            </button>
                        )}
                        <button
                            onClick={handleGenerateReport}
                            disabled={isGenerating || hasGeneratedInsightToday}
                            className="group px-5 py-2.5 rounded-md font-medium text-sm transition-colors bg-canvas text-ink hover:bg-canvas/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4 text-ai group-hover:rotate-12 transition-transform" />}
                            <span>{isGenerating ? '分析中...' : hasGeneratedInsightToday ? '今日已生成' : '生成周报'}</span>
                        </button>
                    </div>
                </div>
            </div>

            <EvidenceLinkedInsightSidecar
                title="可审计洞察记录"
                runs={insightRunsQuery.data}
                isLoading={insightRunsQuery.isLoading}
                error={insightRunsQuery.error ? insightRunsQuery.error.message : null}
                limit={5}
                onRefresh={() => insightRunsQuery.refetch()}
            />

            {/* Error */}
            {error && (
                <div className="p-4 rounded-md bg-loss/10 text-loss text-sm">
                    {error}
                </div>
            )}

            {/* ====== 双栏主体 ====== */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

                {/* ====== 左侧主内容区 (3/5) ====== */}
                <div className="lg:col-span-3 space-y-6">

                    {/* --- 随笔摘要 --- */}
                    <div className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none overflow-hidden">
                        <div className="px-5 pt-5 pb-4 border-b border-line">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-md bg-panel-subtle flex items-center justify-center">
                                    <Brain className="w-4 h-4 text-ai" />
                                </div>
                                <div>
                                    <h3 className="font-semibold text-sm">随笔摘要</h3>
                                    <p className="text-xs text-ink-faint">近一周随笔 + 持仓变动摘要</p>
                                </div>
                            </div>
                        </div>
                        <div className="p-5">
                            {summaryError && (
                                <div className="p-3 rounded-md bg-loss/10 text-loss text-sm mb-4">{summaryError}</div>
                            )}
                            {isLoadingSummary ? (
                                <div className="flex items-center justify-center py-10">
                                    <Loader2 className="w-5 h-5 animate-spin text-ink-muted" />
                                </div>
                            ) : dailySummary ? (
                                <div>
                                    <LegacyInsightText label="旧版随笔摘要" content={dailySummary.content} />
                                    <p className="text-[11px] text-ink-faint mt-4 flex items-center gap-1">
                                        <Clock className="w-3 h-3" />
                                        生成于 {new Date(dailySummary.created_at).toLocaleString('zh-CN')}
                                    </p>
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <Brain className="w-10 h-10 text-ink-faint mx-auto mb-3" />
                                    <p className="text-sm text-ink-faint">点击顶部「生成摘要」按钮</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* --- AI 分析助手 (内联) --- */}
                    <div className="rounded-lg border border-ai/20 bg-panel shadow-panel dark:shadow-none !p-0 overflow-hidden">
                        {/* 标题 */}
                        <div className="px-5 py-4 bg-ai/5 border-b border-line">
                            <div className="flex items-center gap-3">
                                <div className="w-9 h-9 rounded-md bg-ai/10 flex items-center justify-center">
                                    <Brain className="w-4 h-4 text-ai" />
                                </div>
                                <div>
                                    <h2 className="font-bold text-sm">AI 分析助手</h2>
                                    <p className="text-xs text-ink-faint">选择维度，AI 诊断交易习惯并提供改进建议</p>
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
                                            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap border
                                                ${isSelected
                                                    ? 'bg-ai/10 border-ai text-ai ring-1 ring-ai'
                                                    : 'bg-panel border-line text-ink-muted hover:border-line-strong'}
                                                disabled:opacity-50 disabled:cursor-not-allowed
                                            `}
                                        >
                                            <Icon className="w-3.5 h-3.5" />
                                            {opt.label}
                                            {isSelected && isAnalyzing && <Loader2 className="w-3.5 h-3.5 animate-spin ml-1" />}
                                            {isSelected && !isAnalyzing && analysisResultsMap[opt.type] && (
                                                <span className="w-1.5 h-1.5 rounded-full bg-profit ml-1" title="已缓存" />
                                            )}
                                        </button>
                                    )
                                })}
                            </div>
                        </div>

                        {/* 日期范围 */}
                        <div className="px-5 pb-4">
                            <div className="rounded-lg border border-line bg-panel-subtle p-3">
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                    <label className="space-y-1 text-xs font-medium text-ink-muted">
                                        <span>开始日期</span>
                                        <input
                                            type="date"
                                            value={analysisDateRange.startDate}
                                            onChange={(event) => setAnalysisDateRange(prev => ({ ...prev, startDate: event.target.value }))}
                                            className="w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink-soft outline-none transition-colors focus:border-ai focus:ring-2 focus:ring-ai/20 tn-nums"
                                        />
                                    </label>
                                    <label className="space-y-1 text-xs font-medium text-ink-muted">
                                        <span>结束日期</span>
                                        <input
                                            type="date"
                                            value={analysisDateRange.endDate}
                                            onChange={(event) => setAnalysisDateRange(prev => ({ ...prev, endDate: event.target.value }))}
                                            className="w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink-soft outline-none transition-colors focus:border-ai focus:ring-2 focus:ring-ai/20 tn-nums"
                                        />
                                    </label>
                                </div>
                                <p className="mt-2 flex items-center gap-1 text-[11px] text-ink-faint">
                                    <Calendar className="w-3 h-3" />
                                    当前分析范围：{formatAnalysisDateRangeLabel(analysisDateRange.startDate, analysisDateRange.endDate)}
                                </p>
                            </div>
                        </div>

                        {/* 分析结果区 */}
                        <div className="p-5 min-h-[300px]">
                            {(() => {
                                const cachedResult = selectedAnalysis ? analysisResultsMap[selectedAnalysis] : null

                                if (!selectedAnalysis) return (
                                    <div className="h-full flex flex-col items-center justify-center py-12 text-ink-faint">
                                        <Brain className="w-12 h-12 mb-3 opacity-15" />
                                        <p className="text-sm">请选择一个分析维度开始</p>
                                    </div>
                                )

                                if (isAnalyzing) return (
                                    <div className="h-full flex flex-col items-center justify-center py-12 text-ai">
                                        <Loader2 className="w-10 h-10 animate-spin mb-4" />
                                        <p className="font-medium text-sm">AI 正在分析您的交易数据...</p>
                                        <p className="text-xs text-ink-faint mt-1">通常需要 10-20 秒</p>
                                    </div>
                                )

                                if (analysisError) return (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-center py-8 text-loss bg-loss/10 rounded-md border border-loss/30">
                                            <p className="text-sm">{analysisError}</p>
                                        </div>
                                        <div className="flex justify-center">
                                            <button onClick={handleRunAnalysis} className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-5 py-2.5 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                                                <Sparkles className="w-4 h-4" /> 重试
                                            </button>
                                        </div>
                                    </div>
                                )

                                if (cachedResult) return (
                                    <div className="space-y-5">
                                        {/* 操作栏 */}
                                        <div className="flex items-center justify-between">
                                            <p className="text-[11px] text-ink-faint flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                生成于 {new Date(cachedResult.created_at).toLocaleString('zh-CN')}
                                                <span className="hidden sm:inline">·</span>
                                                <span>{analysisResultRangeLabelsMap[selectedAnalysis] || '最近一次分析'}</span>
                                            </p>
                                            <button
                                                onClick={handleRunAnalysis}
                                                disabled={isAnalyzing}
                                                className="px-4 py-1.5 rounded-md text-xs font-medium bg-ai/10 text-ai hover:bg-ai/20 transition-colors flex items-center gap-1.5 border border-ai/20"
                                            >
                                                <Sparkles className="w-3 h-3" /> 重新生成
                                            </button>
                                        </div>
                                        {/* 图表 */}
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-ink-faint mb-3">数据可视化</h3>
                                            <div className="bg-panel-subtle rounded-md p-4 border border-line">
                                                <LegacyAnalysisChart result={cachedResult} compact />
                                            </div>
                                        </div>
                                        {/* AI 诊断文字 */}
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-ai mb-3 flex items-center gap-1.5">
                                                <Sparkles className="w-3.5 h-3.5" /> AI 深度诊断
                                            </h3>
                                            <LegacyInsightText label="旧版分析正文" content={cachedResult.ai_insights || '暂无分析结论'} />
                                        </div>
                                    </div>
                                )

                                // 选中了维度但无缓存 → 显示生成按钮
                                return (
                                    <div className="h-full flex flex-col items-center justify-center py-12">
                                        <Brain className="w-12 h-12 text-ink-faint mb-4" />
                                        <p className="text-sm text-ink-faint mb-1">
                                            {ANALYSIS_OPTIONS.find(o => o.type === selectedAnalysis)?.desc}
                                        </p>
                                        <p className="text-xs text-ink-faint">
                                            范围：{formatAnalysisDateRangeLabel(analysisDateRange.startDate, analysisDateRange.endDate)}
                                        </p>
                                        <button
                                            onClick={handleRunAnalysis}
                                            disabled={isAnalyzing}
                                            className="mt-4 inline-flex items-center justify-center gap-2 rounded-md bg-ink px-6 py-2.5 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft"
                                        >
                                            <Sparkles className="w-4 h-4" /> 生成分析
                                        </button>
                                    </div>
                                )
                            })()}
                        </div>
                    </div>

                    {/* --- AI 分析历史 --- */}
                    <div className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none overflow-hidden">
                        <div className="px-5 py-4 border-b border-line flex items-center justify-between">
                            <div>
                                <h2 className="font-bold text-sm flex items-center gap-2">
                                    <Clock className="w-4 h-4 text-ai" />
                                    近期分析记录
                                </h2>
                                <p className="text-xs text-ink-faint mt-1">可追溯、可复访的洞察记录</p>
                            </div>
                            <button
                                onClick={fetchAnalysisHistory}
                                disabled={isLoadingAnalysisHistory}
                                className="rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-ink-muted transition-colors hover:border-line-strong hover:text-ai disabled:opacity-50"
                            >
                                刷新
                            </button>
                        </div>
                        <div className="p-5 space-y-3">
                            {analysisHistoryError && (
                                <div className="rounded-md border border-loss/30 bg-loss/10 px-3 py-2 text-xs font-medium text-loss">
                                    {analysisHistoryError}
                                </div>
                            )}
                            {isLoadingAnalysisHistory ? (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="w-5 h-5 animate-spin text-ink-muted" />
                                </div>
                            ) : analysisHistory.length > 0 ? (
                                analysisHistory.map(item => (
                                    <a
                                        key={item.artifact_public_id}
                                        href={item.href}
                                        className="group block rounded-lg border border-line bg-panel-subtle p-4 transition-colors hover:border-line-strong hover:bg-panel"
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <p className="text-xs font-bold text-ai">{getAnalysisOptionLabel(item.analysis_type)}</p>
                                                <h3 className="mt-1 truncate text-sm font-semibold text-ink">{item.title}</h3>
                                                <p className="mt-1 line-clamp-2 text-xs text-ink-muted">{item.summary}</p>
                                                <p className="mt-2 text-[11px] text-ink-faint tn-nums">
                                                    {formatHistoryDateRange(item)} · {new Date(item.created_at).toLocaleDateString('zh-CN')}
                                                </p>
                                            </div>
                                            <ArrowRight className="mt-1 w-4 h-4 shrink-0 text-ink-faint transition-transform group-hover:translate-x-0.5 group-hover:text-ai" />
                                        </div>
                                    </a>
                                ))
                            ) : (
                                <div className="rounded-lg border border-dashed border-line p-6 text-center text-sm text-ink-faint">
                                    暂无历史分析，生成一次后会出现在这里。
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* ====== 右侧周报栏 (2/5) ====== */}
                <div className="lg:col-span-2">
                    <div className="lg:sticky lg:top-6 space-y-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-base font-bold flex items-center gap-2">
                                <Calendar className="w-4 h-4 text-ai" />
                                周报历史
                            </h2>
                            <span className="text-xs text-ink-faint tn-nums">{reports.length} 份报告</span>
                        </div>

                        {reports.length === 0 ? (
                            <div className="rounded-lg border border-line bg-panel p-8 text-center shadow-panel dark:shadow-none">
                                <FileText className="w-12 h-12 text-ink-faint mx-auto mb-3" />
                                <p className="text-sm text-ink-faint mb-4">暂无周报洞察</p>
                                <button
                                    onClick={handleGenerateReport}
                                    disabled={isGenerating}
                                    className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50 disabled:cursor-not-allowed"
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
                                        <div key={report.id} className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none overflow-hidden">
                                            {/* 报告头部 */}
                                            <div
                                                className="w-full px-4 py-3 flex items-center justify-between hover:bg-panel-subtle transition-colors"
                                            >
                                                <button
                                                    onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                                    className="min-w-0 flex flex-1 items-center gap-3 text-left"
                                                >
                                                    <div className="w-9 h-9 rounded-md bg-panel-subtle flex items-center justify-center shrink-0">
                                                        <FileText className="w-4 h-4 text-ai" />
                                                    </div>
                                                    <div className="min-w-0">
                                                        <h3 className="font-semibold text-sm tn-nums">
                                                            {formatDate(report.week_start)} - {formatDate(report.week_end)}
                                                        </h3>
                                                        <p className="text-[11px] text-ink-faint tn-nums">
                                                            {new Date(report.created_at).toLocaleDateString('zh-CN')}
                                                        </p>
                                                    </div>
                                                </button>
                                                <div className="flex items-center gap-2">
                                                    {canExportPdf && (
                                                        <button
                                                            onClick={() => handleExportReport(report.id)}
                                                            disabled={isExporting}
                                                            className="inline-flex items-center gap-1.5 rounded-full border border-line bg-panel px-2.5 py-1.5 text-[11px] font-semibold text-ink-soft transition-colors hover:border-line-strong hover:text-ai disabled:cursor-not-allowed disabled:opacity-60"
                                                        >
                                                            {isExporting
                                                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                                : <Download className="w-3.5 h-3.5" />
                                                            }
                                                            <span>PDF</span>
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                                        className="rounded-full p-1.5 text-ink-faint transition-colors hover:bg-panel-subtle hover:text-ink-soft"
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
                                                <div className="mx-4 mb-3 rounded-md border border-loss/30 bg-loss/10 px-3 py-2 text-[11px] font-medium text-loss">
                                                    {exportError}
                                                </div>
                                            )}

                                            {/* 展开的报告内容 */}
                                            {isExpanded && (
                                                <div className="px-4 pb-4 space-y-3 border-t border-line pt-3">
                                                    {report.trades_summary && (
                                                        <ReportSection
                                                            icon={<TrendingUp className="w-3.5 h-3.5 text-ai" />}
                                                            title="交易回顾"
                                                            content={report.trades_summary}
                                                            bgClass="bg-ai/10"
                                                        />
                                                    )}
                                                    {report.munger_evaluation && (
                                                        <ReportSection
                                                            icon={<Sparkles className="w-3.5 h-3.5 text-warning" />}
                                                            title="芒格视角"
                                                            content={report.munger_evaluation}
                                                            bgClass="bg-warning/10"
                                                        />
                                                    )}
                                                    {report.suggestions && (
                                                        <ReportSection
                                                            icon={<TrendingUp className="w-3.5 h-3.5 text-profit" />}
                                                            title="改进建议"
                                                            content={report.suggestions}
                                                            bgClass="bg-profit/10"
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
        <div className={`p-3 ${bgClass} rounded-md`}>
            <h4 className="font-medium text-xs mb-2 flex items-center gap-1.5">
                {icon}
                <span>{title}</span>
            </h4>
            <div className="prose prose-xs dark:prose-invert max-w-none text-ink-soft text-[13px] leading-relaxed">
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
        <div className={`rounded-md border border-warning/30 bg-warning/10 ${compact ? 'p-2.5' : 'p-4'}`}>
            <p className="text-[10px] font-black uppercase tracking-[0.18em] text-warning">
                旧版未关联输出 · {label}
            </p>
            <p className="mt-1 text-xs leading-5 text-warning">
                仅作历史读取；新的 AI 展示以可审计产物、证据引用和可信元数据为准。
            </p>
            <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-ink-soft">
                {content}
            </pre>
        </div>
    )
}
