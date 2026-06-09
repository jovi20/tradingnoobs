'use client'

import { createContext, useContext, useEffect, useSyncExternalStore, type ReactNode } from 'react'
import {
    THEME_STORAGE_KEY,
    isThemePreference,
    resolveThemePreference,
    type ResolvedTheme,
    type ThemePreference,
} from '@/lib/theme'

interface ThemeContextValue {
    theme: ThemePreference
    resolvedTheme: ResolvedTheme
    setTheme: (value: string) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)
const themePreferenceListeners = new Set<() => void>()

function readStoredThemePreference(): ThemePreference {
    if (typeof window === 'undefined') return 'system'

    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY)
    return isThemePreference(storedTheme) ? storedTheme : 'system'
}

function readServerThemePreference(): ThemePreference {
    return 'system'
}

function subscribeThemePreference(listener: () => void) {
    themePreferenceListeners.add(listener)

    const handleStorage = (event: StorageEvent) => {
        if (event.key === THEME_STORAGE_KEY) {
            listener()
        }
    }

    window.addEventListener('storage', handleStorage)

    return () => {
        themePreferenceListeners.delete(listener)
        window.removeEventListener('storage', handleStorage)
    }
}

function emitThemePreferenceChange() {
    themePreferenceListeners.forEach((listener) => listener())
}

function subscribeSystemPreference(listener: () => void) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    mediaQuery.addEventListener('change', listener)

    return () => mediaQuery.removeEventListener('change', listener)
}

function readSystemPrefersDark() {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyResolvedTheme(resolvedTheme: ResolvedTheme) {
    document.documentElement.classList.remove('light', 'dark')
    document.documentElement.classList.add(resolvedTheme)
    document.documentElement.style.colorScheme = resolvedTheme
}

export function ThemeProvider({ children }: { children: ReactNode }) {
    const theme = useSyncExternalStore(
        subscribeThemePreference,
        readStoredThemePreference,
        readServerThemePreference
    )
    const prefersDark = useSyncExternalStore(
        subscribeSystemPreference,
        readSystemPrefersDark,
        () => false
    )
    const resolvedTheme = resolveThemePreference(theme, prefersDark)

    useEffect(() => {
        applyResolvedTheme(resolvedTheme)
    }, [resolvedTheme])

    const setTheme = (value: string) => {
        if (!isThemePreference(value)) return

        window.localStorage.setItem(THEME_STORAGE_KEY, value)
        applyResolvedTheme(resolveThemePreference(value, readSystemPrefersDark()))
        emitThemePreferenceChange()
    }

    return (
        <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    )
}

export function useTheme() {
    const context = useContext(ThemeContext)
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider')
    }
    return context
}
