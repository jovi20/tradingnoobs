'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ArrowLeft, Gauge, ShieldCheck } from 'lucide-react'

import { cn } from '@/lib/cn'
import { useAuth } from '@/contexts/AuthContext'
import { isNavigationItemActive } from '@/lib/navigation'
import { ThemeToggle } from '@/components/ThemeToggle'

const ADMIN_ITEMS = [
    { href: '/admin/ops', label: '运维控制台', icon: Gauge },
    { href: '/admin/jobs', label: '任务队列', icon: ShieldCheck },
]

/**
 * Admin shell — a deliberately distinct surface from the product. Desktop-first,
 * denser, with its own top rail and an explicit boundary back to the product.
 */
export function AdminShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()
    const { isAuthenticated } = useAuth()

    if (!isAuthenticated) {
        return <>{children}</>
    }

    return (
        <div className="min-h-screen bg-panel-subtle">
            <header className="sticky top-0 z-30 border-b border-line-strong bg-panel/90 backdrop-blur-md">
                <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4 md:px-6">
                    <Link
                        href="/timeline"
                        aria-label="返回产品"
                        title="返回产品"
                        className="inline-flex items-center gap-2 text-sm text-ink-muted transition-colors hover:text-ink"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span className="hidden sm:inline">返回产品</span>
                    </Link>
                    <span className="h-5 w-px bg-line-strong" />
                    <div className="flex items-center gap-2">
                        <span className="flex h-6 w-6 items-center justify-center rounded bg-ink text-canvas">
                            <ShieldCheck className="h-3.5 w-3.5" />
                        </span>
                        <span className="text-sm font-semibold tracking-tight text-ink">管理后台</span>
                    </div>

                    <nav className="ml-4 flex items-center gap-1">
                        {ADMIN_ITEMS.map((item) => {
                            const Icon = item.icon
                            const active = isNavigationItemActive(item.href, pathname)
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    aria-label={item.label}
                                    title={item.label}
                                    className={cn(
                                        'inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                                        active ? 'bg-ink text-canvas' : 'text-ink-muted hover:bg-panel-subtle hover:text-ink',
                                    )}
                                >
                                    <Icon className="h-4 w-4" />
                                    <span className="hidden sm:inline">{item.label}</span>
                                </Link>
                            )
                        })}
                    </nav>

                    <div className="ml-auto">
                        <ThemeToggle />
                    </div>
                </div>
            </header>
            <main className="mx-auto w-full max-w-7xl px-4 py-6 md:px-6">
                {children}
            </main>
        </div>
    )
}
