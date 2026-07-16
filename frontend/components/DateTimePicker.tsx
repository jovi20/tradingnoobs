'use client'

import { useEffect, useId, useRef, useState } from 'react'
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
    const [currentMonth, setCurrentMonth] = useState<Date>(value ? new Date(value) : new Date())
    const [selectedDate, setSelectedDate] = useState<Date>(value ? new Date(value) : new Date())
    const [timeValue, setTimeValue] = useState(value ? format(new Date(value), 'HH:mm') : format(new Date(), 'HH:mm'))
    const containerRef = useRef<HTMLDivElement>(null)
    const triggerId = useId()
    const timeInputId = useId()
    const displayedValue = value
        ? format(new Date(value), 'PPP p', { locale: zhCN })
        : '未选择'
    const triggerLabel = `${label || '日期和时间'}：${displayedValue}`

    // Sync internal state when prop value changes
    useEffect(() => {
        if (!value) return

        const syncTimer = window.setTimeout(() => {
            const date = new Date(value)
            setSelectedDate(date)
            setCurrentMonth(date)
            setTimeValue(format(date, 'HH:mm'))
        }, 0)

        return () => window.clearTimeout(syncTimer)
    }, [value])

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false)
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

    const renderCalendar = (surface: 'mobile' | 'desktop') => (
        <>
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <button
                    onClick={prevMonth}
                    type="button"
                    className="p-1 hover:bg-panel-subtle rounded-lg"
                    aria-label="上一个月"
                    title="上一个月"
                >
                    <ChevronLeft className="w-5 h-5 text-ink-muted" />
                </button>
                <span className="font-semibold text-ink-soft">
                    {format(currentMonth, 'yyyy年 MM月', { locale: zhCN })}
                </span>
                <button
                    onClick={nextMonth}
                    type="button"
                    className="p-1 hover:bg-panel-subtle rounded-lg"
                    aria-label="下一个月"
                    title="下一个月"
                >
                    <ChevronRight className="w-5 h-5 text-ink-muted" />
                </button>
            </div>

            {/* Weekdays */}
            <div className="grid grid-cols-7 mb-2 text-center text-xs text-ink-faint font-medium">
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
                            aria-label={format(day, 'yyyy年M月d日 EEEE', { locale: zhCN })}
                            aria-pressed={isSelected}
                            aria-current={isToday ? 'date' : undefined}
                            className={`
                                h-8 w-8 rounded-md text-sm flex items-center justify-center transition-colors tn-nums
                                ${isSelected
                                    ? 'bg-ink text-canvas font-semibold'
                                    : 'hover:bg-panel-subtle text-ink-soft'}
                                ${isToday && !isSelected ? 'text-ink font-semibold' : ''}
                            `}
                        >
                            {format(day, 'd')}
                        </button>
                    )
                })}
            </div>

            <div className="h-px bg-line my-4" />

            {/* Time Picker */}
            <div className="flex items-center space-x-3 mb-4">
                <Clock className="w-4 h-4 text-ink-faint" />
                <label htmlFor={`${timeInputId}-${surface}`} className="text-sm text-ink-muted">时间</label>
                <input
                    id={`${timeInputId}-${surface}`}
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
                    className="flex-1 py-2 rounded-lg text-sm text-ink-muted hover:bg-panel-subtle transition-colors"
                >
                    取消
                </button>
                <button
                    type="button"
                    onClick={handleConfirm}
                    className="flex-1 py-2 rounded-md text-sm bg-ink text-canvas font-medium hover:bg-ink-soft transition-colors"
                >
                    确认
                </button>
            </div>
        </>
    )

    return (
        <div className={`relative ${isOpen ? 'z-50' : 'z-10'}`} ref={containerRef}>
            {label && (
                <label htmlFor={triggerId} className="block text-sm font-medium mb-2">
                    <CalendarIcon className="w-4 h-4 inline mr-1" />
                    {label} {required && '*'}
                </label>
            )}

            {/* Input Trigger */}
            <button
                id={triggerId}
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="input group flex w-full cursor-pointer items-center justify-between text-left transition-colors hover:border-line-strong"
                aria-label={triggerLabel}
                aria-haspopup="dialog"
                aria-expanded={isOpen}
            >
                <span className={value ? 'text-ink' : 'text-ink-faint'}>
                    {value ? format(new Date(value), 'PPP p', { locale: zhCN }) : '选择日期时间'}
                </span>
                <CalendarIcon className="w-4 h-4 text-ink-faint group-hover:text-ink-muted transition-colors" />
            </button>

            {/* Popover */}
            {isOpen && (
                <>
                    {/* Mobile: Backdrop + Centered Modal */}
                    <div
                        className="md:hidden fixed inset-0 z-[100] bg-black/20 flex items-center justify-center p-4 animate-in fade-in duration-200"
                        onClick={() => setIsOpen(false)}
                    >
                        <div
                            className="bg-panel rounded-lg border border-line w-full max-w-sm p-4 animate-in zoom-in-95 duration-200"
                            onClick={e => e.stopPropagation()}
                            role="dialog"
                            aria-modal="true"
                            aria-label="选择日期和时间"
                        >
                            {renderCalendar('mobile')}
                        </div>
                    </div>

                    {/* Desktop: Absolute Dropdown */}
                    <div
                        className="hidden md:block absolute z-50 left-0 top-full mt-2 w-72 p-4 rounded-md bg-panel border border-line animate-in fade-in slide-in-from-top-2 duration-200"
                        role="dialog"
                        aria-label="选择日期和时间"
                    >
                        {renderCalendar('desktop')}
                    </div>
                </>
            )}
        </div>
    )
}
