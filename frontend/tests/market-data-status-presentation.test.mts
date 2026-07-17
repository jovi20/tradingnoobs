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

test('journal baseline position forms do not load or present market data', () => {
  const pages = [
    readSource('app/(product)/positions/new/page.tsx'),
    readSource('app/(product)/positions/[id]/add-batch/page.tsx'),
  ]

  for (const source of pages) {
    assert.doesNotMatch(source, /marketAPI|MARKET_RUNTIME_ENABLED|SymbolValidation/)
    assert.doesNotMatch(source, /buildMarketDataStatus|validateSymbol|marketDataStatus/)
    assert.doesNotMatch(source, /行情来源：|新鲜度：|数据截至：/)
    assert.doesNotMatch(source, /选择行情源|切换行情源|setMarketProvider/)
  }
})

test('new-position requires manual release identity and only matches same-side positions', () => {
  const source = readSource('app/(product)/positions/new/page.tsx')

  assert.match(source, /\{ value: 'STOCK', label:/)
  assert.match(source, /\{ value: 'FUND', label:/)
  assert.match(source, /\{ value: 'CRYPTO', label:/)
  assert.match(source, /\{ value: 'US', label:/)
  assert.match(source, /value="USD"/)
  assert.match(source, /value="SPOT"/)
  assert.match(source, /existing && existing\.direction === form\.direction/)
  assert.doesNotMatch(source, /detectSymbolType|symbolValidation|isValidating/)
})
