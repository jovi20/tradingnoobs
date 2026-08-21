'use client'

import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import Link from 'next/link'
import { Mail, Lock, AlertCircle, Gift } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

export default function RegisterPage() {
    const { register } = useAuth()
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [inviteCode, setInviteCode] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const { theme, resolvedTheme } = useTheme()
    const [mounted, setMounted] = useState(false)

    useEffect(() => {
        setMounted(true)
    }, [])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')

        if (password !== confirmPassword) {
            setError('两次输入的密码不一致')
            return
        }

        if (password.length < 6) {
            setError('密码至少需要6个字符')
            return
        }

        if (!inviteCode.trim()) {
            setError('请输入邀请码')
            return
        }

        setIsLoading(true)

        try {
            await register(email, password, inviteCode)
        } catch (err: any) {
            setError(err.message || '注册失败，该邮箱可能已被使用')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-[80vh] flex items-center justify-center">
            <div className="w-full max-w-md">
                <div className="card p-8">
                    {/* Logo */}
                    <div className="flex flex-col items-center mb-8 group">
                        <div className="relative w-20 h-20 mb-4">
                            <img
                                src={mounted && (theme === 'dark' || resolvedTheme === 'dark') ? '/logo-white.png' : '/logo-black.png'}
                                alt="Trading Noobs Logo"
                                className="w-full h-full object-contain rotate-6 group-hover:rotate-12 transition-transform duration-500"
                            />
                        </div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Trading Noobs</h1>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-center space-x-2 text-red-600 dark:text-red-400">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <span className="text-sm">{error}</span>
                        </div>
                    )}

                    {/* Form */}
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">邮箱</label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="input !pl-14"
                                    placeholder="your@email.com"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">密码</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input !pl-14"
                                    placeholder="至少6个字符"
                                    required
                                    minLength={6}
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">确认密码</label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                                <input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="input !pl-14"
                                    placeholder="再次输入密码"
                                    required
                                />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2">邀请码</label>
                            <div className="relative">
                                <Gift className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                                <input
                                    type="text"
                                    value={inviteCode}
                                    onChange={(e) => setInviteCode(e.target.value)}
                                    className="input !pl-14"
                                    placeholder="请输入邀请码"
                                    required
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full btn btn-primary py-3 text-lg"
                        >
                            {isLoading ? '注册中...' : '注册'}
                        </button>
                    </form>

                    {/* Login Link */}
                    <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
                        已有账户？{' '}
                        <Link href="/login" className="text-primary-600 hover:text-primary-700 font-medium">
                            立即登录
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    )
}
