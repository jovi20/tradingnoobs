import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptAdminJobsPageData,
  getAdminJobActions,
  getAdminJobStatusTone,
} from '../lib/adapters/admin-jobs.ts'

test('adaptAdminJobsPageData summarizes job status counts and latest failures', () => {
  const result = adaptAdminJobsPageData({
    items: [
      {
        public_id: 'job-failed',
        definition: { public_id: 'def-1', key: 'derived.timeline.refresh', display_name: 'Refresh Timeline' },
        status: 'FAILED',
        queue_name: 'derived',
        priority: 0,
        attempt_count: 3,
        max_attempts: 3,
        next_run_at: null,
        started_at: '2026-05-05T10:00:00Z',
        finished_at: '2026-05-05T10:01:00Z',
        created_at: '2026-05-05T09:59:00Z',
        error_message: 'handler exploded',
      },
      {
        public_id: 'job-running',
        definition: { public_id: 'def-1', key: 'derived.timeline.refresh', display_name: 'Refresh Timeline' },
        status: 'RUNNING',
        queue_name: 'derived',
        priority: 10,
        attempt_count: 1,
        max_attempts: 3,
        next_run_at: null,
        started_at: '2026-05-05T10:02:00Z',
        finished_at: null,
        created_at: '2026-05-05T10:02:00Z',
        error_message: null,
      },
      {
        public_id: 'job-queued',
        definition: { public_id: 'def-2', key: 'market.warmup', display_name: 'Market Warmup' },
        status: 'QUEUED',
        queue_name: 'market',
        priority: 1,
        attempt_count: 0,
        max_attempts: 2,
        next_run_at: '2026-05-05T10:05:00Z',
        started_at: null,
        finished_at: null,
        created_at: '2026-05-05T10:03:00Z',
        error_message: null,
      },
    ],
    total: 3,
    limit: 50,
  })

  assert.equal(result.total, 3)
  assert.deepEqual(result.counts, {
    QUEUED: 1,
    RUNNING: 1,
    SUCCEEDED: 0,
    FAILED: 1,
    RETRYING: 0,
    CANCELLED: 0,
  })
  assert.equal(result.items[0].statusLabel, 'Failed')
  assert.equal(result.items[0].attemptLabel, '3/3 attempts')
  assert.equal(result.latestFailures[0].public_id, 'job-failed')
  assert.equal(result.queues.join(','), 'derived,market')
})

test('admin job adapter exposes safe actions by status', () => {
  assert.deepEqual(getAdminJobActions('FAILED'), { canRequeue: true, canCancel: false })
  assert.deepEqual(getAdminJobActions('RETRYING'), { canRequeue: true, canCancel: true })
  assert.deepEqual(getAdminJobActions('QUEUED'), { canRequeue: false, canCancel: true })
  assert.deepEqual(getAdminJobActions('RUNNING'), { canRequeue: false, canCancel: false })
  assert.deepEqual(getAdminJobActions('SUCCEEDED'), { canRequeue: false, canCancel: false })
})

test('admin job status tones stay deterministic', () => {
  assert.equal(getAdminJobStatusTone('QUEUED').label, 'Queued')
  assert.equal(getAdminJobStatusTone('RUNNING').label, 'Running')
  assert.equal(getAdminJobStatusTone('SUCCEEDED').label, 'Succeeded')
  assert.equal(getAdminJobStatusTone('FAILED').label, 'Failed')
  assert.equal(getAdminJobStatusTone('RETRYING').label, 'Retrying')
  assert.equal(getAdminJobStatusTone('CANCELLED').label, 'Cancelled')
})
