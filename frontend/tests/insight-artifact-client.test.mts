import test from 'node:test'
import assert from 'node:assert/strict'

import {
  insightArtifactDetailPath,
  insightArtifactsAPI,
} from '../lib/insightArtifactClient.ts'

test('insight artifact client builds artifact detail path', () => {
  assert.equal(insightArtifactDetailPath('artifact-1'), '/api/v1/insights/artifacts/artifact-1')
})

test('insight artifact client fetches artifact detail', async () => {
  const originalFetch = globalThis.fetch
  const calls: string[] = []
  globalThis.fetch = async (input: RequestInfo | URL) => {
    calls.push(String(input))
    return new Response(JSON.stringify({ public_id: 'artifact-1', run: { public_id: 'run-1' } }), { status: 200 })
  }

  try {
    const result = await insightArtifactsAPI.getArtifact('token-1', 'artifact-1')
    assert.equal(result.public_id, 'artifact-1')
    assert.match(calls[0], /\/api\/v1\/insights\/artifacts\/artifact-1$/)
  } finally {
    globalThis.fetch = originalFetch
  }
})
