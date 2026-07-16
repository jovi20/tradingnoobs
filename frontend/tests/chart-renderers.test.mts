import test from 'node:test'
import assert from 'node:assert/strict'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import path from 'node:path'

import {
  buildLinePath,
  buildPieSlices,
  buildScatterPoints,
  normalizeSankeyLinks,
  scaleLinear,
} from '../components/charts/renderers/chartGeometry.ts'

const SCAN_ROOTS = ['app', 'components', 'lib']
const SOURCE_EXTENSIONS = new Set(['.js', '.jsx', '.ts', '.tsx', '.mts', '.cts'])
const ALLOWED_RECHARTS_IMPORTS = new Set<string>()

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

test('scaleLinear maps values across domains and protects flat domains', () => {
  const scale = scaleLinear(0, 10, 0, 100)
  assert.equal(scale(5), 50)

  const flatScale = scaleLinear(10, 10, 0, 100)
  assert.equal(flatScale(10), 50)
})

test('buildLinePath returns an SVG path starting with M', () => {
  const pathData = buildLinePath([
    { x: 0, y: 10 },
    { x: 5, y: 5 },
    { x: 10, y: 0 },
  ], 200, 100)

  assert.match(pathData, /^M/)
  assert.match(pathData, /L/)
})

test('buildPieSlices covers the full circle for positive values', () => {
  const slices = buildPieSlices([25, 25, 50], 80)
  const totalAngle = slices.reduce((sum, slice) => sum + (slice.endAngle - slice.startAngle), 0)

  assert.equal(slices.length, 3)
  assert.ok(Math.abs(totalAngle - Math.PI * 2) < 0.000001)
})

test('buildScatterPoints keeps points inside the viewport', () => {
  const points = buildScatterPoints([
    { x: -10, y: 20 },
    { x: 0, y: 0 },
    { x: 10, y: -20 },
  ], 300, 160)

  assert.equal(points.length, 3)
  for (const point of points) {
    assert.ok(point.cx >= 0 && point.cx <= 300)
    assert.ok(point.cy >= 0 && point.cy <= 160)
  }
})

test('normalizeSankeyLinks exposes empty state for missing links', () => {
  const normalized = normalizeSankeyLinks({ nodes: [{ name: 'Cash' }], links: [] })

  assert.equal(normalized.isEmpty, true)
  assert.equal(normalized.emptyReason, '暂无桑基图连接数据')
  assert.deepEqual(normalized.links, [])
})
