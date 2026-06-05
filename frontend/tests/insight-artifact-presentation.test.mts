import test from 'node:test'
import assert from 'node:assert/strict'

import { buildAuditableInsightCards } from '../lib/insightArtifacts.ts'

test('auditable insight cards use artifact summary as primary content and retain legacy markdown separately', () => {
    const cards = buildAuditableInsightCards([
        {
            public_id: 'run-1',
            run_type: 'analysis.strategy_health',
            status: 'COMPLETED',
            prompt_version: 'v1',
            input_refs: ['analysis:strategy_health'],
            started_at: '2026-06-05T12:00:00Z',
            completed_at: '2026-06-05T12:01:00Z',
            error_code: null,
            error_message: null,
            artifacts: [
                {
                    public_id: 'artifact-1',
                    artifact_type: 'analysis_card',
                    title: 'Strategy health',
                    summary: 'Average loss still needs work.',
                    content_markdown: '# Legacy markdown body',
                    payload: { linked_surface: 'insights' },
                    evidence_refs: ['analysis:strategy_health'],
                    chart_schema: null,
                    trust_meta: {
                        freshness: 'FRESH',
                        source: 'AI_GENERATED',
                        source_refs: ['analysis:strategy_health', 'dataset:positions'],
                    },
                },
            ],
        },
    ])

    assert.equal(cards.length, 1)
    assert.equal(cards[0].primaryContent, 'Average loss still needs work.')
    assert.equal(cards[0].legacyReadOnlyContent, '# Legacy markdown body')
    assert.equal(cards[0].href, '/insights/artifact-1')
    assert.deepEqual(cards[0].evidenceRefs, ['analysis:strategy_health'])
    assert.deepEqual(cards[0].sourceRefs, ['analysis:strategy_health', 'dataset:positions'])
})
