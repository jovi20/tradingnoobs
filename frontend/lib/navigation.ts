import {
    DISABLED_EFFECTIVE_CAPABILITIES,
    isEffectiveCapabilityEnabled,
    type EffectiveCapabilities,
    type EffectiveCapabilityId,
} from './effective-capabilities.ts'

export type UserRole = string | null | undefined
export type NavigationSection = 'product' | 'ops' | 'settings'

export interface NavigationItem {
    href: string
    label: string
    icon: 'timeline' | 'dashboard' | 'positions' | 'strategies' | 'daily' | 'insights' | 'settings' | 'adminJobs' | 'adminOps'
    section: NavigationSection
    requiredCapability?: EffectiveCapabilityId
}

const productItems: NavigationItem[] = [
    { href: '/timeline', label: '时间线', icon: 'timeline', section: 'product' },
    { href: '/dashboard', label: '看板', icon: 'dashboard', section: 'product' },
    { href: '/positions', label: '交易', icon: 'positions', section: 'product' },
    { href: '/strategies', label: '策略', icon: 'strategies', section: 'product' },
    { href: '/daily', label: '日历', icon: 'daily', section: 'product' },
    { href: '/insights', label: '洞察', icon: 'insights', section: 'product', requiredCapability: 'AI_INSIGHTS' },
]

const adminItems: NavigationItem[] = [
    { href: '/admin/ops', label: '运维', icon: 'adminOps', section: 'ops' },
    { href: '/admin/jobs', label: '任务', icon: 'adminJobs', section: 'ops' },
]

const settingsItem: NavigationItem = { href: '/settings', label: '设置', icon: 'settings', section: 'settings' }

export function getVisibleNavigationItems(
    role: UserRole,
    effectiveCapabilities: EffectiveCapabilities = DISABLED_EFFECTIVE_CAPABILITIES,
): NavigationItem[] {
    const visibleProductItems = productItems.filter((item) => (
        !item.requiredCapability
        || isEffectiveCapabilityEnabled(effectiveCapabilities, item.requiredCapability)
    ))

    if (role === 'admin') {
        return [...visibleProductItems, ...adminItems, settingsItem]
    }
    return [...visibleProductItems, settingsItem]
}

export function isNavigationItemActive(href: string, pathname: string): boolean {
    if (href === '/timeline') return pathname === href
    return pathname === href || pathname.startsWith(`${href}/`)
}
