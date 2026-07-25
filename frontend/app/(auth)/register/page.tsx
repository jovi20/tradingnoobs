'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertCircle, KeyRound, UserPlus } from 'lucide-react'

import { Button } from '@/components/ui/Button'
import { Callout } from '@/components/ui/Callout'
import { Field, Input } from '@/components/ui/Input'
import { authAPI } from '@/lib/api'
import { getLocalizedAuthError } from '@/lib/authErrors'

const COMMON_TIMEZONES = [
    'Asia/Shanghai',
    'Asia/Hong_Kong',
    'Asia/Singapore',
    'Asia/Tokyo',
    'America/New_York',
    'America/Chicago',
    'Europe/London',
    'Europe/Paris',
    'UTC',
]

export default function RegisterPage() {
    const router = useRouter()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [inviteCode, setInviteCode] = useState('')
    const [timezone, setTimezone] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const handleSubmit = async (event: React.FormEvent) => {
        event.preventDefault()
        setError('')
        setIsLoading(true)
        try {
            await authAPI.register({
                email,
                password,
                invite_code: inviteCode,
                timezone,
            })
            router.push('/login?registered=1')
        } catch (requestError: unknown) {
            setError(getLocalizedAuthError(requestError, '注册失败，请检查输入后重试'))
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="grid min-h-screen lg:grid-cols-2">
            <aside className="relative hidden flex-col justify-between border-r border-line bg-panel-subtle p-10 lg:flex">
                <div className="flex items-center gap-2.5">
                    <span className="flex h-9 w-9 items-center justify-center rounded-md bg-ink p-1.5">
                        <Image src="/logo.png" alt="Trading Noobs" width={28} height={28} priority />
                    </span>
                    <span className="text-sm font-semibold text-ink">Trading Noobs</span>
                </div>
                <div className="max-w-md">
                    <KeyRound className="h-8 w-8 text-ink-muted" />
                    <h1 className="tn-display mt-5 text-3xl font-semibold leading-tight text-ink">
                        使用邀请码创建你的交易日志。
                    </h1>
                    <p className="mt-4 text-sm leading-6 text-ink-muted">
                        时区会用于确定交易发生时间、每日复盘边界和时间线顺序。
                    </p>
                </div>
                <p className="text-xs text-ink-faint">邀请码一次有效 · 到期后自动失效</p>
            </aside>

            <main className="flex items-center justify-center px-4 py-10">
                <div className="w-full max-w-sm">
                    <div className="mb-7 flex h-11 w-11 items-center justify-center rounded-md border border-line bg-panel lg:hidden">
                        <UserPlus className="h-5 w-5 text-ink" />
                    </div>
                    <h2 className="text-2xl font-semibold text-ink">创建账户</h2>
                    <p className="mt-1.5 text-sm text-ink-muted">输入管理员提供的一次性邀请码。</p>

                    {error && (
                        <div role="alert" aria-live="assertive">
                            <Callout kind="error" className="mt-6" icon={<AlertCircle className="h-4 w-4" />}>
                                {error}
                            </Callout>
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                        <Field label="邮箱" htmlFor="register-email">
                            <Input
                                id="register-email"
                                type="email"
                                value={email}
                                onChange={(event) => setEmail(event.target.value)}
                                autoComplete="email"
                                required
                            />
                        </Field>
                        <Field label="密码" htmlFor="register-password" hint="至少 8 个字符">
                            <Input
                                id="register-password"
                                type="password"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                autoComplete="new-password"
                                minLength={8}
                                required
                            />
                        </Field>
                        <Field label="邀请码" htmlFor="invite-code">
                            <Input
                                id="invite-code"
                                value={inviteCode}
                                onChange={(event) => setInviteCode(event.target.value)}
                                autoComplete="one-time-code"
                                required
                            />
                        </Field>
                        <Field label="时区" htmlFor="timezone">
                            <select
                                id="timezone"
                                value={timezone}
                                onChange={(event) => setTimezone(event.target.value)}
                                className="h-11 w-full rounded-md border border-line bg-panel px-3.5 text-sm text-ink outline-none focus:border-ink/40 focus:ring-2 focus:ring-ink/15"
                                required
                            >
                                <option value="" disabled>请选择时区</option>
                                {COMMON_TIMEZONES.map((item) => (
                                    <option key={item} value={item}>{item}</option>
                                ))}
                            </select>
                        </Field>
                        <Button type="submit" size="lg" loading={isLoading} className="w-full">
                            {isLoading ? '创建中…' : '创建账户'}
                        </Button>
                    </form>

                    <p className="mt-6 text-center text-sm text-ink-muted">
                        已有账户？{' '}
                        <Link href="/login" className="font-medium text-ink hover:underline">
                            返回登录
                        </Link>
                    </p>
                </div>
            </main>
        </div>
    )
}
