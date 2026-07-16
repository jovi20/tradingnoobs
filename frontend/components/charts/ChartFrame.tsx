import type { ReactNode } from 'react'

import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import {
    assertSupportedChartSchema,
    formatChartEmptyStateCopy,
    formatChartTrustLabel,
    getChartFreshnessTone,
    getChartSchemaBadge,
    hasChartData,
    type ChartEmptyState,
    type ChartSchema,
    type ChartTrustMeta,
} from '@/lib/charts'

interface ChartFrameProps {
    title: string
    eyebrow?: string
    description?: string
    schema?: ChartSchema | null
    trustMeta?: ChartTrustMeta | null
    emptyState?: ChartEmptyState | null
    dataCount?: number
    compact?: boolean
    className?: string
    children: ReactNode
    footer?: ReactNode
    action?: ReactNode
}

export function ChartFrame({
    title,
    eyebrow = '图表',
    description,
    schema,
    trustMeta,
    emptyState,
    dataCount,
    compact = false,
    className = '',
    children,
    footer,
    action,
}: ChartFrameProps) {
    const schemaBadge = getChartSchemaBadge(schema)
    const trustLabel = formatChartTrustLabel(trustMeta)
    const emptyStateCopy = formatChartEmptyStateCopy(emptyState)
    const hasData = dataCount === undefined
        ? !emptyState?.is_empty
        : hasChartData(new Array(dataCount).fill(true), emptyState)

    return (
        <Surface className={`${compact ? 'p-4' : 'p-4 md:p-5'} ${className}`}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <SectionHeader
                    eyebrow={eyebrow}
                    title={title}
                    description={description}
                    action={action}
                />
                <div className="flex flex-wrap gap-2 sm:justify-end">
                    {schemaBadge && (
                        <StatusPill tone={assertSupportedChartSchema(schema) ? 'review' : 'warning'}>
                            {schemaBadge}
                        </StatusPill>
                    )}
                    <StatusPill tone={getChartFreshnessTone(trustMeta)}>
                        {trustLabel}
                    </StatusPill>
                </div>
            </div>
            <div className={compact ? 'mt-3' : 'mt-4'}>
                {hasData ? children : (
                    <EmptyStatePanel
                        title={emptyStateCopy.title}
                        detail={emptyStateCopy.detail}
                    />
                )}
            </div>
            {trustMeta?.source_refs && trustMeta.source_refs.length > 0 && (
                <p className="mt-3 break-all text-[11px] text-ink-faint">
                    来源引用：{trustMeta.source_refs.join(', ')}
                </p>
            )}
            {footer && <div className="mt-3">{footer}</div>}
        </Surface>
    )
}
