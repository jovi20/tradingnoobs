import test from 'node:test'
import assert from 'node:assert/strict'

import {
  formatBackupResult,
  formatPasswordResetNotice,
  isValidUserPublicIdInput,
} from '../lib/adapters/admin-ops.ts'

test('formatBackupResult surfaces backend, path, and created timestamp', () => {
  const result = formatBackupResult({
    status: 'SUCCESS',
    backup_id: 'sqlite-20260611T101010000000Z',
    path: '/tmp/backups/sqlite-20260611T101010000000Z.db',
    database_backend: 'sqlite',
    created_at: '2026-06-11T10:10:10Z',
    message: 'SQLite database backup completed.',
  })

  assert.equal(result.statusLabel, '成功')
  assert.equal(result.backendLabel, 'SQLite')
  assert.equal(result.fileName, 'sqlite-20260611T101010000000Z.db')
  assert.match(result.createdLabel, /2026/)
  assert.equal(result.description, 'SQLite database backup completed.')
})

test('formatPasswordResetNotice emphasizes one-time temporary password handling', () => {
  const notice = formatPasswordResetNotice({
    status: 'SUCCESS',
    user_public_id: 'user-public-id',
    temporary_password: 'TempPassword123456',
    active_sessions_revoked: true,
    revoked_session_count: 2,
    revoked_token_count: 3,
    message: 'Temporary password generated and only shown once.',
  })

  assert.equal(notice.temporaryPassword, 'TempPassword123456')
  assert.equal(notice.sessionNotice, '已撤销 2 个会话和 3 个令牌。')
  assert.match(notice.securityNotice, /仅显示一次/)
})

test('isValidUserPublicIdInput rejects empty or whitespace input', () => {
  assert.equal(isValidUserPublicIdInput(''), false)
  assert.equal(isValidUserPublicIdInput('   '), false)
  assert.equal(isValidUserPublicIdInput('user-public-id'), true)
})
