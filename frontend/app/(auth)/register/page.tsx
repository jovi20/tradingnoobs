'use client'

import { useState } from 'react'
import { useTheme } from '@/components/ThemeProvider'
import Link from 'next/link'
import Image from 'next/image'
import { AlertCircle, Clock3, ClipboardCheck, Sparkles } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

import { Button } from '@/components/ui/Button'
import { Input, Field } from '@/components/ui/Input'
import { Callout } from '@/components/ui/Callout'
import { getLocalizedAuthError } from '@/lib/authErrors'

export default function RegisterPage() {
    const { register } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [inviteCode, setInviteCode] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const { theme, resolvedTheme } = useTheme()
    const isDark = theme === 'dark' || resolvedTheme === 'dark'

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (password !== confirmPassword) {
            setError('两次输入的密码不一致')
            return
        }
        if (password.length < 8) {
            setError('密码至少需要 8 个字符')
            return
        }
        if (!inviteCode.trim()) {
            setError('请输入邀请码')
            return
        }

        setIsLoading(true)
        try {
            await register(email, password, inviteCode)
        } catch (err: unknown) {
            setError(getLocalizedAuthError(err, '注册失败，请稍后重试'))
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
                        建立你的决策档案，
                        <br />
                        让每一笔交易都能被读懂。
                    </h2>
                    <p className="mt-4 text-sm leading-6 text-ink-muted">
                        注册后即可记录交易、复盘偏差、追踪风险，并让 AI 从你的历史里发现模式。
                    </p>

                    <div className="mt-8 space-y-3">
                        {[
                            { icon: Clock3, text: '时间线优先，先看最近发生了什么' },
                            { icon: ClipboardCheck, text: '复盘完成度与纪律画像一目了然' },
                            { icon: Sparkles, text: '可审计的 AI 洞察与证据链' },
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

                <p className="text-xs text-ink-faint">量化系统前奏 · 决策复盘工作台</p>
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

                    <h1 className="text-2xl font-semibold tracking-tight text-ink">创建账户</h1>
                    <p className="mt-1.5 text-sm text-ink-muted">加入 Trading Noobs，开始记录你的第一笔决策。</p>

                    {error && (
                        <div role="alert" aria-live="assertive">
                            <Callout kind="error" className="mt-6" icon={<AlertCircle className="h-4 w-4" />}>
                                {error}
                            </Callout>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                        <Field label="邮箱" htmlFor="email">
                            <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="your@email.com" required autoComplete="email" />
                        </Field>
                        <Field label="密码" htmlFor="password">
                            <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="至少 8 个字符" required minLength={8} autoComplete="new-password" />
                        </Field>
                        <Field label="确认密码" htmlFor="confirm">
                            <Input id="confirm" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="再次输入密码" required autoComplete="new-password" />
                        </Field>
                        <Field label="邀请码" htmlFor="invite">
                            <Input id="invite" type="text" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} placeholder="请输入邀请码" required />
                        </Field>

                        <Button type="submit" loading={isLoading} className="w-full" size="lg">
                            {isLoading ? '注册中…' : '注册'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-sm text-ink-muted">
                        已有账户？{' '}
                        <Link href="/login" className="font-medium text-ai transition-opacity hover:opacity-80">
                            立即登录
                        </Link>
                    </p>
                </div>
            </main>
        </div>
    )
}
