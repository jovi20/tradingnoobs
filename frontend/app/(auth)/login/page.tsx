'use client'

import { useState } from 'react'
import { useTheme } from '@/components/ThemeProvider'
import Image from 'next/image'
import { AlertCircle, BookOpen, Clock3, ClipboardCheck } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

import { Button } from '@/components/ui/Button'
import { Input, Field } from '@/components/ui/Input'
import { Callout } from '@/components/ui/Callout'
import { getLocalizedAuthError } from '@/lib/authErrors'

export default function LoginPage() {
    const { login } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const { theme, resolvedTheme } = useTheme()
    const isDark = theme === 'dark' || resolvedTheme === 'dark'

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setIsLoading(true)
        try {
            await login(email, password)
        } catch (err: unknown) {
            setError(getLocalizedAuthError(err, '登录失败，请检查邮箱和密码'))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="grid min-h-screen lg:grid-cols-2">
            {/* Brand / preview panel */}
            <aside className="relative hidden flex-col justify-between overflow-hidden border-r border-line bg-panel-subtle p-10 lg:flex">
                <div className="flex items-center gap-2.5">
                    <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-md bg-ink p-1.5">
                        <Image src="/logo.png" alt="Trading Noobs" width={28} height={28} className="h-full w-full object-contain" priority />
                    </span>
                    <span className="text-sm font-semibold tracking-tight text-ink">Trading Noobs</span>
                </div>

                <div className="max-w-md">
                    <h2 className="tn-display text-3xl font-semibold leading-tight tracking-tight text-ink">
                        把交易从流水记录，
                        <br />
                        提升为可复盘的决策工作台。
                    </h2>
                    <p className="mt-4 text-sm leading-6 text-ink-muted">
                        时间线优先、复盘为中心。理解你最近做了什么，以及下一步该重复什么、避免什么。
                    </p>

                    <div className="mt-8 space-y-3">
                        {[
                            { icon: Clock3, text: '决策事件流：开仓到复盘一条线程' },
                            { icon: ClipboardCheck, text: '纪律与计划偏移和盈亏同级' },
                            { icon: BookOpen, text: '策略、检查清单和随笔形成完整记录' },
                        ].map(({ icon: Icon, text }) => (
                            <div key={text} className="flex items-center gap-3 text-sm text-ink-soft">
                                <span className="flex h-8 w-8 items-center justify-center rounded-md border border-line bg-panel text-ink-muted">
                                    <Icon className="h-4 w-4" />
                                </span>
                                {text}
                            </div>
                        ))}
                    </div>
                </div>

                <p className="text-xs text-ink-faint">邀请制交易日志 · 决策复盘工作台</p>
            </aside>

            {/* Form panel */}
            <main className="flex items-center justify-center px-4 py-12">
                <div className="w-full max-w-sm">
                    <div className="mb-8 flex flex-col items-center lg:hidden">
                        <Image
                            src={isDark ? '/logo-white.png' : '/logo-black.png'}
                            alt="Trading Noobs"
                            width={64}
                            height={64}
                            priority
                            className="h-16 w-16 object-contain"
                        />
                    </div>

                    <h1 className="text-2xl font-semibold tracking-tight text-ink">欢迎回来</h1>
                    <p className="mt-1.5 text-sm text-ink-muted">登录以继续你的决策复盘。</p>

                    {error && (
                        <div role="alert" aria-live="assertive">
                            <Callout kind="error" className="mt-6" icon={<AlertCircle className="h-4 w-4" />}>
                                {error}
                            </Callout>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                        <Field label="邮箱" htmlFor="email">
                            <Input
                                id="email"
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="your@email.com"
                                required
                                autoComplete="email"
                            />
                        </Field>

                        <Field label="密码" htmlFor="password">
                            <Input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                minLength={6}
                                autoComplete="current-password"
                            />
                        </Field>

                        <Button type="submit" loading={isLoading} className="w-full" size="lg">
                            {isLoading ? '登录中…' : '登录'}
                        </Button>
                    </form>

                </div>
            </main>
        </div>
    )
}
