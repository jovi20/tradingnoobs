'use client'

import { useState, useEffect } from 'react'
import { Globe, Clock, Moon, Sun } from 'lucide-react'

// Market definitions
type MarketStatusType = 'OPEN' | 'CLOSED' | 'PRE' | 'POST' | 'OVERNIGHT' | 'WEEKEND' | 'HOLIDAY'

interface MarketInfo {
    id: string
    name: string
    timezone: string // IANA timezone
    sessions: {
        pre?: { start: string; end: string } // HH:mm
        regular: { start: string; end: string }
        post?: { start: string; end: string }
        overnight?: { start: string; end: string } // Note: Overnight usually spans midnight, specialized logic needed
    }
}

const MARKETS: MarketInfo[] = [
    {
        id: 'US',
        name: '美股',
        timezone: 'America/New_York',
        sessions: {
            pre: { start: '04:00', end: '09:30' },
            regular: { start: '09:30', end: '16:00' },
            post: { start: '16:00', end: '20:00' },
            overnight: { start: '20:00', end: '04:00' } // 20:00 - 04:00 next day
        }
    },
    {
        id: 'CN',
        name: 'A股',
        timezone: 'Asia/Shanghai',
        sessions: {
            regular: { start: '09:30', end: '15:00' }
            // Simplified, ignores lunch break 11:30-13:00 for status check simplicity or we can add it later
            // For now let's keep simple: "Open" if within 9:30-15:00 weekdays
            // A-Share doesn't really have pre/post market in same sense for retail
        }
    },
    {
        id: 'CRYPTO',
        name: '加密',
        timezone: 'UTC',
        sessions: {
            regular: { start: '00:00', end: '23:59' } // Always open
        }
    }
]

export default function MarketStatus() {
    const [currentTime, setCurrentTime] = useState(new Date())

    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000)
        return () => clearInterval(timer)
    }, [])

    const getMarketStatus = (market: MarketInfo, now: Date): { status: MarketStatusType; label: string; color: string } => {
        if (market.id === 'CRYPTO') return { status: 'OPEN', label: '交易中', color: 'text-emerald-500' }

        // Convert current time to market timezone
        const options: Intl.DateTimeFormatOptions = {
            timeZone: market.timezone,
            hour: 'numeric',
            minute: 'numeric',
            second: 'numeric',
            hour12: false,
            weekday: 'short'
        }

        // Get market local parts
        const formatter = new Intl.DateTimeFormat('en-US', options)
        const parts = formatter.formatToParts(now)
        const partMap = new Map(parts.map(p => [p.type, p.value]))

        const hour = parseInt(partMap.get('hour') || '0')
        const minute = parseInt(partMap.get('minute') || '0')
        const weekday = partMap.get('weekday') // 'Sat', 'Sun' etc.

        const currentMins = hour * 60 + minute

        // Weekend check
        if (weekday === 'Sat' || weekday === 'Sun') {
            // Crypto handled above. US/CN closed.
            // Note: US Overnight starts Sunday 20:00 ET? 
            // Usually Overnight: Mon-Fri? Or Sun night to Fri?
            // Blue Ocean ATS is Sun-Thu 8PM - 4AM. 
            // Let's assume standard Sun 8pm open for Overnight.
            if (market.id === 'US' && weekday === 'Sun') {
                // Check if >= 20:00
                const overnightStart = 20 * 60
                if (currentMins >= overnightStart) {
                    return { status: 'OVERNIGHT', label: '夜盘', color: 'text-indigo-500' }
                }
            }
            if (market.id === 'US' && weekday === 'Sat') {
                // Sat is closed
                return { status: 'CLOSED', label: '休市', color: 'text-slate-400' }
            }
            if (market.id === 'CN') {
                return { status: 'CLOSED', label: '休市', color: 'text-slate-400' }
            }
            // For simplicity, standard weekend closed unless caught above
        }

        const toMins = (timeResult: string) => {
            const [h, m] = timeResult.split(':').map(Number)
            return h * 60 + m
        }

        const { pre, regular, post, overnight } = market.sessions

        // Regular
        const regStart = toMins(regular.start)
        const regEnd = toMins(regular.end)

        // CN A-Share Lunch Break special handling
        if (market.id === 'CN') {
            const lunchStart = 11 * 60 + 30
            const lunchEnd = 13 * 60
            if (currentMins >= regStart && currentMins < lunchStart) return { status: 'OPEN', label: '交易中', color: 'text-emerald-500' }
            if (currentMins >= lunchStart && currentMins < lunchEnd) return { status: 'CLOSED', label: '休市(午间)', color: 'text-slate-400' }
            if (currentMins >= lunchEnd && currentMins <= regEnd) return { status: 'OPEN', label: '交易中', color: 'text-emerald-500' }
            return { status: 'CLOSED', label: '休市', color: 'text-slate-400' }
        }

        // US
        if (currentMins >= regStart && currentMins < regEnd) {
            return { status: 'OPEN', label: '盘中', color: 'text-emerald-500' }
        }

        if (pre && currentMins >= toMins(pre.start) && currentMins < toMins(pre.end)) {
            return { status: 'PRE', label: '盘前', color: 'text-amber-500' }
        }

        if (post && currentMins >= toMins(post.start) && currentMins < toMins(post.end)) {
            return { status: 'POST', label: '盘后', color: 'text-amber-500' }
        }

        if (overnight) {
            const start = toMins(overnight.start)
            const end = toMins(overnight.end)
            // Overnight spans midnight. 20:00 - 04:00
            // If current time > 20:00 (Evening) OR current time < 04:00 (Early morning)
            // Since we parsed current local time hours, checking logic:

            if (currentMins >= start) {
                // e.g. 21:00
                return { status: 'OVERNIGHT', label: '夜盘', color: 'text-indigo-500' }
            }
            if (currentMins < end) {
                // e.g. 03:00. This is technicall "next day" but belong to session
                // We need to confirm if it's a weekday for early morning.
                // If it is Tuesday 03:00, it is Overnight session from Monday.
                // Mon 03:00 is from Sunday night? Yes.
                return { status: 'OVERNIGHT', label: '夜盘', color: 'text-indigo-500' }
            }
        }

        return { status: 'CLOSED', label: '休市', color: 'text-slate-400' }
    }

    return (
        <div className="flex items-center gap-4 bg-white dark:bg-slate-800 p-2 rounded-xl border border-slate-100 dark:border-slate-700 shadow-sm overflow-x-auto max-w-full">
            {MARKETS.map(market => {
                const { status, label, color } = getMarketStatus(market, currentTime)

                // Get Local Display Time for that market (to show "What time is it there")
                const localTimeStr = new Intl.DateTimeFormat('en-US', {
                    timeZone: market.timezone,
                    hour: 'numeric',
                    minute: 'numeric',
                    hour12: false
                }).format(currentTime)

                return (
                    <div key={market.id} className="flex items-center gap-2 px-2 border-r last:border-0 border-slate-100 dark:border-slate-700 shrink-0">
                        <div className="text-xs">
                            <div className="flex items-center gap-1 font-medium text-slate-700 dark:text-slate-300">
                                {market.id === 'US' ? <Globe className="w-3 h-3" /> : null}
                                {market.name}
                            </div>
                            <div className="text-slate-400 scale-90 origin-left font-mono">
                                {localTimeStr}
                            </div>
                        </div>
                        <div className={`text-xs font-bold ${color} px-1.5 py-0.5 rounded bg-slate-50 dark:bg-slate-700/50`}>
                            {label}
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
