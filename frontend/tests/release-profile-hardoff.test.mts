import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import {
  BROKER_SYNC_RUNTIME_ENABLED,
  MARKET_RUNTIME_ENABLED,
  RELEASE_PROFILE,
  resolveReleaseProfile,
} from '../lib/release-profile.ts'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readSource(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('unknown or missing frontend profile fails closed to JOURNAL_BASELINE', () => {
  assert.equal(resolveReleaseProfile(undefined), 'JOURNAL_BASELINE')
  assert.equal(resolveReleaseProfile('unknown'), 'JOURNAL_BASELINE')
  assert.equal(resolveReleaseProfile('DEVELOPMENT_FULL'), 'DEVELOPMENT_FULL')
  assert.equal(RELEASE_PROFILE, 'JOURNAL_BASELINE')
  assert.equal(BROKER_SYNC_RUNTIME_ENABLED, false)
  assert.equal(MARKET_RUNTIME_ENABLED, false)
})

test('launch profile cannot be changed through browser process env', () => {
  const profileSource = readSource('lib/release-profile.ts')
  const generatedContractSource = readSource('lib/generated/release-contract.ts')

  assert.match(profileSource, /RELEASE_PROFILE: ReleaseProfile = 'JOURNAL_BASELINE'/)
  assert.doesNotMatch(profileSource, /process\.env/)
  assert.match(profileSource, /from '\.\/generated\/release-contract\.ts'/)
  assert.match(generatedContractSource, /MARKET_RUNTIME_ENABLED = false as const/)
  assert.match(generatedContractSource, /BROKER_SYNC_RUNTIME_ENABLED = false as const/)
})

test('optional UI calls are guarded by the build-time release profile', () => {
  const settingsPage = readSource('app/(product)/settings/page.tsx')
  const dailyPage = readSource('app/(product)/daily/page.tsx')
  const newPositionPage = readSource('app/(product)/positions/new/page.tsx')
  const addBatchPage = readSource('app/(product)/positions/[id]/add-batch/page.tsx')
  const adminOpsPage = readSource('app/(admin)/admin/ops/page.tsx')

  assert.match(settingsPage, /BROKER_SYNC_RUNTIME_ENABLED && \(/)
  assert.match(settingsPage, /if \(BROKER_SYNC_RUNTIME_ENABLED\)/)
  assert.match(dailyPage, /MARKET_RUNTIME_ENABLED\s*\? await Promise\.all\(/)
  assert.match(dailyPage, /buildLocalMarketCalendar\(market, year, month \+ 1\)/)
  assert.match(newPositionPage, /if \(!MARKET_RUNTIME_ENABLED\)/)
  assert.match(addBatchPage, /MARKET_RUNTIME_ENABLED && data\.status === 'OPEN'/)
  assert.match(adminOpsPage, /MARKET_RUNTIME_ENABLED && platformForm\.finnhubApiKey\.trim\(\)/)
  assert.match(adminOpsPage, /MARKET_RUNTIME_ENABLED && <LabeledInput/)
})
