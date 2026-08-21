'use client'

import { useState, useRef, useEffect } from 'react'
import { format, addMonths, subMonths, startOfMonth, endOfMonth, eachDayOfInterval, isSameDay, setHours, setMinutes } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Clock } from 'lucide-react'

interface DateTimePickerProps {
    value: string // ISO string
    onChange: (value: string) => void
    label?: string
    required?: boolean
}

export default function DateTimePicker({ value, onChange, label, required }: DateTimePickerProps) {
    const [isOpen, setIsOpen] = useState(false)
    const [currentMonth, setCurrentMonth] = useState(new Date())
    const [selectedDate, setSelectedDate] = useState<Date>(value ? new Date(value) : new Date())
    const [timeValue, setTimeValue] = useState(value ? format(new Date(value), 'HH:mm') : format(new Date(), 'HH:mm'))
    const containerRef = useRef<HTMLDivElement>(null)

    // Sync internal state when prop value changes
    useEffect(() => {
        if (value) {
            const date = new Date(value)
            setSelectedDate(date)
            setTimeValue(format(date, 'HH:mm'))
        }
    }, [value])

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                // Only close if it's the desktop dropdown (or click outside mobile modal content which is handled by backdrop click)
                // Actually for mobile modal we have a separate backdrop click handler
                // So this logic mainly serves desktop or clicks completely outside the react root
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [])

    const handleDateClick = (date: Date) => {
        const [hours, minutes] = timeValue.split(':').map(Number)
        const newDate = setMinutes(setHours(date, hours), minutes)
        setSelectedDate(newDate)
    }

    const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const newTime = e.target.value
        setTimeValue(newTime)
        const [hours, minutes] = newTime.split(':').map(Number)
        const newDate = setMinutes(setHours(selectedDate, hours), minutes)
        setSelectedDate(newDate)
    }

    const handleConfirm = () => {
        const isoString = format(selectedDate, "yyyy-MM-dd'T'HH:mm")
        onChange(isoString)
        setIsOpen(false)
    }

    const nextMonth = () => setCurrentMonth(addMonths(currentMonth, 1))
    const prevMonth = () => setCurrentMonth(subMonths(currentMonth, 1))

    const days = eachDayOfInterval({
        start: startOfMonth(currentMonth),
        end: endOfMonth(currentMonth)
    })

    const startDay = startOfMonth(currentMonth).getDay()
    const emptyDays = Array(startDay).fill(null)

    const renderCalendar = () => (
        <>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <button onClick={prevMonth} type="button" className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                    <ChevronLeft className="w-5 h-5 text-slate-500" />
                </button>
                <span className="font-semibold text-slate-700 dark:text-slate-200">
                    {format(currentMonth, 'yyyy年 MM月', { locale: zhCN })}
                </span>
                <button onClick={nextMonth} type="button" className="p-1 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg">
                    <ChevronRight className="w-5 h-5 text-slate-500" />
                </button>
            </div>

            {/* Weekdays */}
            <div className="grid grid-cols-7 mb-2 text-center text-xs text-slate-400 font-medium">
                {['日', '一', '二', '三', '四', '五', '六'].map(d => (
                    <div key={d}>{d}</div>
                ))}
            </div>

            {/* Days Grid */}
            <div className="grid grid-cols-7 gap-1 mb-4">
                {emptyDays.map((_, i) => <div key={`empty-${i}`} />)}
                {days.map(day => {
                    const isSelected = isSameDay(day, selectedDate)
                    const isToday = isSameDay(day, new Date())
                    return (
                        <button
                            key={day.toISOString()}
                            type="button"
                            onClick={() => handleDateClick(day)}
                            className={`
                                h-8 w-8 rounded-lg text-sm flex items-center justify-center transition-all
                                ${isSelected
                                    ? 'bg-primary-500 text-white font-semibold shadow-md shadow-primary-500/30'
                                    : 'hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300'}
                                ${isToday && !isSelected ? 'text-primary-500 font-semibold' : ''}
                            `}
                        >
                            {format(day, 'd')}
                        </button>
                    )
                })}
            </div>

            <div className="h-px bg-slate-100 dark:bg-slate-700 my-4" />

            {/* Time Picker */}
            <div className="flex items-center space-x-3 mb-4">
                <Clock className="w-4 h-4 text-slate-400" />
                <label className="text-sm text-slate-500">时间</label>
                <input
                    type="time"
                    value={timeValue}
                    onChange={handleTimeChange}
                    className="flex-1 input py-1 px-2 text-sm h-9"
                />
            </div>

            {/* Actions */}
            <div className="flex space-x-2">
                <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="flex-1 py-2 rounded-lg text-sm text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                >
                    取消
                </button>
                <button
                    type="button"
                    onClick={handleConfirm}
                    className="flex-1 py-2 rounded-lg text-sm bg-primary-500 text-white font-medium hover:bg-primary-600 shadow-lg shadow-primary-500/20 transition-all"
                >
                    确认
                </button>
            </div>
        </>
    )

    return (
        <div className={`relative ${isOpen ? 'z-50' : 'z-10'}`} ref={containerRef}>
            {label && (
                <label className="block text-sm font-medium mb-2">
                    <CalendarIcon className="w-4 h-4 inline mr-1" />
                    {label} {required && '*'}
                </label>
            )}

            {/* Input Trigger */}
            <div
                onClick={() => setIsOpen(!isOpen)}
                className="input cursor-pointer flex items-center justify-between group hover:border-primary-400 transition-colors"
            >
                <span className={value ? 'text-slate-900 dark:text-slate-100' : 'text-slate-400'}>
                    {value ? format(new Date(value), 'PPP p', { locale: zhCN }) : '选择日期时间'}
                </span>
                <CalendarIcon className="w-4 h-4 text-slate-400 group-hover:text-primary-500 transition-colors" />
            </div>

            {/* Popover */}
            {isOpen && (
                <>
                    {/* Mobile: Backdrop + Centered Modal */}
                    <div
                        className="md:hidden fixed inset-0 z-[100] bg-black/20 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200"
                        onClick={() => setIsOpen(false)}
                    >
                        <div
                            className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-sm p-4 animate-in zoom-in-95 duration-200 shadow-2xl"
                            onClick={e => e.stopPropagation()}
                        >
                            {renderCalendar()}
                        </div>
                    </div>

                    {/* Desktop: Absolute Dropdown */}
                    <div className="hidden md:block absolute z-50 left-0 top-full mt-2 w-72 p-4 rounded-xl bg-white dark:bg-slate-800 shadow-xl border border-slate-200 dark:border-slate-700 animate-in fade-in slide-in-from-top-2 duration-200">
                        {renderCalendar()}
                    </div>
                </>
            )}
        </div>
    )
}
