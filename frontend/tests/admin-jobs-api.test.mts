import test from 'node:test'
import assert from 'node:assert/strict'

import { adminAPI } from '../lib/api.ts'

test('admin job API client lists and reads jobs through admin endpoints', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch

  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    const url = String(input)
    if (url.includes('/api/admin/jobs?')) {
      return new Response(JSON.stringify({ items: [], total: 0, limit: 20 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    return new Response(JSON.stringify({
      public_id: 'job-1',
      definition: { public_id: 'def-1', key: 'derived.timeline.refresh', display_name: 'Refresh Timeline', queue_name: 'derived' },
      status: 'FAILED',
      queue_name: 'derived',
      priority: 0,
      payload: {},
      result: {},
      error_message: 'boom',
      attempt_count: 3,
      max_attempts: 3,
      locked_by: null,
      locked_at: null,
      next_run_at: null,
      started_at: null,
      finished_at: null,
      created_at: '2026-05-05T10:00:00Z',
      updated_at: null,
      business_locks: [],
      events: [],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const listed = await adminAPI.listJobs('token-1', { status: 'FAILED', queue_name: 'derived', limit: 20 })
    const detail = await adminAPI.getJob('token-1', 'job-1')

    assert.equal(listed.limit, 20)
    assert.equal(detail.public_id, 'job-1')
    assert.equal(calls.length, 2)
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/admin/jobs?status=FAILED&queue_name=derived&limit=20')
    assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer token-1')
    assert.equal(String(calls[1].input), 'http://localhost:8000/api/admin/jobs/job-1')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('admin job API client posts requeue and cancel actions', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch

  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(JSON.stringify({
      public_id: 'job-1',
      definition: { public_id: 'def-1', key: 'derived.timeline.refresh', display_name: 'Refresh Timeline', queue_name: 'derived' },
      status: 'QUEUED',
      queue_name: 'derived',
      priority: 0,
      payload: {},
      result: {},
      error_message: null,
      attempt_count: 0,
      max_attempts: 3,
      locked_by: null,
      locked_at: null,
      next_run_at: null,
      started_at: null,
      finished_at: null,
      created_at: '2026-05-05T10:00:00Z',
      updated_at: null,
      business_locks: [],
      events: [],
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    await adminAPI.requeueJob('token-1', 'job-1')
    await adminAPI.cancelJob('token-1', 'job-1')

    assert.equal(String(calls[0].input), 'http://localhost:8000/api/admin/jobs/job-1/requeue')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal(String(calls[1].input), 'http://localhost:8000/api/admin/jobs/job-1/cancel')
    assert.equal(calls[1].init?.method, 'POST')
  } finally {
    globalThis.fetch = originalFetch
  }
})
