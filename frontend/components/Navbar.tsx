'use client'

import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import { LogOut, User } from 'lucide-react'
import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'
import { getVisibleNavigationItems } from '@/lib/navigation'
import { ProductTopNav } from '@/components/navigation/ProductTopNav'
import { MobileBottomNav } from '@/components/navigation/MobileBottomNav'

export function Navbar() {
    const pathname = usePathname()
    const { user, isAuthenticated, logout } = useAuth()
    const visibleNavItems = getVisibleNavigationItems(user?.role)

    // 不在登录/注册页显示导航
    if (pathname === '/login' || pathname === '/register') {
        return null
    }

    return (
        <>
            <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/88 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/88">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
                    <Link href="/timeline" className="flex items-center gap-3">
                        <div className="relative h-9 w-9 overflow-hidden rounded-2xl bg-slate-950 p-1.5 dark:bg-white">
                            <Image
                                src="/logo.png"
                                alt="Trading Noobs"
                                width={28}
                                height={28}
                                className="h-full w-full object-contain"
                                priority
                            />
                        </div>
                        <div className="leading-tight">
                            <span className="block text-base font-semibold tracking-tight text-slate-950 dark:text-white">
                                Trading Noobs
                            </span>
                            <span className="hidden text-[11px] uppercase tracking-[0.18em] text-slate-400 sm:block">
                                Decision Journal
                            </span>
                        </div>
                    </Link>

                    {isAuthenticated && <ProductTopNav items={visibleNavItems} pathname={pathname} />}

                    <div className="flex items-center gap-3">
                        <ThemeToggle />
                        {isAuthenticated && (
                            <>
                                <div className="hidden items-center gap-2 text-sm text-slate-500 lg:flex">
                                    <User className="h-4 w-4" />
                                    <span>{user?.email}</span>
                                </div>
                                <button
                                    onClick={logout}
                                    className="rounded-xl p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
                                    title="退出登录"
                                >
                                    <LogOut className="h-5 w-5" />
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </nav>

            {isAuthenticated && <MobileBottomNav items={visibleNavItems} pathname={pathname} />}
        </>
    )
}
