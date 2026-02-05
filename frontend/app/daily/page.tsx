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
    Ban,
    PenLine,
    Plus,
    Trash2,
    Send
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI, marketAPI, journalAPI, Position, TradeBatch, MarketCalendar, MarketHoliday, JournalEntry } from '@/lib/api'
import { useTrendColor } from '@/hooks/useTrendColor'

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

// 当日交易批次（包含所属 Position 信息）
interface DayBatch {
    batch: TradeBatch
    position: Position
}

interface DayData {
    date: Date
    batches: DayBatch[]
    pnl: number
    isCurrentMonth: boolean
    isHoliday: boolean
    holidayName?: string
    isWeekend: boolean
    isTradingDay: boolean
}

export default function DailyPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [positions, setPositions] = useState<Position[]>([])
    const [calendar, setCalendar] = useState<MarketCalendar | null>(null)
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
                const [positionsData, cnCalendar, usCalendar, hkCalendar] = await Promise.all([
                    positionsAPI.list(token),
                    marketAPI.calendar(token, 'CN', year, month + 1),
                    marketAPI.calendar(token, 'US', year, month + 1),
                    marketAPI.calendar(token, 'HK', year, month + 1)
                ])
                setPositions(positionsData)

                // Merge Calendars
                const mergedCalendar: MarketCalendar = {
                    market: 'MERGED',
                    year,
                    month,
                    holidays: [],
                    trading_days: [],
                    non_trading_days: []
                }

                // Merge Trading Days (Union)
                const tradingDaysSet = new Set([
                    ...(cnCalendar?.trading_days || []),
                    ...(usCalendar?.trading_days || []),
                    ...(hkCalendar?.trading_days || [])
                ])
                mergedCalendar.trading_days = Array.from(tradingDaysSet)

                // Merge Holidays
                const holidayMap = new Map<string, string[]>()

                cnCalendar?.holidays?.forEach(h => {
                    const existing = holidayMap.get(h.date) || []
                    if (!existing.some(e => e.includes('A股'))) existing.push(`[A股] ${h.name}`)
                    holidayMap.set(h.date, existing)
                })

                hkCalendar?.holidays?.forEach(h => {
                    const existing = holidayMap.get(h.date) || []
                    if (!existing.some(e => e.includes('港股'))) existing.push(`[港股] ${h.name}`)
                    holidayMap.set(h.date, existing)
                })

                usCalendar?.holidays?.forEach(h => {
                    const existing = holidayMap.get(h.date) || []
                    if (!existing.some(e => e.includes('美股'))) existing.push(`[美股] ${h.name}`)
                    holidayMap.set(h.date, existing)
                })

                mergedCalendar.holidays = Array.from(holidayMap.entries()).map(([date, names]) => ({
                    date,
                    name: names.join(' / '),
                    is_trading: false
                }))

                setCalendar(mergedCalendar)

            } catch (err) {
                console.error(err)
                try {
                    const positionsData = await positionsAPI.list(token)
                    setPositions(positionsData)
                } catch { }
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token, year, month])

    // 生成日历网格数据
    const generateCalendar = (): DayData[] => {
        const firstDay = new Date(year, month, 1)
        const lastDay = new Date(year, month + 1, 0)
        const startPadding = firstDay.getDay()
        const totalDays = lastDay.getDate()

        // 创建节假日映射
        const holidayMap = new Map<string, MarketHoliday>()
        const tradingDaySet = new Set(calendar?.trading_days || [])
        const nonTradingDaySet = new Set(calendar?.non_trading_days || [])

        calendar?.holidays?.forEach(h => {
            holidayMap.set(h.date, h)
        })

        const days: DayData[] = []

        // 上月填充
        for (let i = startPadding - 1; i >= 0; i--) {
            const date = new Date(year, month, -i)
            const dateStr = formatLocalDate(date)
            const holiday = holidayMap.get(dateStr)
            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
                isHoliday: !!holiday,
                holidayName: holiday?.name,
                isWeekend: date.getDay() === 0 || date.getDay() === 6,
                isTradingDay: tradingDaySet.has(dateStr),
            })
        }

        // 当月
        for (let i = 1; i <= totalDays; i++) {
            const date = new Date(year, month, i)
            const dateStr = formatLocalDate(date)
            const holiday = holidayMap.get(dateStr)
            const isWeekend = date.getDay() === 0 || date.getDay() === 6

            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: true,
                isHoliday: !!holiday,
                holidayName: holiday?.name,
                isWeekend,
                isTradingDay: tradingDaySet.has(dateStr),
            })
        }

        // 下月填充
        const remaining = 42 - days.length
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i)
            const dateStr = formatLocalDate(date)
            const holiday = holidayMap.get(dateStr)
            days.push({
                date,
                batches: getBatchesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
                isHoliday: !!holiday,
                holidayName: holiday?.name,
                isWeekend: date.getDay() === 0 || date.getDay() === 6,
                isTradingDay: tradingDaySet.has(dateStr),
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
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    const calendarDays = generateCalendar()

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
                <h1 className="text-2xl font-bold">交易日历</h1>
                <div className="flex items-center space-x-4">


                    {/* 月份导航 */}
                    <button
                        onClick={() => navigateMonth('prev')}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-lg font-semibold min-w-[120px] text-center">
                        {year}年{month + 1}月
                    </span>
                    <button
                        onClick={() => navigateMonth('next')}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        <ChevronRight className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* 图例 */}
            <div className="flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border ${trendColor.isGreenUp ? 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300' : 'bg-red-100 dark:bg-red-900/30 border-red-300'}`}></div>
                    <span className="text-slate-600 dark:text-slate-400">盈利日</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded border ${trendColor.isGreenUp ? 'bg-red-100 dark:bg-red-900/30 border-red-300' : 'bg-emerald-100 dark:bg-emerald-900/30 border-emerald-300'}`}></div>
                    <span className="text-slate-600 dark:text-slate-400">亏损日</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-slate-200 dark:bg-slate-700"></div>
                    <span className="text-slate-600 dark:text-slate-400">周末</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-orange-100 dark:bg-orange-900/30 border border-orange-300 flex items-center justify-center">
                        <span className="text-orange-500 text-[8px]">●</span>
                    </div>
                    <span className="text-slate-600 dark:text-slate-400">节假日</span>
                </div>
            </div>

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Calendar */}
                <div className="lg:col-span-2 card p-4">
                    {/* Week headers */}
                    <div className="grid grid-cols-7 mb-2">
                        {weekDays.map((day, index) => (
                            <div
                                key={day}
                                className={`text-center text-sm font-medium py-2 ${index === 0 || index === 6
                                    ? 'text-red-400'
                                    : 'text-slate-500'
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
                            const isNonTrading = day.isWeekend || day.isHoliday

                            return (
                                <button
                                    key={index}
                                    onClick={() => setSelectedDate(day.date)}
                                    title={day.holidayName || undefined}
                                    className={`
                                        min-h-[60px] md:min-h-[90px] p-1 md:p-2 rounded-xl text-sm transition-all relative flex flex-col items-center justify-center gap-1
                                        ${!day.isCurrentMonth ? 'text-slate-300 dark:text-slate-600' : ''}
                                        ${isToday(day.date) ? 'ring-2 ring-primary-500' : ''}
                                        ${isSelected ? 'bg-primary-500 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-700'}
                                        ${day.isWeekend && !isSelected ? 'bg-slate-100 dark:bg-slate-800' : ''}
                                        ${day.isHoliday && !isSelected ? 'bg-orange-50 dark:bg-orange-900/20' : ''}
                                        ${hasTrades && !isSelected && !isNonTrading ? (isPositive ? (trendColor.isGreenUp ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20') : (trendColor.isGreenUp ? 'bg-red-50 dark:bg-red-900/20' : 'bg-emerald-50 dark:bg-emerald-900/20')) : ''}
                                    `}
                                >
                                    <span className="font-semibold">{day.date.getDate()}</span>

                                    {/* 节假日标记 */}
                                    {day.isHoliday && !isSelected && (
                                        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-orange-400"></span>
                                    )}

                                    {/* 盈亏显示 */}
                                    {hasTrades && (
                                        <span className={`text-[10px] md:text-xs block truncate ${isSelected ? 'text-white/80' : isPositive ? trendColor.upColor : trendColor.downColor}`}>
                                            {isPositive ? '+' : ''}{day.pnl.toFixed(0)}
                                        </span>
                                    )}

                                    {/* 节假日名称（手机隐藏） */}
                                    {day.isHoliday && day.holidayName && !hasTrades && (
                                        <div className={`hidden md:flex flex-col items-center w-full px-1 gap-0.5 overflow-hidden ${isSelected ? 'text-white/70' : 'text-orange-500'}`}>
                                            {day.holidayName.split(' / ').map((name, i) => (
                                                <span key={i} className="text-[9px] leading-tight truncate w-full text-center" title={name}>
                                                    {name}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </button>
                            )
                        })}
                    </div>
                </div>

                {/* Day Detail */}
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold flex items-center space-x-2">
                        <Calendar className="w-5 h-5 text-primary-500" />
                        <span>
                            {selectedDayData
                                ? `${selectedDayData.date.getMonth() + 1}月${selectedDayData.date.getDate()}日`
                                : '选择日期查看详情'
                            }
                        </span>
                    </h2>

                    {selectedDayData ? (
                        <>
                            {/* 节假日提示 */}
                            {(() => {
                                const dateStr = formatLocalDate(selectedDayData.date)
                                const holiday = calendar?.holidays?.find(h => h.date === dateStr)
                                const isWeekend = selectedDayData.date.getDay() === 0 || selectedDayData.date.getDay() === 6

                                if (holiday) {
                                    return (
                                        <div className="card p-4 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800">
                                            <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
                                                <Ban className="w-5 h-5" />
                                                <span className="font-medium">{holiday.name} - 休市</span>
                                            </div>
                                        </div>
                                    )
                                } else if (isWeekend) {
                                    return (
                                        <div className="card p-4 bg-slate-100 dark:bg-slate-800">
                                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                                                <Ban className="w-5 h-5" />
                                                <span>周末休市</span>
                                            </div>
                                        </div>
                                    )
                                }
                                return null
                            })()}

                            {/* Summary */}
                            <div className="card p-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <p className="text-sm text-slate-500">交易批次</p>
                                        <p className="text-xl font-bold">{selectedDayData.batches.length}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-slate-500">当日盈亏</p>
                                        <p className={`text-xl font-bold ${selectedDayData.pnl >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                            {selectedDayData.pnl >= 0 ? '+' : ''}${selectedDayData.pnl.toFixed(2)}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Batch List */}
                            {selectedDayData.batches.length > 0 ? (
                                <div className="space-y-2">
                                    {selectedDayData.batches.map(({ batch, position }) => (
                                        <Link key={batch.id} href={`/positions/${position.id}`}>
                                            <div className="card p-4 hover:scale-[1.02] transition-transform cursor-pointer">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center space-x-3">
                                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${batch.type === 'ENTRY'
                                                                ? 'bg-blue-100 dark:bg-blue-900/30'
                                                                : (Number(batch.pnl) || 0) >= 0 ? trendColor.upBg : trendColor.downBg
                                                            }`}>
                                                            {batch.type === 'ENTRY' ? (
                                                                <TrendingUp className="w-4 h-4 text-blue-500" />
                                                            ) : (Number(batch.pnl) || 0) >= 0 ? (
                                                                <TrendingUp className={`w-4 h-4 ${trendColor.upColor}`} />
                                                            ) : (
                                                                <TrendingDown className={`w-4 h-4 ${trendColor.downColor}`} />
                                                            )}
                                                        </div>
                                                        <div>
                                                            <p className="font-medium">{position.symbol}</p>
                                                            <p className="text-xs text-slate-500">
                                                                {batch.type === 'ENTRY' ? '建仓' : '平仓'} · {Number(batch.quantity).toFixed(2)} 股 @ ${Number(batch.price).toFixed(2)}
                                                            </p>
                                                        </div>
                                                    </div>
                                                    {batch.type === 'EXIT' && (
                                                        <p className={`font-bold ${(Number(batch.pnl) || 0) >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                                            {(Number(batch.pnl) || 0) >= 0 ? '+' : ''}${Number(batch.pnl || 0).toFixed(2)}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                        </Link>
                                    ))}
                                </div>
                            ) : (
                                <div className="card p-8 text-center text-slate-500">
                                    当日无交易记录
                                </div>
                            )}

                            {/* 随笔区域 */}
                            <div className="card p-4 space-y-4">
                                <div className="flex items-center gap-2">
                                    <PenLine className="w-5 h-5 text-primary-500" />
                                    <h3 className="font-semibold">随笔</h3>
                                    <span className="text-xs text-slate-400">({journalEntries.length}/5)</span>
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
                                            <span className="text-xs text-slate-400">{newNote.length}/500</span>
                                            <button
                                                onClick={handleAddNote}
                                                disabled={isSavingNote || !newNote.trim()}
                                                className="btn btn-primary btn-sm flex items-center gap-1"
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
                                            <div key={entry.id} className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg group">
                                                <div className="flex items-start justify-between gap-2">
                                                    <p className="text-sm whitespace-pre-wrap flex-1">{entry.content}</p>
                                                    <button
                                                        onClick={() => handleDeleteNote(entry.id)}
                                                        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/20 rounded text-red-500 transition-opacity"
                                                        title="删除"
                                                    >
                                                        <Trash2 className="w-4 h-4" />
                                                    </button>
                                                </div>
                                                <p className="text-xs text-slate-400 mt-1">
                                                    {new Date(entry.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-400 text-center py-4">暂无随笔</p>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="card p-8 text-center text-slate-500">
                            点击日历中的日期查看当日交易详情
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
