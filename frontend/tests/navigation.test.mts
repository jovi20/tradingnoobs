import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getVisibleNavigationItems,
  isNavigationItemActive,
} from '../lib/navigation.ts'

test('regular users do not see admin navigation as a primary product item', () => {
  const items = getVisibleNavigationItems('user')
  assert.deepEqual(items.map((item) => item.href), [
    '/timeline',
    '/dashboard',
    '/positions',
    '/strategies',
    '/daily',
    '/insights',
    '/settings',
  ])
})

test('admins receive a separated ops item after product navigation', () => {
  const items = getVisibleNavigationItems('admin')
  assert.equal(items.at(-2)?.href, '/admin/jobs')
  assert.equal(items.at(-2)?.section, 'ops')
  assert.equal(items.at(-1)?.href, '/settings')
})

test('navigation active state handles nested paths', () => {
  assert.equal(isNavigationItemActive('/positions', '/positions/abc123'), true)
  assert.equal(isNavigationItemActive('/timeline', '/timeline'), true)
  assert.equal(isNavigationItemActive('/timeline', '/dashboard'), false)
})
