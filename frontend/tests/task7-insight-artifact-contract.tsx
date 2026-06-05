import {
    assertSupportedChartSchema,
    type ChartSchema,
    type InsightArtifact,
    type InsightRun,
} from '@/lib/insightArtifacts'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'

const chartSchema: ChartSchema = {
    schema_version: 'chart.v1',
    chart_type: 'bar',
    series: [{ field: 'avg_pnl', label: 'Average PnL' }],
}

const artifact: InsightArtifact = {
    public_id: 'artifact-1',
    artifact_type: 'analysis_card',
    title: 'Strategy health',
    summary: 'Average loss still needs work.',
    content_markdown: null,
    payload: { linked_surface: 'insights' },
    evidence_refs: ['analysis:strategy_health'],
    chart_schema: chartSchema,
    trust_meta: {
        freshness: 'FRESH',
        source: 'AI_GENERATED',
        source_refs: ['analysis:strategy_health'],
    },
}

const run: InsightRun = {
    public_id: 'run-1',
    run_type: 'analysis.strategy_health',
    status: 'COMPLETED',
    prompt_version: 'v1',
    input_refs: ['analysis:strategy_health'],
    started_at: '2026-06-05T12:00:00Z',
    completed_at: '2026-06-05T12:01:00Z',
    error_code: null,
    error_message: null,
    artifacts: [artifact],
}

function InsightArtifactContractConsumer({ token }: { token: string | null }) {
    const query = useInsightRuns(token)
    return (
        <EvidenceLinkedInsightSidecar
            runs={query.data ?? [run]}
            isLoading={query.isLoading}
            error={query.error ? query.error.message : null}
            onRefresh={() => query.refetch()}
        />
    )
}

export const task7InsightArtifactContract = {
    run,
    artifact,
    isSupported: assertSupportedChartSchema(chartSchema),
    InsightArtifactContractConsumer,
}
