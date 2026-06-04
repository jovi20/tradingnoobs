import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import {
    insightArtifactsAPI,
    insightRunDetailPath,
    insightRunsPath,
} from '@/lib/insightArtifactClient'
import type { InsightRun } from '@/lib/insightArtifacts'

const task6SidecarPositionId = '01JPOSITIONTASK6AISIDECAR000'
const task6SidecarRun: InsightRun = {
    public_id: '01JINSIGHTRUNTASK6AISIDECAR',
    run_type: 'lifecycle_sidecar',
    status: 'COMPLETED',
    prompt_version: 'task6-ai-sidecar-contract',
    input_refs: [task6SidecarPositionId],
    started_at: '2026-06-04T12:00:00.000Z',
    completed_at: '2026-06-04T12:01:00.000Z',
    error_code: null,
    error_message: null,
    artifacts: [
        {
            public_id: '01JARTIFACTTASK6AISIDECAR',
            artifact_type: 'decision_review',
            title: 'Evidence-linked thesis drift',
            summary: 'Checklist drift is linked to the opening thesis and one catalyst.',
            content_markdown: null,
            payload: { stance: 'watch' },
            evidence_refs: ['01JEVIDENCETASK6THESIS', '01JEVIDENCETASK6CATALYST'],
            chart_schema: {
                schema_version: 'chart.v1',
                chart_type: 'bar',
                series: [{ field: 'drift_score', label: 'Drift score' }],
            },
            trust_meta: {
                as_of: '2026-06-04T12:01:00.000Z',
                freshness: 'FRESH',
                source: 'AI_GENERATED',
                maturity: 'EARLY_SIGNAL',
                value_status: 'ESTIMATED',
                generated_by: 'insight_artifact_service',
                source_refs: ['01JEVIDENCETASK6THESIS', '01JEVIDENCETASK6CATALYST'],
            },
        },
    ],
}

async function contractFetch(token: string) {
    const runs: InsightRun[] = await insightArtifactsAPI.listRuns(token)
    const detail: InsightRun = await insightArtifactsAPI.getRun(
        token,
        runs[0]?.public_id ?? task6SidecarRun.public_id,
    )

    return detail.artifacts.every(
        (artifact) => artifact.evidence_refs.length > 0 && artifact.trust_meta.source_refs.length > 0,
    )
}

function ContractAISidecarConsumer({ token }: { token: string | null }) {
    const query = useInsightRuns(token)
    return (
        <EvidenceLinkedInsightSidecar
            runs={query.data ?? [task6SidecarRun]}
            isLoading={query.isLoading}
            error={query.error ? query.error.message : null}
            linkedObjectPublicId={task6SidecarPositionId}
            onRefresh={() => query.refetch()}
        />
    )
}

export const task6AiSidecarContract = {
    contractFetch,
    ContractAISidecarConsumer,
    insightRunsPath,
    insightRunDetailPath,
}
