export type SupportedChartType = 'bar' | 'line' | 'scatter' | 'sankey'

export interface ChartSeriesRef {
    field: string
    label: string
    color?: string
}

export interface ChartSchema {
    schema_version: 'chart.v1'
    chart_type: SupportedChartType
    series: ChartSeriesRef[]
    dimensions?: Array<{ field: string; label: string }>
    data_path?: string
    options?: Record<string, string | number | boolean | null>
}

export interface InsightArtifactTrustMeta {
    freshness?: string
    source?: string
    source_refs?: string[]
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
    trust_meta: InsightArtifactTrustMeta
    created_at?: string | null
}

export interface InsightRun {
    public_id: string
    run_type: string
    status: string
    prompt_version: string | null
    input_refs: string[]
    started_at: string
    completed_at: string | null
    error_code: string | null
    error_message: string | null
    artifacts: InsightArtifact[]
}

export interface InsightArtifactDetail extends InsightArtifact {
    run: Omit<InsightRun, 'artifacts'>
}

export interface AuditableInsightCard {
    artifact: InsightArtifact
    run: InsightRun
    title: string
    artifactType: string
    primaryContent: string
    legacyReadOnlyContent: string | null
    href: string
    evidenceRefs: string[]
    sourceRefs: string[]
    chartSchema: ChartSchema | null
}

const supportedChartTypes: ReadonlySet<string> = new Set(['bar', 'line', 'scatter', 'sankey'])

export function assertSupportedChartSchema(schema: ChartSchema | null | undefined): boolean {
    if (!schema) return false
    if (schema.schema_version !== 'chart.v1') return false
    if (!supportedChartTypes.has(schema.chart_type)) return false
    if (!Array.isArray(schema.series) || schema.series.length === 0) return false
    if (schema.dimensions && !schema.dimensions.every((dimension) => Boolean(dimension.field && dimension.label))) return false
    return schema.series.every((series) => Boolean(series.field && series.label))
}

export function buildAuditableInsightCards(runs: InsightRun[] = [], limit = Number.POSITIVE_INFINITY): AuditableInsightCard[] {
    return runs
        .flatMap((run) => run.artifacts.map((artifact) => {
            const sourceRefs = artifact.trust_meta.source_refs ?? []
            return {
                artifact,
                run,
                title: artifact.title,
                artifactType: artifact.artifact_type,
                primaryContent: artifact.summary,
                legacyReadOnlyContent: artifact.content_markdown,
                href: `/insights/${artifact.public_id}`,
                evidenceRefs: artifact.evidence_refs ?? [],
                sourceRefs,
                chartSchema: artifact.chart_schema,
            }
        }))
        .slice(0, limit)
}
