import test from 'node:test'
import assert from 'node:assert/strict'

import { ApiRequestError, isAuthenticationApiError } from '../lib/api.ts'

test('only explicit authentication responses invalidate a stored session', () => {
  assert.equal(isAuthenticationApiError(new ApiRequestError(401, 'Unauthorized')), true)
  assert.equal(isAuthenticationApiError(new ApiRequestError(403, 'Inactive user')), true)
  assert.equal(isAuthenticationApiError(new ApiRequestError(500, 'Upstream failure')), false)
  assert.equal(isAuthenticationApiError(new TypeError('Failed to fetch')), false)
})
