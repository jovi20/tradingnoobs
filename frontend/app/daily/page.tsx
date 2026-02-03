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
    Ban
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { tradesAPI, marketAPI, Trade, MarketCalendar, MarketHoliday } from '@/lib/api'

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

interface DayData {
    date: Date
    trades: Trade[]
    pnl: number
    isCurrentMonth: boolean
    isHoliday: boolean
    holidayName?: string
    isWeekend: boolean
    isTradingDay: boolean
}

export default function DailyPage() {
    const { token } = useAuth()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [trades, setTrades] = useState<Trade[]>([])
    const [calendar, setCalendar] = useState<MarketCalendar | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [selectedDate, setSelectedDate] = useState<Date | null>(null)

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const [tradesData, cnCalendar, usCalendar] = await Promise.all([
                    tradesAPI.list(token),
                    marketAPI.calendar(token, 'CN', year, month + 1),
                    marketAPI.calendar(token, 'US', year, month + 1)
                ])
                setTrades(tradesData)

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
                    ...(usCalendar?.trading_days || [])
                ])
                mergedCalendar.trading_days = Array.from(tradingDaysSet)

                // Merge Holidays
                const holidayMap = new Map<string, string[]>()

                cnCalendar?.holidays?.forEach(h => {
                    const existing = holidayMap.get(h.date) || []
                    existing.push(`[A股] ${h.name}`)
                    holidayMap.set(h.date, existing)
                })

                usCalendar?.holidays?.forEach(h => {
                    const existing = holidayMap.get(h.date) || []
                    existing.push(`[美股] ${h.name}`)
                    holidayMap.set(h.date, existing)
                })

                mergedCalendar.holidays = Array.from(holidayMap.entries()).map(([date, names]) => ({
                    date,
                    name: names.join(' / '),
                    is_trading: false // simplified, specialized logic might be needed but good for display
                }))

                // Non-trading days: Only if NOT in trading set (Intersection of non-trading effectively, or simpler: complement of Union of Trading)
                // For simplicity just leave empty as we drive logic via trading_days set mostly

                setCalendar(mergedCalendar)

            } catch (err) {
                console.error(err)
                // Fallback to basic trades data
                try {
                    const tradesData = await tradesAPI.list(token)
                    setTrades(tradesData)
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
                trades: getTradesForDate(date),
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
                trades: getTradesForDate(date),
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
                trades: getTradesForDate(date),
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

    const getTradesForDate = (date: Date): Trade[] => {
        const dateStr = formatLocalDate(date)
        return trades.filter((trade) => {
            // 已平仓交易：使用平仓日期；持仓中：使用入场日期
            const tradeDateStr = trade.status === 'CLOSED' && trade.exit_time
                ? new Date(trade.exit_time).toLocaleDateString('sv-SE')  // sv-SE 格式: YYYY-MM-DD
                : new Date(trade.entry_time).toLocaleDateString('sv-SE')
            return tradeDateStr === dateStr
        })
    }

    const getPnlForDate = (date: Date): number => {
        const dayTrades = getTradesForDate(date)
        return dayTrades.reduce((sum, trade) => sum + (trade.pnl || 0), 0)
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
        trades: getTradesForDate(selectedDate),
        pnl: getPnlForDate(selectedDate),
    } : null

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
                    <div className="w-4 h-4 rounded bg-emerald-100 dark:bg-emerald-900/30 border border-emerald-300"></div>
                    <span className="text-slate-600 dark:text-slate-400">盈利日</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="w-4 h-4 rounded bg-red-100 dark:bg-red-900/30 border border-red-300"></div>
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
                            const hasTrades = day.trades.length > 0
                            const isPositive = day.pnl >= 0
                            const isSelected = selectedDate?.toDateString() === day.date.toDateString()
                            const isNonTrading = day.isWeekend || day.isHoliday

                            return (
                                <button
                                    key={index}
                                    onClick={() => setSelectedDate(day.date)}
                                    title={day.holidayName || undefined}
                                    className={`
                                        aspect-square p-1 md:p-2 rounded-xl text-sm transition-all relative
                                        ${!day.isCurrentMonth ? 'text-slate-300 dark:text-slate-600' : ''}
                                        ${isToday(day.date) ? 'ring-2 ring-primary-500' : ''}
                                        ${isSelected ? 'bg-primary-500 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-700'}
                                        ${day.isWeekend && !isSelected ? 'bg-slate-100 dark:bg-slate-800' : ''}
                                        ${day.isHoliday && !isSelected ? 'bg-orange-50 dark:bg-orange-900/20' : ''}
                                        ${hasTrades && !isSelected && !isNonTrading ? (isPositive ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20') : ''}
                                    `}
                                >
                                    <span className="block">{day.date.getDate()}</span>

                                    {/* 节假日标记 */}
                                    {day.isHoliday && !isSelected && (
                                        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-orange-400"></span>
                                    )}

                                    {/* 盈亏显示 */}
                                    {hasTrades && (
                                        <span className={`text-[10px] md:text-xs block truncate ${isSelected ? 'text-white/80' : isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                                            {isPositive ? '+' : ''}{day.pnl.toFixed(0)}
                                        </span>
                                    )}

                                    {/* 节假日名称（手机隐藏） */}
                                    {day.isHoliday && day.holidayName && !hasTrades && (
                                        <span className={`hidden md:block text-[9px] truncate ${isSelected ? 'text-white/70' : 'text-orange-500'}`}>
                                            {day.holidayName}
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
                                        <p className="text-sm text-slate-500">交易数</p>
                                        <p className="text-xl font-bold">{selectedDayData.trades.length}</p>
                                    </div>
                                    <div>
                                        <p className="text-sm text-slate-500">当日盈亏</p>
                                        <p className={`text-xl font-bold ${selectedDayData.pnl >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                            {selectedDayData.pnl >= 0 ? '+' : ''}${selectedDayData.pnl.toFixed(2)}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Trade List */}
                            {selectedDayData.trades.length > 0 ? (
                                <div className="space-y-2">
                                    {selectedDayData.trades.map((trade) => (
                                        <Link key={trade.id} href={`/trades/${trade.id}`}>
                                            <div className="card p-4 hover:scale-[1.02] transition-transform cursor-pointer">
                                                <div className="flex items-center justify-between">
                                                    <div className="flex items-center space-x-3">
                                                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${(trade.pnl || 0) >= 0 ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                                                            {(trade.pnl || 0) >= 0 ? (
                                                                <TrendingUp className="w-4 h-4 text-emerald-500" />
                                                            ) : (
                                                                <TrendingDown className="w-4 h-4 text-red-500" />
                                                            )}
                                                        </div>
                                                        <div>
                                                            <p className="font-medium">{trade.symbol}</p>
                                                            <p className="text-xs text-slate-500">{trade.exchange}</p>
                                                        </div>
                                                    </div>
                                                    <p className={`font-bold ${(trade.pnl || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                                                        {(trade.pnl || 0) >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                                                    </p>
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
