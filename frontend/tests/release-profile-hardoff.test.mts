import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import { RELEASE_PROFILE, resolveReleaseProfile } from '../lib/release-profile.ts'

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
})

test('launch profile cannot be changed through browser process env', () => {
  const profileSource = readSource('lib/release-profile.ts')
  const generatedContractSource = readSource('lib/generated/release-contract.ts')

  assert.match(profileSource, /RELEASE_PROFILE: ReleaseProfile = 'JOURNAL_BASELINE'/)
  assert.doesNotMatch(profileSource, /process\.env/)
  assert.match(profileSource, /from '\.\/generated\/release-contract\.ts'/)
  assert.doesNotMatch(profileSource, /RUNTIME_ENABLED/)
  assert.doesNotMatch(generatedContractSource, /RUNTIME_ENABLED/)
})

test('optional provider implementations are absent from baseline product surfaces', () => {
  const settingsPage = readSource('app/(product)/settings/page.tsx')
  const dailyPage = readSource('app/(product)/daily/page.tsx')
  const newPositionPage = readSource('app/(product)/positions/new/page.tsx')
  const addBatchPage = readSource('app/(product)/positions/[id]/add-batch/page.tsx')
  const adminOpsPage = readSource('app/(admin)/admin/ops/page.tsx')

  assert.doesNotMatch(settingsPage, /brokerSyncAPI|BROKER_SYNC_RUNTIME_ENABLED|ibkr_flex|binance_api/)
  assert.doesNotMatch(dailyPage, /marketAPI|MARKET_RUNTIME_ENABLED|buildLocalMarketCalendar|MarketCalendar/)
  assert.doesNotMatch(newPositionPage, /marketAPI|MARKET_RUNTIME_ENABLED|validateSymbol/)
  assert.doesNotMatch(addBatchPage, /marketAPI|MARKET_RUNTIME_ENABLED|validateSymbol/)
  assert.doesNotMatch(adminOpsPage, /MARKET_RUNTIME_ENABLED|LLM|OpenAI|Finnhub|testLLM/)
  assert.doesNotMatch(adminOpsPage, /listIntegrationCredentials|upsertIntegrationCredential/)
})
