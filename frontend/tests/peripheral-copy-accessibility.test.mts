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

test('date and theme icon controls expose localized accessible names', () => {
  const dateTimePicker = readSource('components/DateTimePicker.tsx')
  const themeToggle = readSource('components/ThemeToggle.tsx')

  assert.match(dateTimePicker, /aria-label="上一个月"/)
  assert.match(dateTimePicker, /aria-label="下一个月"/)
  assert.match(dateTimePicker, /aria-haspopup="dialog"/)
  assert.match(dateTimePicker, /aria-label=\{format\(day, 'yyyy年M月d日 EEEE'/)
  assert.match(themeToggle, /title=\{`当前主题：\$\{themeLabel\}`\}/)
  assert.match(themeToggle, /aria-label=\{`切换主题，当前为\$\{themeLabel\}`\}/)
})

test('chart renderers expose Chinese chart names', () => {
  const expectedLabels = new Map([
    ['components/charts/renderers/SvgLineChart.tsx', '折线图'],
    ['components/charts/renderers/SvgPieChart.tsx', '资产配置饼图'],
    ['components/charts/renderers/SvgSankeyChart.tsx', '组合资金流向桑基图'],
  ])

  for (const [file, label] of expectedLabels) {
    assert.match(readSource(file), new RegExp(`aria-label="${label}"`))
  }

  assert.doesNotMatch(readSource('components/charts/renderers/SvgPieChart.tsx'), />\s*Total\s*</)
})
