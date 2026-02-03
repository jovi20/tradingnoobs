'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
    LayoutDashboard,
    TrendingUp,
    Calendar,
    Settings,
    FileText,
    Layers,
    LogOut,
    User,
    Briefcase
} from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'

const navItems = [
    { href: '/', label: '看板', icon: LayoutDashboard },
    { href: '/positions', label: '交易', icon: Briefcase },
    { href: '/strategies', label: '策略', icon: Layers },
    { href: '/daily', label: '日历', icon: Calendar },
    { href: '/reports', label: '周报', icon: FileText },
    { href: '/settings', label: '设置', icon: Settings },
]

export function Navbar() {
    const pathname = usePathname()
    const { user, isAuthenticated, logout } = useAuth()

    // 不在登录/注册页显示导航
    if (pathname === '/login' || pathname === '/register') {
        return null
    }

    return (
        <nav className="sticky top-0 z-50 backdrop-blur-xl bg-white/80 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-700">
            <div className="container mx-auto px-4">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <Link href="/" className="flex items-center space-x-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                            <TrendingUp className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-xl font-bold gradient-text">Trading Noobs</span>
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

            {/* Mobile Bottom Nav */}
            {isAuthenticated && (
                <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border-t border-slate-200 dark:border-slate-700">
                    <div className="flex justify-around py-2">
                        {navItems.slice(0, 5).map((item) => {
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
        </nav>
    )
}
