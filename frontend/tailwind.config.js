/** @type {import('tailwindcss').Config} */

// Semantic color tokens resolve to CSS variables defined in app/globals.css
// (:root + .dark). Each variable holds space-separated RGB channels so Tailwind
// can apply opacity via the `<alpha-value>` slot. Single source of truth for the
// "calm paper workbench" theme; dark mode is a full second theme, not a tint.
function withOpacity(variable) {
    return ({ opacityValue } = {}) =>
        opacityValue === undefined
            ? `rgb(var(${variable}))`
            : `rgb(var(${variable}) / ${opacityValue})`
}

module.exports = {
    darkMode: 'class',
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    theme: {
        extend: {
            colors: {
                // Surfaces
                canvas: withOpacity('--tn-canvas'),
                panel: withOpacity('--tn-panel'),
                'panel-subtle': withOpacity('--tn-panel-subtle'),
                // Lines
                line: withOpacity('--tn-border'),
                'line-strong': withOpacity('--tn-border-strong'),
                // Text (ink)
                ink: withOpacity('--tn-ink'),
                'ink-soft': withOpacity('--tn-ink-soft'),
                'ink-muted': withOpacity('--tn-ink-muted'),
                'ink-faint': withOpacity('--tn-ink-faint'),
                // Semantic status
                profit: withOpacity('--tn-profit'),
                loss: withOpacity('--tn-loss'),
                ai: withOpacity('--tn-ai'),
                warning: withOpacity('--tn-warning'),

                // Legacy scales — kept during migration, removed in Phase 6.
                primary: {
                    50: '#f8fafc', 100: '#f1f5f9', 200: '#e2e8f0', 300: '#cbd5e1',
                    400: '#94a3b8', 500: '#0f172a', 600: '#020617', 700: '#000000',
                    800: '#1e293b', 900: '#334155',
                },
                accent: {
                    50: '#f8fafc', 100: '#f1f5f9', 200: '#e2e8f0', 300: '#cbd5e1',
                    400: '#94a3b8', 500: '#64748b', 600: '#475569', 700: '#334155',
                    800: '#1e293b', 900: '#0f172a',
                },
            },
            fontFamily: {
                sans: ['var(--font-sans)', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans SC', 'system-ui', 'sans-serif'],
                mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
                serif: ['Songti SC', 'STSong', 'Georgia', 'Noto Serif SC', 'serif'],
            },
            borderRadius: {
                sm: '8px',
                DEFAULT: '10px',
                md: '12px',
                lg: '16px',
                xl: '20px',
            },
            boxShadow: {
                panel: '0 1px 2px rgb(16 15 14 / 0.04), 0 1px 3px rgb(16 15 14 / 0.03)',
                'panel-lg': '0 4px 16px rgb(16 15 14 / 0.06), 0 1px 3px rgb(16 15 14 / 0.04)',
                pop: '0 8px 28px rgb(16 15 14 / 0.12), 0 2px 6px rgb(16 15 14 / 0.06)',
                focus: '0 0 0 3px rgb(var(--tn-ring) / 0.35)',
            },
            ringColor: {
                DEFAULT: 'rgb(var(--tn-ring) / 0.5)',
            },
            animation: {
                'fade-in': 'fadeIn 0.35s ease-out',
                'rise-in': 'riseIn 0.4s cubic-bezier(0.22, 1, 0.36, 1)',
                'scale-in': 'scaleIn 0.16s cubic-bezier(0.22, 1, 0.36, 1)',
                'slide-up': 'slideUp 0.28s cubic-bezier(0.22, 1, 0.36, 1)',
                'slide-in-right': 'slideInRight 0.3s cubic-bezier(0.22, 1, 0.36, 1)',
            },
            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0' },
                    '100%': { opacity: '1' },
                },
                riseIn: {
                    '0%': { transform: 'translateY(8px)', opacity: '0' },
                    '100%': { transform: 'translateY(0)', opacity: '1' },
                },
                scaleIn: {
                    '0%': { transform: 'scale(0.97)', opacity: '0' },
                    '100%': { transform: 'scale(1)', opacity: '1' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(100%)' },
                    '100%': { transform: 'translateY(0)' },
                },
                slideInRight: {
                    '0%': { transform: 'translateX(100%)' },
                    '100%': { transform: 'translateX(0)' },
                },
            },
        },
    },
    plugins: [],
}
