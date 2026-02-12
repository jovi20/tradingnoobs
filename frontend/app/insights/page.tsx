'use client'

import { useState, useEffect } from 'react'
import {
    FileText,
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
import { useAuth } from '@/contexts/AuthContext'
import ReactMarkdown from 'react-markdown'
import { insightsAPI, WeeklyReport, AISummary, AnalysisType, AnalysisResponse } from '@/lib/api'
import { useTrendColor } from '@/hooks/useTrendColor'
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts'

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

    // 周报状态
    const [reports, setReports] = useState<WeeklyReport[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isGenerating, setIsGenerating] = useState(false)
    const [expandedReport, setExpandedReport] = useState<number | null>(null)
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

    useEffect(() => {
        fetchReports()
        fetchDailySummary()
        fetchPersistedAnalyses()
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

    // ============== 图表渲染 ==============
    const renderChart = () => {
        const currentResult = selectedAnalysis ? analysisResultsMap[selectedAnalysis] : null
        if (!currentResult || !currentResult.raw_data) return null

        if (currentResult.raw_data.stats) {
            const chartData = Object.entries(currentResult.raw_data.stats).map(([key, val]: any) => ({
                name: key,
                pnl: val.avg_pnl,
                win_rate: (val.win_rate * 100).toFixed(1),
                count: val.count
            }))
            return (
                <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                            <XAxis dataKey="name" fontSize={11} />
                            <YAxis fontSize={11} />
                            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                            <Bar dataKey="pnl" name="平均盈亏" radius={[4, 4, 0, 0]}>
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#34d399' : '#f87171'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )
        }

        if (currentResult.analysis_type === 'checklist_effect') {
            const d1 = currentResult.raw_data.checklist_completed
            const d2 = currentResult.raw_data.checklist_ignored
            const chartData = [
                { name: '已执行清单', pnl: d1?.avg_pnl || 0, count: d1?.count || 0 },
                { name: '未执行/未完成', pnl: d2?.avg_pnl || 0, count: d2?.count || 0 }
            ]
            return (
                <div className="h-56 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                            <XAxis dataKey="name" fontSize={11} />
                            <YAxis fontSize={11} />
                            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                            <Bar dataKey="pnl" name="平均盈亏" radius={[4, 4, 0, 0]}>
                                {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#34d399' : '#f87171'} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )
        }
        return null
    }

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
                                    <div className="prose prose-sm dark:prose-invert max-w-none">
                                        <ReactMarkdown>{dailySummary.content}</ReactMarkdown>
                                    </div>
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
                                                {renderChart()}
                                            </div>
                                        </div>
                                        {/* AI 诊断文字 */}
                                        <div>
                                            <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-500 mb-3 flex items-center gap-1.5">
                                                <Sparkles className="w-3.5 h-3.5" /> AI 深度诊断
                                            </h3>
                                            <div className="bg-slate-50 dark:bg-slate-900/50 rounded-xl p-5 border border-slate-100 dark:border-slate-800 prose prose-sm dark:prose-invert max-w-none break-words overflow-hidden">
                                                <ReactMarkdown>{cachedResult.ai_insights || '暂无分析结论'}</ReactMarkdown>
                                            </div>
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
                                    return (
                                        <div key={report.id} className="card overflow-hidden">
                                            {/* 报告头部 */}
                                            <button
                                                onClick={() => setExpandedReport(isExpanded ? null : report.id)}
                                                className="w-full px-4 py-3 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shrink-0">
                                                        <FileText className="w-4 h-4 text-white" />
                                                    </div>
                                                    <div className="text-left">
                                                        <h3 className="font-semibold text-sm">
                                                            {formatDate(report.week_start)} - {formatDate(report.week_end)}
                                                        </h3>
                                                        <p className="text-[11px] text-slate-400">
                                                            {new Date(report.created_at).toLocaleDateString('zh-CN')}
                                                        </p>
                                                    </div>
                                                </div>
                                                {isExpanded
                                                    ? <ChevronUp className="w-4 h-4 text-slate-400 shrink-0" />
                                                    : <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
                                                }
                                            </button>

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
                <ReactMarkdown>{content}</ReactMarkdown>
            </div>
        </div>
    )
}
