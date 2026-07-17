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

function assertTruthOnlyWrite(source: string, fileLabel: string): void {
  const truthCall = source.indexOf('positionsAPI.createTradingPositionTradeEvent')

  assert.notEqual(truthCall, -1, `${fileLabel} should call truth event write API`)
  assert.doesNotMatch(source, /positionsAPI\.addBatch/)
  assert.doesNotMatch(source, /migrationFallback|getTruthFirstWriteFallbackState/)
}

test('add-batch page writes only canonical truth events', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/add-batch/page.tsx')

  assertTruthOnlyWrite(source, 'add-batch page')
  assert.match(source, /旧版批次写入已从产品入口关闭/)
})

test('frontend API and adapters expose no public legacy batch fallback', () => {
  const source = readFrontendFile('lib/api.ts')
  const adapters = readFrontendFile('lib/adapters/trading.ts')

  assert.doesNotMatch(source, /X-Migration-Fallback|legacy-batch-write|addBatch:/)
  assert.doesNotMatch(adapters, /getTruthFirstWriteFallbackState|canWriteLegacyFallback/)
})

test('new-position add-to-existing flow writes only canonical truth events', () => {
  const source = readFrontendFile('app/(product)/positions/new/page.tsx')

  assertTruthOnlyWrite(source, 'new-position page')
  assert.match(source, /审计生命周期不可用，无法安全加仓/)
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
