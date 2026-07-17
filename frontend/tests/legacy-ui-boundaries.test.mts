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
    'app/(product)/positions/[id]/add-batch/page.tsx',
    'app/(product)/positions/page.tsx',
  ],
  create_sync_bridge: [
    'app/(product)/positions/new/page.tsx',
  ],
  legacy_analytics: [
    'components/dashboard/MaeMfeScatterPlot.tsx',
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
  const source = readFrontendFile('app/(product)/positions/page.tsx')

  assert.match(source, /旧版批次记录/)
  assert.match(source, /仅供迁移和排查使用/)
  assert.match(source, /记录加仓/)
  assert.match(source, /记录减仓或平仓/)
})

test('add-batch page exposes truth writes without a legacy migration fallback', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/add-batch/page.tsx')

  assert.match(source, /审计事件写入/)
  assert.match(source, /权威审计生命周期/)
  assert.match(source, /旧版批次写入已从产品入口关闭/)
  assert.doesNotMatch(source, /migrationFallback|X-Migration-Fallback|positionsAPI\.addBatch/)
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
