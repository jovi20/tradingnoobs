import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getNextThemePreference,
  isThemePreference,
  resolveThemePreference,
} from '../lib/theme.ts'

test('theme preference guard only accepts supported values', () => {
  assert.equal(isThemePreference('light'), true)
  assert.equal(isThemePreference('dark'), true)
  assert.equal(isThemePreference('system'), true)
  assert.equal(isThemePreference('sepia'), false)
  assert.equal(isThemePreference(null), false)
})

test('system preference resolves against the current media state', () => {
  assert.equal(resolveThemePreference('system', true), 'dark')
  assert.equal(resolveThemePreference('system', false), 'light')
  assert.equal(resolveThemePreference('dark', false), 'dark')
  assert.equal(resolveThemePreference('light', true), 'light')
})

test('theme toggle cycles light to dark to system', () => {
  assert.equal(getNextThemePreference('light'), 'dark')
  assert.equal(getNextThemePreference('dark'), 'system')
  assert.equal(getNextThemePreference('system'), 'light')
})
