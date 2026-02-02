'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    ChevronLeft,
    ChevronRight,
    Calendar,
    TrendingUp,
    TrendingDown,
    Loader2
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { tradesAPI, Trade } from '@/lib/api'

const weekDays = ['日', '一', '二', '三', '四', '五', '六']

interface DayData {
    date: Date
    trades: Trade[]
    pnl: number
    isCurrentMonth: boolean
}

export default function DailyPage() {
    const { token } = useAuth()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [trades, setTrades] = useState<Trade[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [selectedDate, setSelectedDate] = useState<Date | null>(null)

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    useEffect(() => {
        const fetchTrades = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const data = await tradesAPI.list(token)
                setTrades(data)
            } catch (err) {
                console.error(err)
            } finally {
                setIsLoading(false)
            }
        }
        fetchTrades()
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
                trades: getTradesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
            })
        }

        // 当月
        for (let i = 1; i <= totalDays; i++) {
            const date = new Date(year, month, i)
            days.push({
                date,
                trades: getTradesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: true,
            })
        }

        // 下月填充
        const remaining = 42 - days.length
        for (let i = 1; i <= remaining; i++) {
            const date = new Date(year, month + 1, i)
            days.push({
                date,
                trades: getTradesForDate(date),
                pnl: getPnlForDate(date),
                isCurrentMonth: false,
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
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">交易日历</h1>
                <div className="flex items-center space-x-4">
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

            <div className="grid lg:grid-cols-3 gap-6">
                {/* Calendar */}
                <div className="lg:col-span-2 card p-4">
                    {/* Week headers */}
                    <div className="grid grid-cols-7 mb-2">
                        {weekDays.map((day) => (
                            <div key={day} className="text-center text-sm font-medium text-slate-500 py-2">
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

                            return (
                                <button
                                    key={index}
                                    onClick={() => setSelectedDate(day.date)}
                                    className={`
                                        aspect-square p-2 rounded-xl text-sm transition-all relative
                                        ${!day.isCurrentMonth ? 'text-slate-300 dark:text-slate-600' : ''}
                                        ${isToday(day.date) ? 'ring-2 ring-primary-500' : ''}
                                        ${isSelected ? 'bg-primary-500 text-white' : 'hover:bg-slate-100 dark:hover:bg-slate-700'}
                                        ${hasTrades && !isSelected ? (isPositive ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20') : ''}
                                    `}
                                >
                                    <span className="block">{day.date.getDate()}</span>
                                    {hasTrades && (
                                        <span className={`text-xs block ${isSelected ? 'text-white/80' : isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
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
