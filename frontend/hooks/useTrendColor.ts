
import { useAuth } from '@/contexts/AuthContext'

export function useTrendColor() {
    const { settings } = useAuth()

    // Default to GREEN (International/Crypto)
    // If 'RED', then Red Up / Green Down
    const isGreenUp = !settings?.up_color || settings.up_color === 'GREEN'

    return {
        // Core Logic
        isGreenUp,

        // Tailwind Text Colors (semantic tokens; profit=up, loss=down by convention)
        upColor: isGreenUp ? 'text-profit' : 'text-loss',
        downColor: isGreenUp ? 'text-loss' : 'text-profit',

        // Tailwind Background+Text Colors (for tags/badges)
        upBg: isGreenUp ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss',
        downBg: isGreenUp ? 'bg-loss/10 text-loss' : 'bg-profit/10 text-profit',

        // Hex Colors (for Charts — literal hex required by the SVG renderer)
        upHex: isGreenUp ? '#1A7F5C' : '#B84A39',
        downHex: isGreenUp ? '#B84A39' : '#1A7F5C'
    }
}
