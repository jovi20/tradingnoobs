'use client'

import { Sun, Moon, Monitor } from 'lucide-react'
import { useTheme } from '@/components/ThemeProvider'
import { getNextThemePreference } from '@/lib/theme'

export function ThemeToggle() {
    const { theme, setTheme } = useTheme()
    const themeLabel = theme === 'light' ? '浅色' : theme === 'dark' ? '深色' : '跟随系统'

    const toggleTheme = () => {
        setTheme(getNextThemePreference(theme))
    }

    return (
        <button
            type="button"
            onClick={toggleTheme}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-ink-muted transition-colors hover:bg-panel-subtle hover:text-ink"
            title={`当前主题：${themeLabel}`}
            aria-label={`切换主题，当前为${themeLabel}`}
        >
            {theme === 'light' && <Sun className="h-[18px] w-[18px]" />}
            {theme === 'dark' && <Moon className="h-[18px] w-[18px]" />}
            {theme === 'system' && <Monitor className="h-[18px] w-[18px]" />}
        </button>
    )
}
