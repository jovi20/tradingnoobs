import localFont from 'next/font/local'

// Self-hosted IBM Plex families. Latin subset only — CJK falls back to the
// system stack declared in globals.css so we never ship multi-MB webfonts.
export const plexSans = localFont({
    src: [
        { path: './PlexSans-400.woff2', weight: '400', style: 'normal' },
        { path: './PlexSans-500.woff2', weight: '500', style: 'normal' },
        { path: './PlexSans-600.woff2', weight: '600', style: 'normal' },
        { path: './PlexSans-700.woff2', weight: '700', style: 'normal' },
    ],
    variable: '--font-sans',
    display: 'swap',
    fallback: ['PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', 'system-ui', 'sans-serif'],
})

export const plexMono = localFont({
    src: [
        { path: './PlexMono-400.woff2', weight: '400', style: 'normal' },
        { path: './PlexMono-500.woff2', weight: '500', style: 'normal' },
    ],
    variable: '--font-mono',
    display: 'swap',
    fallback: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
})
