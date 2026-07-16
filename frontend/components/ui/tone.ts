import type { WorkbenchTone } from '@/lib/adapters/timeline-workbench'

/**
 * Central tone → class mappings for the semantic status palette.
 * Every badge / pill / tile / callout resolves color through these maps so the
 * whole product speaks one color language (profit green, loss red, ai indigo…).
 */

export type Tone = WorkbenchTone

// Solid text color (metric values, inline emphasis)
export const toneText: Record<Tone, string> = {
    neutral: 'text-ink',
    positive: 'text-profit',
    negative: 'text-loss',
    warning: 'text-warning',
    danger: 'text-loss',
    entry: 'text-profit',
    exit: 'text-warning',
    review: 'text-ai',
    ai: 'text-ai',
}

// Soft pill / badge (tinted background + readable text)
export const toneSoft: Record<Tone, string> = {
    neutral: 'bg-panel-subtle text-ink-muted',
    positive: 'bg-profit/10 text-profit',
    negative: 'bg-loss/10 text-loss',
    warning: 'bg-warning/12 text-warning',
    danger: 'bg-loss/10 text-loss',
    entry: 'bg-profit/10 text-profit',
    exit: 'bg-warning/12 text-warning',
    review: 'bg-ai/10 text-ai',
    ai: 'bg-ai/10 text-ai',
}

// Dot / accent marker background
export const toneDot: Record<Tone, string> = {
    neutral: 'bg-ink-faint',
    positive: 'bg-profit',
    negative: 'bg-loss',
    warning: 'bg-warning',
    danger: 'bg-loss',
    entry: 'bg-profit',
    exit: 'bg-warning',
    review: 'bg-ai',
    ai: 'bg-ai',
}

// Left border accent (event rails, callouts)
export const toneBorder: Record<Tone, string> = {
    neutral: 'border-line-strong',
    positive: 'border-profit',
    negative: 'border-loss',
    warning: 'border-warning',
    danger: 'border-loss',
    entry: 'border-profit',
    exit: 'border-warning',
    review: 'border-ai',
    ai: 'border-ai',
}
