import {
    assertSupportedChartSchema,
    getChartSchemaBadge,
    type ChartSchema,
    type ChartTrustMeta,
} from './charts.ts'

export type { ChartSchema }
export type InsightArtifactTrustMeta = ChartTrustMeta

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

export interface InsightArtifactDetailView {
    title: string
    artifactType: string
    runType: string
    primaryContent: string
    legacyReadOnlyContent: string | null
    evidenceRefs: string[]
    sourceRefs: string[]
    chartBadge: string | null
    trustMeta: InsightArtifactTrustMeta
    createdAt?: string | null
}

export { assertSupportedChartSchema }

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

export function buildInsightArtifactDetailView(artifact: InsightArtifactDetail): InsightArtifactDetailView {
    return {
        title: artifact.title,
        artifactType: artifact.artifact_type,
        runType: artifact.run.run_type,
        primaryContent: artifact.summary,
        legacyReadOnlyContent: artifact.content_markdown,
        evidenceRefs: artifact.evidence_refs ?? [],
        sourceRefs: artifact.trust_meta.source_refs ?? [],
        chartBadge: getChartSchemaBadge(artifact.chart_schema),
        trustMeta: artifact.trust_meta,
        createdAt: artifact.created_at,
    }
}
