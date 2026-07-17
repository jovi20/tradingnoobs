'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    ChevronLeft,
    ChevronRight,
    Calendar,
    TrendingUp,
    TrendingDown,
    Loader2,
    PenLine,
    Plus,
    Trash2,
    Send
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
    positionsAPI,
    journalAPI,
    JournalEntry,
} from '@/lib/api'
import { adaptPositions, PositionViewModel, TradeBatchViewModel } from '@/lib/adapters/trading'
import { useTrendColor } from '@/hooks/useTrendColor'
import { getCurrencySymbol } from '@/lib/symbolUtils'

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// 当日交易批次（包含所属 Position 信息）
interface DayBatch {
    batch: TradeBatchViewModel
    position: PositionViewModel
}

interface DayData {
    date: Date
    batches: DayBatch[]
    pnl: number
    isCurrentMonth: boolean
    isWeekend: boolean
}

export default function DailyPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [positions, setPositions] = useState<PositionViewModel[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [selectedDate, setSelectedDate] = useState<Date | null>(new Date()) // 默认今天

    // 随笔相关状态
    const [journalEntries, setJournalEntries] = useState<JournalEntry[]>([])
    const [newNote, setNewNote] = useState('')
    const [isSavingNote, setIsSavingNote] = useState(false)

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const positionsData = await positionsAPI.list(token)
                setPositions(adaptPositions(positionsData))
            } catch (err) {
                console.error(err)
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token])

    // 生成日历网格数据
    const generateCalendar = (): DayData[] => {
        const firstDay = new Date(year, month, 1)
        const lastDay = new Date(year, month + 1, 0)
        const startPadding = firstDay.getDay()
        const totalDays = lastDay.getDate()

        const days: DayData[] = []

        // 上月填充
        for (let i = startPadding - 1; i >= 0; i--) {
            const date = new Date(year, month, -i)
            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
                isWeekend: date.getDay() === 0 || date.getDay() === 6,
            })
        }

        // 当月
        for (let i = 1; i <= totalDays; i++) {
            const date = new Date(year, month, i)
            const isWeekend = date.getDay() === 0 || date.getDay() === 6

            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: true,
                isWeekend,
            })
        }

        // 下月填充
        const remaining = 42 - days.length
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i)
            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
                isWeekend: date.getDay() === 0 || date.getDay() === 6,
            })

        }

        return days
    }

    // 格式化本地日期为 YYYY-MM-DD
    const formatLocalDate = (date: Date): string => {
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
    }

    // 获取某日期的所有交易批次
    const getBatchesForDate = (date: Date): DayBatch[] => {
        const dateStr = formatLocalDate(date)
        const result: DayBatch[] = []

        positions.forEach(position => {
            position.batches?.forEach(batch => {
                const batchDateStr = new Date(batch.time).toLocaleDateString('sv-SE')
                if (batchDateStr === dateStr) {
                    result.push({ batch, position })
                }
            })
        })

        return result.sort((a, b) =>
            new Date(b.batch.time).getTime() - new Date(a.batch.time).getTime()
        )
    }

    const getPnlForDate = (date: Date): number => {
        const dayBatches = getBatchesForDate(date)
        return dayBatches.reduce((sum, { batch }) => sum + (Number(batch.pnl) || 0), 0)
    }

    const navigateMonth = (direction: 'prev' | 'next') => {
        setCurrentDate(new Date(year, month + (direction === 'next' ? 1 : -1), 1))
        setSelectedDate(null)
    }

    const isToday = (date: Date) => {
        const today = new Date()
        return date.toDateString() === today.toDateString()
    }

    const selectedDayData = selectedDate ? {
        date: selectedDate,
        batches: getBatchesForDate(selectedDate),
        pnl: getPnlForDate(selectedDate),
    } : null

    // 加载选中日期的随笔
    useEffect(() => {
        const loadJournalEntries = async () => {
            if (!token || !selectedDate) return
            try {
                const dateStr = formatLocalDate(selectedDate)
                const entries = await journalAPI.getByDate(token, dateStr)
                setJournalEntries(entries)
            } catch (err) {
                console.error('Failed to load journal entries:', err)
                setJournalEntries([])
            }
        }
        loadJournalEntries()
    }, [token, selectedDate])

    // 添加随笔
    const handleAddNote = async () => {
        if (!token || !selectedDate || !newNote.trim()) return
        if (journalEntries.length >= 5) {
            alert('每天最多只能添加5条随笔')
            return
        }
        try {
            setIsSavingNote(true)
            const dateStr = formatLocalDate(selectedDate)
            const entry = await journalAPI.create(token, { date: dateStr, content: newNote.trim() })
            setJournalEntries([entry, ...journalEntries])
            setNewNote('')
        } catch (err: any) {
            alert(err.message || '保存失败')
        } finally {
            setIsSavingNote(false)
        }
    }

    // 删除随笔
    const handleDeleteNote = async (id: number) => {
        if (!token) return
        try {
            await journalAPI.delete(token, id)
            setJournalEntries(journalEntries.filter(e => e.id !== id))
        } catch (err) {
            console.error('Failed to delete journal entry:', err)
        }
    }

    // 检查某个日期是否有随笔
    const hasJournalForDate = (date: Date): boolean => {
        // 这里简化处理，只检查当前选中日期
        if (selectedDate && date.toDateString() === selectedDate.toDateString()) {
            return journalEntries.length > 0
        }
        return false
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    const calendarDays = generateCalendar()

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <h1 className="text-2xl font-bold">日志日历</h1>
                <div className="flex items-center space-x-4">


                    {/* 月份导航 */}
                    <button
                        onClick={() => navigateMonth('prev')}
                        className="p-2 rounded-md hover:bg-panel-subtle"
                        aria-label="上一个月"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-lg font-semibold min-w-[120px] text-center tn-nums">
                        {year}年{month + 1}月
                    </span>
                    <button
                        onClick={() => navigateMonth('next')}
                        className="p-2 rounded-md hover:bg-panel-subtle"
                        aria-label="下一个月"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* 图例 */}
            <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border ${trendColor.isGreenUp ? 'bg-profit/15 border-profit/40' : 'bg-loss/15 border-loss/40'}`}></div>
                    <span className="text-ink-soft">盈利日</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border ${trendColor.isGreenUp ? 'bg-loss/15 border-loss/40' : 'bg-profit/15 border-profit/40'}`}></div>
                    <span className="text-ink-soft">亏损日</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-line-strong"></div>
                    <span className="text-ink-soft">周末</span>
                </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Calendar */}
                <div className="lg:col-span-2 rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                    {/* Week headers */}
                    <div className="grid grid-cols-7 mb-2">
                        {weekDays.map((day, index) => (
                            <div
                                key={day}
                                className={`text-center text-sm font-medium py-2 ${index === 0 || index === 6
                                    ? 'text-loss'
                                    : 'text-ink-muted'
                                    }`}
                            >
                                {day}
                            </div>
                        ))}
                    </div>

                    {/* Calendar grid */}
                    <div className="grid grid-cols-7 gap-1">
                        {calendarDays.map((day, index) => {
                            const hasTrades = day.batches.length > 0
                            const isPositive = day.pnl >= 0
                            const isSelected = selectedDate?.toDateString() === day.date.toDateString()
                            const dateLabel = day.date.toLocaleDateString('zh-CN', {
                                year: 'numeric',
                                month: 'long',
                                day: 'numeric',
                                weekday: 'long',
                            })
                            const tradeLabel = hasTrades
                                ? `，${day.batches.length} 笔交易，当日盈亏 ${isPositive ? '+' : ''}${day.pnl.toFixed(0)}`
                                : '，无交易'

                            return (
                                <button
                                    key={index}
                                    type="button"
                                    onClick={() => setSelectedDate(day.date)}
                                    aria-label={`${dateLabel}${tradeLabel}`}
                                    aria-pressed={isSelected}
                                    className={`
                                        min-h-[60px] md:min-h-[90px] p-1 md:p-2 rounded-md text-sm transition-all relative flex flex-col items-center justify-center gap-1
                                        ${!day.isCurrentMonth ? 'text-ink-faint' : ''}
                                        ${isToday(day.date) ? 'ring-2 ring-ink' : ''}
                                        ${isSelected ? 'bg-ink text-canvas' : 'hover:bg-panel-subtle'}
                                        ${day.isWeekend && !isSelected ? 'bg-panel-subtle' : ''}
                                        ${hasTrades && !isSelected ? (isPositive ? (trendColor.isGreenUp ? 'bg-profit/10' : 'bg-loss/10') : (trendColor.isGreenUp ? 'bg-loss/10' : 'bg-profit/10')) : ''}
                                    `}
                                >
                                    <span className="font-semibold tn-nums">{day.date.getDate()}</span>

                                    {/* 盈亏显示 */}
                                    {hasTrades && (
                                        <span className={`text-[10px] md:text-xs block truncate tn-nums ${isSelected ? 'text-canvas/80' : isPositive ? trendColor.upColor : trendColor.downColor}`}>
                                            {isPositive ? '+' : ''}{day.pnl.toFixed(0)}
                                        </span>
                                    )}
                                </button>
                            )
                        })}
                    </div>
                </div>

                {/* Day Detail */}
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold flex items-center space-x-2">
                        <Calendar className="w-5 h-5 text-ai" />
                        <span>
                            {selectedDayData
                                ? `${selectedDayData.date.getMonth() + 1}月${selectedDayData.date.getDate()}日`
                                : '选择日期查看详情'
                            }
                        </span>
                    </h2>

                    {selectedDayData ? (
                        <>
                            {/* Summary */}
                            <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-ink-muted">交易批次</p>
                                        <p className="text-xl font-bold tn-nums">{selectedDayData.batches.length}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-ink-muted">当日盈亏</p>
                                        <p className={`text-xl font-bold tn-nums ${selectedDayData.pnl >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                            {selectedDayData.pnl >= 0 ? '+' : ''}${selectedDayData.pnl.toFixed(2)}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Batch List */}
                            {selectedDayData.batches.length > 0 ? (
                                <div className="space-y-2">
                                    {selectedDayData.batches.map(({ batch, position }) => (
                                        <Link key={batch.id} href={`/positions/${position.routeId}`}>
                                            <div className="rounded-lg border border-line bg-panel p-4 shadow-panel transition-colors hover:border-line-strong dark:shadow-none cursor-pointer">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center space-x-3">
                                                        <div className={`w-8 h-8 rounded-md flex items-center justify-center ${batch.type === 'ENTRY'
                                                            ? 'bg-ai/10'
                                                            : (Number(batch.pnl) || 0) >= 0 ? trendColor.upBg : trendColor.downBg
                                                            }`}>
                                                            {batch.type === 'ENTRY' ? (
                                                                <TrendingUp className="w-4 h-4 text-ai" />
                                                            ) : (Number(batch.pnl) || 0) >= 0 ? (
                                                                <TrendingUp className={`w-4 h-4 ${trendColor.upColor}`} />
                                                            ) : (
                                                                <TrendingDown className={`w-4 h-4 ${trendColor.downColor}`} />
                                                            )}
                                                        </div>
                                                        <div>
                                                            <p className="font-medium">{position.symbol}</p>
                                                            <p className="text-xs text-ink-muted tn-nums">
                                                                {batch.type === 'ENTRY' ? '建仓' : '平仓'} · {Number(batch.quantity).toFixed(2)} 股 @ {getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.price).toFixed(2)}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    {batch.type === 'EXIT' && (
                                                        <p className={`font-bold tn-nums ${(Number(batch.pnl) || 0) >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                                            {(Number(batch.pnl) || 0) >= 0 ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.pnl || 0).toFixed(2)}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="rounded-lg border border-line bg-panel p-8 text-center text-ink-muted shadow-panel dark:shadow-none">
                                    当日无交易记录
                                </div>
                            )}

                            {/* 随笔区域 */}
                            <div className="rounded-lg border border-line bg-panel p-4 space-y-4 shadow-panel dark:shadow-none">
                                <div className="flex items-center gap-2">
                                    <PenLine className="w-5 h-5 text-ai" />
                                    <h3 className="font-semibold">随笔</h3>
                                    <span className="text-xs text-ink-faint">({journalEntries.length}/5)</span>
                                </div>

                                {/* 添加随笔 */}
                                {journalEntries.length < 5 && (
                                    <div className="space-y-2">
                                        <textarea
                                            value={newNote}
                                            onChange={(e) => setNewNote(e.target.value.slice(0, 500))}
                                            placeholder="记录今天的想法..."
                                            className="input resize-none"
                                            rows={3}
                                        />
                                        <div className="flex items-center justify-between">
                                            <span className="text-xs text-ink-faint tn-nums">{newNote.length}/500</span>
                                            <button
                                                onClick={handleAddNote}
                                                disabled={isSavingNote || !newNote.trim()}
                                                className="inline-flex items-center justify-center gap-1 rounded-md bg-ink px-3 py-1.5 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                {isSavingNote ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <Send className="w-4 h-4" />
                                                )}
                                                <span>保存</span>
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {/* 随笔列表 */}
                                {journalEntries.length > 0 ? (
                                    <div className="space-y-2">
                                        {journalEntries.map((entry) => (
                                            <div key={entry.id} className="p-3 bg-panel-subtle rounded-md group">
                                                <div className="flex items-start justify-between gap-2">
                                                    <p className="text-sm whitespace-pre-wrap flex-1">{entry.content}</p>
                                                    <button
                                                        onClick={() => handleDeleteNote(entry.id)}
                                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-loss/10 rounded text-loss transition-opacity"
                                                        title="删除"
                                                        aria-label="删除这条随笔"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                                <p className="text-xs text-ink-faint mt-1 tn-nums">
                                                    {new Date(entry.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-ink-faint text-center py-4">暂无随笔</p>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="rounded-lg border border-line bg-panel p-8 text-center text-ink-muted shadow-panel dark:shadow-none">
                            点击日历中的日期查看当日交易详情
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
