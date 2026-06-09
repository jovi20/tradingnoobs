export const THEME_STORAGE_KEY = 'theme'

export const themePreferences = ['light', 'dark', 'system'] as const

export type ThemePreference = (typeof themePreferences)[number]
export type ResolvedTheme = Exclude<ThemePreference, 'system'>

export function isThemePreference(value: unknown): value is ThemePreference {
  return typeof value === 'string' && themePreferences.includes(value as ThemePreference)
}

export function resolveThemePreference(theme: ThemePreference, prefersDark: boolean): ResolvedTheme {
  if (theme === 'system') {
    return prefersDark ? 'dark' : 'light'
  }
  return theme
}

export function getNextThemePreference(theme: ThemePreference): ThemePreference {
  if (theme === 'light') return 'dark'
  if (theme === 'dark') return 'system'
  return 'light'
}
