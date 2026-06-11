import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'

const SCAN_ROOTS = ['app', 'components', 'lib']
const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.mts', '.cts'])
const ALLOWED_RECHARTS_IMPORTS = new Set([
  'components/PortfolioSankey.tsx',
  'components/insights/LegacyAnalysisChart.tsx',
  'components/dashboard/MaeMfeScatterPlot.tsx',
  'components/dashboard/AllocationPieChart.tsx',
  'components/dashboard/workbench/DashboardEquityHero.tsx',
])

const RECHARTS_IMPORT_PATTERN = /from\s+['"]recharts(?:\/[^'"]*)?['"]|import\s*\(\s*['"]recharts(?:\/[^'"]*)?['"]\s*\)|require\s*\(\s*['"]recharts(?:\/[^'"]*)?['"]\s*\)/

function toPosixPath(value: string): string {
  return value.split(path.sep).join('/')
}

function collectSourceFiles(dir: string): string[] {
  const files: string[] = []
  for (const entry of readdirSync(dir)) {
    if (entry === 'node_modules' || entry.startsWith('.next')) continue
    const fullPath = path.join(dir, entry)
    const stat = statSync(fullPath)
    if (stat.isDirectory()) {
      files.push(...collectSourceFiles(fullPath))
    } else if (SOURCE_EXTENSIONS.has(path.extname(entry))) {
      files.push(fullPath)
    }
  }
  return files
}

test('new Recharts imports are blocked outside the P18 legacy allowlist', () => {
  const projectRoot = process.cwd()
  const sourceFiles = SCAN_ROOTS.flatMap((root) => collectSourceFiles(path.join(projectRoot, root)))
  const filesWithRechartsImports = sourceFiles
    .filter((filePath) => RECHARTS_IMPORT_PATTERN.test(readFileSync(filePath, 'utf8')))
    .map((filePath) => toPosixPath(path.relative(projectRoot, filePath)))
    .sort()

  const unexpectedImports = filesWithRechartsImports.filter((filePath) => !ALLOWED_RECHARTS_IMPORTS.has(filePath))
  assert.deepEqual(unexpectedImports, [])
  assert.deepEqual(filesWithRechartsImports, Array.from(ALLOWED_RECHARTS_IMPORTS).sort())
})
