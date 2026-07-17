'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
    Search, Clock3, LayoutDashboard, Briefcase, Layers, Calendar,
    FileText, Settings, Plus, Sparkles, ShieldCheck, Gauge, CornerDownLeft,
} from 'lucide-react'

import { cn } from '@/lib/cn'
import { useAuth } from '@/contexts/AuthContext'
import { useEffectiveCapabilities } from '@/contexts/EffectiveCapabilitiesContext'
import {
    isEffectiveCapabilityEnabled,
    type EffectiveCapabilityId,
} from '@/lib/effective-capabilities'

interface Command {
    id: string
    label: string
    hint?: string
    icon: React.ComponentType<{ className?: string }>
    href: string
    keywords?: string
    group: '导航' | '快捷动作' | '管理'
    adminOnly?: boolean
    requiredCapability?: EffectiveCapabilityId
}

const COMMANDS: Command[] = [
    { id: 'nav-timeline', label: '时间线', icon: Clock3, href: '/timeline', keywords: 'timeline home shijianxian', group: '导航' },
    { id: 'nav-dashboard', label: '看板', icon: LayoutDashboard, href: '/dashboard', keywords: 'dashboard kanban', group: '导航' },
    { id: 'nav-positions', label: '交易', icon: Briefcase, href: '/positions', keywords: 'positions trades jiaoyi', group: '导航' },
    { id: 'nav-strategies', label: '策略', icon: Layers, href: '/strategies', keywords: 'strategies celue', group: '导航' },
    { id: 'nav-daily', label: '日历', icon: Calendar, href: '/daily', keywords: 'daily calendar rili', group: '导航' },
    { id: 'nav-insights', label: '洞察', icon: FileText, href: '/insights', keywords: 'insights ai dongcha', group: '导航', requiredCapability: 'AI_INSIGHTS' },
    { id: 'nav-settings', label: '设置', icon: Settings, href: '/settings', keywords: 'settings shezhi', group: '导航' },
    { id: 'act-new', label: '新建交易', hint: '录入一笔新仓位', icon: Plus, href: '/positions/new', keywords: 'new trade create xinjian', group: '快捷动作' },
    { id: 'act-ai', label: '运行 AI 分析', hint: '洞察助手', icon: Sparkles, href: '/insights', keywords: 'ai analyze fenxi', group: '快捷动作', requiredCapability: 'AI_INSIGHTS' },
    { id: 'admin-ops', label: '运维控制台', icon: Gauge, href: '/admin/ops', keywords: 'admin ops yunwei', group: '管理', adminOnly: true },
    { id: 'admin-jobs', label: '任务队列', icon: ShieldCheck, href: '/admin/jobs', keywords: 'admin jobs renwu', group: '管理', adminOnly: true },
]

export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
    // Mount the content fresh on each open so its state resets without an effect.
    if (!open) return null
    return <CommandPaletteContent onOpenChange={onOpenChange} />
}

function CommandPaletteContent({ onOpenChange }: { onOpenChange: (v: boolean) => void }) {
    const router = useRouter()
    const { user } = useAuth()
    const effectiveCapabilities = useEffectiveCapabilities()
    const [query, setQuery] = useState('')
    const [active, setActive] = useState(0)
    const inputRef = useRef<HTMLInputElement>(null)
    const listRef = useRef<HTMLDivElement>(null)

    const results = useMemo(() => {
        const isAdmin = user?.role === 'admin'
        const q = query.trim().toLowerCase()
        return COMMANDS.filter((c) => (!c.adminOnly || isAdmin))
            .filter((c) => (
                !c.requiredCapability
                || isEffectiveCapabilityEnabled(effectiveCapabilities, c.requiredCapability)
            ))
            .filter((c) => !q || c.label.toLowerCase().includes(q) || c.keywords?.includes(q) || c.hint?.toLowerCase().includes(q))
    }, [effectiveCapabilities, query, user?.role])

    useEffect(() => {
        // Focus the input on mount — a DOM side effect, not React state.
        const raf = requestAnimationFrame(() => inputRef.current?.focus())
        return () => cancelAnimationFrame(raf)
    }, [])

    const run = (cmd: Command) => {
        onOpenChange(false)
        router.push(cmd.href)
    }

    const onKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'ArrowDown') {
            e.preventDefault()
            setActive((i) => Math.min(i + 1, results.length - 1))
        } else if (e.key === 'ArrowUp') {
            e.preventDefault()
            setActive((i) => Math.max(i - 1, 0))
        } else if (e.key === 'Enter') {
            e.preventDefault()
            const cmd = results[active]
            if (cmd) run(cmd)
        }
    }

    useEffect(() => {
        listRef.current?.querySelector<HTMLElement>('[data-active="true"]')?.scrollIntoView({ block: 'nearest' })
    }, [active])

    // Preserve source order but present grouped
    let renderIndex = -1

    return (
        <div className="fixed inset-0 z-[100] flex items-start justify-center px-4 pt-[12vh]" role="dialog" aria-modal="true">
            <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px] animate-fade-in" onClick={() => onOpenChange(false)} />
            <div className="relative w-full max-w-xl overflow-hidden rounded-lg border border-line bg-panel shadow-pop animate-scale-in">
                <div className="flex items-center gap-3 border-b border-line px-4">
                    <Search className="h-4 w-4 shrink-0 text-ink-faint" />
                    <input
                        ref={inputRef}
                        value={query}
                        onChange={(e) => { setQuery(e.target.value); setActive(0) }}
                        onKeyDown={onKeyDown}
                        placeholder="搜索页面或动作…"
                        className="h-12 w-full bg-transparent text-sm text-ink placeholder:text-ink-faint focus:outline-none"
                    />
                    <kbd className="hidden shrink-0 rounded border border-line bg-panel-subtle px-1.5 py-0.5 text-[10px] font-medium text-ink-faint sm:block">ESC</kbd>
                </div>

                <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
                    {results.length === 0 ? (
                        <p className="px-3 py-8 text-center text-sm text-ink-muted">没有匹配的结果</p>
                    ) : (
                        (['导航', '快捷动作', '管理'] as const).map((group) => {
                            const groupItems = results.filter((c) => c.group === group)
                            if (groupItems.length === 0) return null
                            return (
                                <div key={group} className="mb-1">
                                    <p className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">{group}</p>
                                    {groupItems.map((cmd) => {
                                        renderIndex += 1
                                        const idx = renderIndex
                                        const Icon = cmd.icon
                                        const isActive = idx === active
                                        return (
                                            <button
                                                key={cmd.id}
                                                data-active={isActive}
                                                onMouseEnter={() => setActive(idx)}
                                                onClick={() => run(cmd)}
                                                className={cn(
                                                    'flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm transition-colors',
                                                    isActive ? 'bg-panel-subtle text-ink' : 'text-ink-soft',
                                                )}
                                            >
                                                <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-ink' : 'text-ink-faint')} />
                                                <span className="flex-1 truncate">{cmd.label}</span>
                                                {cmd.hint && <span className="truncate text-xs text-ink-faint">{cmd.hint}</span>}
                                                {isActive && <CornerDownLeft className="h-3.5 w-3.5 shrink-0 text-ink-faint" />}
                                            </button>
                                        )
                                    })}
                                </div>
                            )
                        })
                    )}
                </div>
            </div>
        </div>
    )
}
