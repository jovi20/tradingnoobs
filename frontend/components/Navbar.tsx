'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
    Activity,
    BarChart3,
    Calendar,
    Settings,
    FileText,
    Layers,
    LogOut,
    User,
    Briefcase,
    PlusCircle
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'

const navItems = [
    { href: '/', label: '时间线', icon: Activity },
    { href: '/dashboard', label: 'Dashboard', icon: BarChart3 },
    { href: '/positions', label: '交易', icon: Briefcase },
    { href: '/strategies', label: '规则与清单', icon: Layers },
    { href: '/daily', label: '日历', icon: Calendar },
    { href: '/insights', label: '复盘/洞察', icon: FileText },
    { href: '/settings', label: '设置', icon: Settings },
]

const mobileNavItems = [
    { href: '/', label: '首页', icon: Activity },
    { href: '/positions', label: '交易', icon: Briefcase },
    { href: '/insights', label: '复盘', icon: FileText },
    { href: '/settings', label: '我的', icon: User },
]

export function Navbar() {
    const pathname = usePathname()
    const { user, isAuthenticated, logout } = useAuth()
    const { theme, resolvedTheme } = useTheme()
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    // 不在登录/注册页显示导航
    if (pathname === '/login' || pathname === '/register') {
        return null
    }

    return (
        <>
            <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700">
                <div className="container mx-auto px-4">
                    <div className="flex items-center justify-between h-16">
                        {/* Logo */}
                        <Link href="/" className="flex items-center space-x-2 group">
                            <div className="relative w-9 h-9">
                                <img
                                    src={mounted && (theme === 'dark' || resolvedTheme === 'dark') ? '/logo-white.png' : '/logo-black.png'}
                                    alt="Logo"
                                    className="w-full h-full object-contain rotate-3 group-hover:rotate-6 transition-transform duration-300"
                                />
                            </div>
                            <div className="flex flex-col leading-none">
                                <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">Trading Noobs</span>
                            </div>
                        </Link>

                        {/* Desktop Nav */}
                        {isAuthenticated && (
                            <div className="hidden md:flex items-center space-x-1">
                                {navItems.map((item) => {
                                    const isActive = pathname === item.href
                                    const Icon = item.icon
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className={`
                                                flex items-center space-x-2 px-4 py-2 rounded-xl transition-all duration-200
                                                ${isActive
                                                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400'
                                                    : 'hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400'
                                                }
                                            `}
                                        >
                                            <Icon className="w-4 h-4" />
                                            <span className="text-sm font-medium">{item.label}</span>
                                        </Link>
                                    )
                                })}
                            </div>
                        )}

                        {/* Right Side */}
                        <div className="flex items-center space-x-3">
                            <ThemeToggle />
                            {isAuthenticated && (
                                <>
                                    <div className="hidden sm:flex items-center space-x-2 text-sm text-slate-500">
                                        <User className="w-4 h-4" />
                                        <span>{user?.email}</span>
                                    </div>
                                    <button
                                        onClick={logout}
                                        className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-slate-500 hover:text-red-500 transition-colors"
                                        title="退出登录"
                                    >
                                        <LogOut className="w-5 h-5" />
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </nav>

            {/* Mobile Bottom Nav */}
            {isAuthenticated && (
                <div className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border-t border-slate-200 dark:border-slate-700 pb-safe">
                    <div className="grid grid-cols-5 items-end px-2 py-2">
                        {mobileNavItems.slice(0, 2).map((item) => {
                            const isActive = pathname === item.href
                            const Icon = item.icon
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`
                                        flex flex-col items-center p-2 rounded-xl transition-all
                                        ${isActive
                                            ? 'text-primary-600 dark:text-primary-400'
                                            : 'text-slate-500 dark:text-slate-400'
                                        }
                                    `}
                                >
                                    <Icon className="w-5 h-5" />
                                    <span className="text-xs mt-1">{item.label}</span>
                                </Link>
                            )
                        })}
                        <Link
                            href="/positions/new"
                            className="mx-auto -mt-8 flex h-16 w-16 flex-col items-center justify-center rounded-2xl bg-slate-950 text-white shadow-xl shadow-slate-900/30 transition-transform active:scale-95 dark:bg-white dark:text-slate-950"
                        >
                            <PlusCircle className="h-6 w-6" />
                            <span className="mt-1 text-[10px] font-semibold">记录</span>
                        </Link>
                        {mobileNavItems.slice(2).map((item) => {
                            const isActive = pathname === item.href
                            const Icon = item.icon
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`
                                        flex flex-col items-center p-2 rounded-xl transition-all
                                        ${isActive
                                            ? 'text-primary-600 dark:text-primary-400'
                                            : 'text-slate-500 dark:text-slate-400'
                                        }
                                    `}
                                >
                                    <Icon className="w-5 h-5" />
                                    <span className="text-xs mt-1">{item.label}</span>
                                </Link>
                            )
                        })}
                    </div>
                </div>
            )}
        </>
    )
}
