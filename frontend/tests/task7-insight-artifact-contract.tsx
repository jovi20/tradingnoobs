import {
    assertSupportedChartSchema,
    type ChartSchema,
    type InsightArtifact,
    type InsightRun,
} from '@/lib/insightArtifacts'

const chartSchema: ChartSchema = {
    schema_version: 'chart.v1',
    chart_type: 'bar',
    x: { field: 'bucket', label: 'Bucket' },
    y: { field: 'count', label: 'Count' },
    series: [{ field: 'count', label: 'Trades' }],
}

const artifact: InsightArtifact = {
    public_id: '01JARTIFACTTASK7000000000',
    artifact_type: 'AI_CONCLUSION',
    title: 'Evidence-linked conclusion',
    summary: 'The conclusion is backed by evidence refs.',
    content_markdown: null,
    payload: { discipline_score: 0.82 },
    evidence_refs: ['01JEVIDENCETASK70000000000'],
    chart_schema: chartSchema,
    trust_meta: {
        as_of: '2026-06-04T00:00:00+00:00',
        freshness: 'FRESH',
        source: 'AI_GENERATED',
        maturity: 'EARLY_SIGNAL',
        value_status: 'ESTIMATED',
        generated_by: 'task7_contract',
        source_refs: ['01JEVIDENCETASK70000000000'],
    },
}

const run: InsightRun = {
    public_id: '01JRUNTASK7000000000000',
    run_type: 'WEEKLY_REVIEW',
    status: 'COMPLETED',
    prompt_version: 'weekly-review-v1',
    input_refs: ['TradingPosition:01JPOSITIONTASK7000000000'],
    started_at: '2026-06-04T00:00:00+00:00',
    completed_at: '2026-06-04T00:00:01+00:00',
    error_code: null,
    error_message: null,
    artifacts: [artifact],
}

export const task7InsightArtifactContract = {
    run,
    isSupported: assertSupportedChartSchema(chartSchema),
}
