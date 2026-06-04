import type { TrustMeta } from '@/lib/readModels'

export type SupportedChartType = 'bar' | 'line' | 'scatter' | 'sankey'

export interface ChartFieldRef {
    field: string
    label: string
    unit?: string
}

export interface ChartSeriesRef {
    field: string
    label: string
    color?: string
}

export interface ChartSchema {
    schema_version: 'chart.v1'
    chart_type: SupportedChartType
    x?: ChartFieldRef
    y?: ChartFieldRef
    series: ChartSeriesRef[]
    data_path?: string
    options?: Record<string, string | number | boolean | null>
}

export interface InsightArtifact {
    public_id: string
    artifact_type: string
    title: string
    summary: string
    content_markdown: string | null
    payload: Record<string, unknown>
    evidence_refs: string[]
    chart_schema: ChartSchema | null
    trust_meta: TrustMeta
}

export interface InsightRun {
    public_id: string
    run_type: string
    status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string
    prompt_version: string | null
    input_refs: string[]
    started_at: string
    completed_at: string | null
    error_code: string | null
    error_message: string | null
    artifacts: InsightArtifact[]
}

const supportedChartTypes: ReadonlySet<string> = new Set(['bar', 'line', 'scatter', 'sankey'])

export function assertSupportedChartSchema(schema: ChartSchema | null | undefined): boolean {
    if (!schema) return false
    if (schema.schema_version !== 'chart.v1') return false
    if (!supportedChartTypes.has(schema.chart_type)) return false
    if (!Array.isArray(schema.series) || schema.series.length === 0) return false
    return schema.series.every((series) => Boolean(series.field && series.label))
}
