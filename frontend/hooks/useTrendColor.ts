
import { useAuth } from '@/contexts/AuthContext'

export function useTrendColor() {
    const { settings } = useAuth()

    // Default to GREEN (International/Crypto)
    // If 'RED', then Red Up / Green Down
    const isGreenUp = !settings?.up_color || settings.up_color === 'GREEN'

    return {
        // Core Logic
        isGreenUp,

        // Tailwind Text Colors
        upColor: isGreenUp ? 'text-emerald-500' : 'text-red-500',
        downColor: isGreenUp ? 'text-red-500' : 'text-emerald-500',

        // Tailwind Background+Text Colors (for tags/badges)
        upBg: isGreenUp ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400' : 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400',
        downBg: isGreenUp ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400' : 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400',

        // Hex Colors (for Charts)
        upHex: isGreenUp ? '#10b981' : '#ef4444',
        downHex: isGreenUp ? '#ef4444' : '#10b981'
    }
}
