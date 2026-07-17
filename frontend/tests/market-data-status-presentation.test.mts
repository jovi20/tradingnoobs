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
  const api = readSource('lib/api.ts')
  const tradingAdapter = readSource('lib/adapters/trading.ts')
  const submitSource = source.slice(
    source.indexOf('const submitPosition'),
    source.indexOf('const handleSubmit'),
  )

  assert.match(source, /\{ value: 'STOCK', label:/)
  assert.match(source, /\{ value: 'FUND', label:/)
  assert.match(source, /\{ value: 'CRYPTO', label:/)
  assert.match(source, /\{ value: 'US', label:/)
  assert.match(source, /value="USD"/)
  assert.match(source, /value="SPOT"/)
  assert.match(source, /exchange_code: ''/)
  assert.match(source, /交易所代码 \*/)
  assert.match(source, /maxLength=\{32\}/)
  assert.match(source, /getIdentityValidationError/)
  assert.match(source, /normalizeReleasePositionIdentityInput\(\{/)
  assert.match(source, /symbol: form\.symbol/)
  assert.match(source, /exchange_code: form\.exchange_code/)
  assert.match(source, /asset_type: form\.asset_type/)
  assert.match(source, /instrument_type: form\.metadata\.instrument/)
  assert.match(source, /quote_currency: form\.metadata\.currency/)
  assert.match(tradingAdapter, /reject every raw non-ASCII token before trimming or uppercasing any token/)
  assert.match(source, /buildOpenIdentity/)
  assert.match(source, /const openIdentity = buildOpenIdentity\(identitySnapshot\)/)
  assert.match(source, /positionsAPI\.checkOpen\([\s\S]*?openIdentity/)
  assert.match(source, /confirmed\.public_id !== existingPosition\.public_id/)
  assert.match(submitSource, /prepareForSubmission\(candidate\)/)
  assert.match(submitSource, /exchange_code: finalForm\.exchange_code/)
  assert.doesNotMatch(submitSource, /\.broker\b/)
  assert.match(api, /export interface PositionCreate \{[\s\S]*?exchange_code: string/)
  assert.match(api, /export type ReleaseAssetType = 'STOCK' \| 'FUND' \| 'CRYPTO'/)
  assert.match(api, /export interface Position \{[\s\S]*?asset_type: string \| null/)
  const positionCreate = api.slice(
    api.indexOf('export interface PositionCreate'),
    api.indexOf('export interface PositionUpdatePayload'),
  )
  assert.match(positionCreate, /asset_type: ReleaseAssetType/)
  assert.doesNotMatch(positionCreate, /EQUITY|ETF|SPOT_CRYPTO/)
  assert.match(api, /\/api\/positions\/check\/open\?\$\{query\.toString\(\)\}/)
  assert.doesNotMatch(source, /detectSymbolType|symbolValidation|isValidating/)
})
