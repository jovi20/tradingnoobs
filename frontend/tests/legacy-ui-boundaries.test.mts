import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, relative, resolve } from 'node:path'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')
const repoRoot = resolve(frontendRoot, '..')

const legacyDtoImportAllowlist = {
  migration_ui: [
    'app/positions/[id]/add-batch/page.tsx',
    'app/positions/page.tsx',
  ],
  create_sync_bridge: [
    'app/positions/new/page.tsx',
  ],
  legacy_analytics: [
    'components/dashboard/MaeMfeScatterPlot.tsx',
    'lib/adapters/chart-views.ts',
  ],
  adapter_boundary: [
    'lib/adapters/trading.ts',
  ],
} as const

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function readFrontendFile(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

function readRepoFile(relativePath: string): string {
  return readFileSync(resolve(repoRoot, relativePath), 'utf8')
}

function listSourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((entry) => {
    const fullPath = resolve(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      if (['node_modules', '.next', 'tests'].includes(entry)) return []
      return listSourceFiles(fullPath)
    }
    return /\.(ts|tsx)$/.test(entry) ? [fullPath] : []
  })
}

test('positions list labels expanded batch rows as migration/support context', () => {
  const source = readFrontendFile('app/positions/page.tsx')

  assert.match(source, /Legacy batch timeline/)
  assert.match(source, /Migration\/support context/)
  assert.match(source, /Truth add event/)
  assert.match(source, /Truth reduce\/close event/)
})

test('add-batch page visibly distinguishes truth writes from legacy migration fallback', () => {
  const source = readFrontendFile('app/positions/[id]/add-batch/page.tsx')

  assert.match(source, /Truth write path/)
  assert.match(source, /TradingPosition \/ PositionEvent/)
  assert.match(source, /legacy batch migration fallback/)
})

test('raw legacy trading DTO imports stay inside migration and adapter boundaries', () => {
  const importBlockPattern = /import\s+(?:type\s+)?{[\s\S]*?}\s+from\s+['"][^'"]*api(?:\.ts)?['"]/g
  const legacyDtoPattern = /\b(Position|TradeBatch|BatchCreate|Transaction)\b/
  const filesWithLegacyDtoImports = listSourceFiles(frontendRoot)
    .filter((file) => {
      const source = readFileSync(file, 'utf8')
      return [...source.matchAll(importBlockPattern)].some((match) => legacyDtoPattern.test(match[0]))
    })
    .map((file) => relative(frontendRoot, file))
    .sort()

  assert.deepEqual(filesWithLegacyDtoImports, Object.values(legacyDtoImportAllowlist).flat().sort())
})

test('developer guide documents frontend legacy dto boundary groups', () => {
  const developerGuide = readRepoFile('docs/DEVELOPER_GUIDE.md')

  for (const [groupName, files] of Object.entries(legacyDtoImportAllowlist)) {
    assert.match(developerGuide, new RegExp(`\\b${groupName}\\b`))
    for (const file of files) {
      assert.match(developerGuide, new RegExp(escapeRegExp(file)))
    }
  }
})
