'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { authAPI, User } from '@/lib/api'

interface AuthContextType {
    user: User | null
    token: string | null
    isLoading: boolean
    isAuthenticated: boolean
    login: (email: string, password: string) => Promise<void>
    register: (email: string, password: string) => Promise<void>
    logout: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const TOKEN_KEY = 'tradingnoobs_token'
const PUBLIC_PATHS = ['/login', '/register']

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null)
    const [token, setToken] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const router = useRouter()
    const pathname = usePathname()

    // 初始化：检查本地存储的 token
    useEffect(() => {
        const initAuth = async () => {
            const storedToken = localStorage.getItem(TOKEN_KEY)
            if (storedToken) {
                try {
                    const userData = await authAPI.me(storedToken)
                    setUser(userData)
                    setToken(storedToken)
                } catch (error) {
                    // Token 无效，清除
                    localStorage.removeItem(TOKEN_KEY)
                }
            }
            setIsLoading(false)
        }
        initAuth()
    }, [])

    // 路由保护
    useEffect(() => {
        if (!isLoading) {
            const isPublicPath = PUBLIC_PATHS.includes(pathname)
            if (!token && !isPublicPath) {
                router.push('/login')
            } else if (token && isPublicPath) {
                router.push('/')
            }
        }
    }, [token, isLoading, pathname, router])

    const login = async (email: string, password: string) => {
        const response = await authAPI.login(email, password)
        const newToken = response.access_token
        localStorage.setItem(TOKEN_KEY, newToken)
        setToken(newToken)

        const userData = await authAPI.me(newToken)
        setUser(userData)
        router.push('/')
    }

    const register = async (email: string, password: string) => {
        await authAPI.register(email, password)
        // 注册成功后自动登录
        await login(email, password)
    }

    const logout = () => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
        router.push('/login')
    }

    // 加载中显示空白，避免闪烁
    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
            </div>
        )
    }

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!token,
                login,
                register,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    )
}

export function useAuth() {
    const context = useContext(AuthContext)
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider')
    }
    return context
}
