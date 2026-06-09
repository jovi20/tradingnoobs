export type UserRole = string | null | undefined
export type NavigationSection = 'product' | 'ops' | 'settings'

export interface NavigationItem {
    href: string
    label: string
    icon: 'timeline' | 'dashboard' | 'positions' | 'strategies' | 'daily' | 'insights' | 'settings' | 'adminJobs'
    section: NavigationSection
}

const productItems: NavigationItem[] = [
    { href: '/timeline', label: '时间线', icon: 'timeline', section: 'product' },
    { href: '/dashboard', label: '看板', icon: 'dashboard', section: 'product' },
    { href: '/positions', label: '交易', icon: 'positions', section: 'product' },
    { href: '/strategies', label: '策略', icon: 'strategies', section: 'product' },
    { href: '/daily', label: '日历', icon: 'daily', section: 'product' },
    { href: '/insights', label: '洞察', icon: 'insights', section: 'product' },
]

const adminItems: NavigationItem[] = [
    { href: '/admin/jobs', label: 'Ops', icon: 'adminJobs', section: 'ops' },
]

const settingsItem: NavigationItem = { href: '/settings', label: '设置', icon: 'settings', section: 'settings' }

export function getVisibleNavigationItems(role: UserRole): NavigationItem[] {
    if (role === 'admin') {
        return [...productItems, ...adminItems, settingsItem]
    }
    return [...productItems, settingsItem]
}

export function isNavigationItemActive(href: string, pathname: string): boolean {
    if (href === '/timeline') return pathname === href
    return pathname === href || pathname.startsWith(`${href}/`)
}
