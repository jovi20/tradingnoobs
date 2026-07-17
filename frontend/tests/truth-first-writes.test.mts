import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readFrontendFile(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

function assertTruthCallBeforeLegacyFallback(source: string, fileLabel: string): void {
  const truthCall = source.indexOf('positionsAPI.createTradingPositionTradeEvent')
  const legacyFallback = source.indexOf('positionsAPI.addBatch')

  assert.notEqual(truthCall, -1, `${fileLabel} should call truth event write API`)
  assert.notEqual(legacyFallback, -1, `${fileLabel} should isolate any remaining legacy fallback`)
  assert.ok(truthCall < legacyFallback, `${fileLabel} should attempt truth event writes before legacy fallback`)
}

test('add-batch page makes legacy batch writes an explicit migration fallback', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/add-batch/page.tsx')

  assertTruthCallBeforeLegacyFallback(source, 'add-batch page')
  assert.match(source, /getTruthFirstWriteFallbackState/)
  assert.match(source, /migrationFallback/)
  assert.match(source, /migrationFallback: true/)
  assert.ok(
    source.indexOf('fallbackState.canWriteLegacyFallback') < source.indexOf('positionsAPI.addBatch'),
    'add-batch page should check fallback permission before addBatch',
  )
})

test('positions API marks explicit legacy batch fallback with migration header', () => {
  const source = readFrontendFile('lib/api.ts')

  assert.match(source, /X-Migration-Fallback/)
  assert.match(source, /legacy-batch-write/)
})

test('new-position add-to-existing flow does not silently fall back to legacy batch writes', () => {
  const source = readFrontendFile('app/(product)/positions/new/page.tsx')

  assertTruthCallBeforeLegacyFallback(source, 'new-position page')
  assert.match(source, /getTruthFirstWriteFallbackState/)
  assert.ok(
    source.indexOf('setError\\(fallbackState.reason\\)') !== -1 ||
    source.indexOf('setError(fallbackState.reason)') !== -1,
    'new-position page should surface fallback guidance instead of silently writing legacy batch',
  )
  assert.ok(
    source.indexOf('fallbackState.canWriteLegacyFallback') < source.indexOf('positionsAPI.addBatch'),
    'new-position page should gate addBatch behind fallback permission',
  )
})

test('new-position create flow keeps the legacy public id as the canonical page route', () => {
  const source = readFrontendFile('app/(product)/positions/new/page.tsx')

  assert.match(source, /truth_position_public_id/)
  assert.ok(
    source.indexOf('positionsAPI.create') < source.indexOf('truth_position_public_id'),
    'new-position page should read the truth id from the create response',
  )
  assert.ok(
    source.indexOf('truth_position_public_id') < source.indexOf('router.push(`/positions/${createdPosition.public_id}`)'),
    'new-position page should confirm truth sync before routing through the canonical legacy public id',
  )
})

test('add and close forms derive close limits from the truth lifecycle snapshot', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/add-batch/page.tsx')

  assert.match(source, /truthLifecycle\?\.openQuantity/)
  assert.match(source, /currentOpenQuantity/)
  assert.ok(
    source.indexOf('truthLifecycle?.openQuantity') < source.indexOf('平仓数量不能超过当前持仓'),
    'truth open quantity should be selected before close validation',
  )
})

test('truth event writes return to the canonical legacy position route', () => {
  const addBatchSource = readFrontendFile('app/(product)/positions/[id]/add-batch/page.tsx')
  const newPositionSource = readFrontendFile('app/(product)/positions/new/page.tsx')

  assert.match(addBatchSource, /router\.push\(`\/positions\/\$\{position\.public_id\}`\)/)
  assert.match(newPositionSource, /router\.push\(`\/positions\/\$\{targetPosition\.routeId\}`\)/)
})
