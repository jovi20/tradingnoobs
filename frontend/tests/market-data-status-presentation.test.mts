import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readSource(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('position forms present routed market data provenance without a provider selector', () => {
  const pages = [
    readSource('app/(product)/positions/new/page.tsx'),
    readSource('app/(product)/positions/[id]/add-batch/page.tsx'),
  ]

  for (const source of pages) {
    assert.match(source, /buildMarketDataStatus/)
    assert.match(source, /行情来源：/)
    assert.match(source, /新鲜度：/)
    assert.match(source, /数据截至：/)
    assert.match(source, /marketDataStatus\.degradedReason/)
    assert.match(source, /role="status"/)
    assert.doesNotMatch(source, /选择行情源|切换行情源|setMarketProvider/)
  }
})

test('new-position market validation ignores responses for a superseded symbol', () => {
  const source = readSource('app/(product)/positions/new/page.tsx')

  assert.match(source, /let cancelled = false/)
  assert.match(source, /if \(cancelled\) return/)
  assert.match(source, /symbolValidation\?\.symbol === form\.symbol\.trim\(\)\.toUpperCase\(\)/)
})
