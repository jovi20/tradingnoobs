import type { Metadata } from 'next'
import './globals.css'
import { plexSans, plexMono } from './fonts'
import { Providers } from '@/components/Providers'

export const metadata: Metadata = {
    title: 'Trading Noobs | 交易日志与洞察',
    description: '专业级交易日志记录、分析与 AI 深度复盘系统',
    icons: {
        icon: '/logo.png',
        shortcut: '/logo.png',
        apple: '/logo.png',
    },
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="zh" suppressHydrationWarning className={`${plexSans.variable} ${plexMono.variable}`}>
            <body>
                <Providers>{children}</Providers>
            </body>
        </html>
    )
}
