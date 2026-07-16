'use client'

import Image from 'next/image'
import Link from 'next/link'
import { LogOut, Search, User } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { ThemeToggle } from '@/components/ThemeToggle'
import {
    DropdownMenu, DropdownMenuTrigger, DropdownMenuContent,
    DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
} from '@/components/ui/DropdownMenu'

export function AppTopBar({ onOpenCommand }: { onOpenCommand: () => void }) {
    const { user, logout } = useAuth()

    return (
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur-md md:px-6">
            {/* Mobile brand (sidebar hidden on mobile) */}
            <Link href="/timeline" className="flex items-center gap-2 md:hidden">
                <span className="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-md bg-ink p-1.5">
                    <Image src="/logo.png" alt="Trading Noobs" width={24} height={24} className="h-full w-full object-contain" priority />
                </span>
                <span className="text-sm font-semibold tracking-tight text-ink">Trading Noobs</span>
            </Link>

            {/* Desktop spacer keeps controls right-aligned */}
            <div className="hidden md:block" />

            <div className="flex items-center gap-1.5">
                <button
                    onClick={onOpenCommand}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-panel-subtle hover:text-ink md:hidden"
                    title="搜索"
                    aria-label="搜索和快速跳转"
                >
                    <Search className="h-[18px] w-[18px]" />
                </button>

                <ThemeToggle />

                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <button
                            className="inline-flex h-9 items-center gap-2 rounded-md px-2 text-sm text-ink-muted transition-colors hover:bg-panel-subtle hover:text-ink"
                            aria-label={user?.email ? `打开账户菜单：${user.email}` : '打开账户菜单'}
                        >
                            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-panel-subtle text-ink-soft">
                                <User className="h-3.5 w-3.5" />
                            </span>
                            <span className="hidden max-w-[12rem] truncate lg:block">{user?.email}</span>
                        </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-56">
                        <DropdownMenuLabel>{user?.email ?? '账户'}</DropdownMenuLabel>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem asChild>
                            <Link href="/settings" className="cursor-pointer">设置</Link>
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem tone="danger" onSelect={() => logout()}>
                            <LogOut className="h-4 w-4" />
                            退出登录
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </header>
    )
}
