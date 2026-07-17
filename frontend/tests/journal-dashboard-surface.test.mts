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

const activeDashboardSources = [
  'app/(product)/dashboard/page.tsx',
  'hooks/useDashboardData.ts',
  'lib/adapters/dashboard.ts',
  'components/dashboard/PositionCard.tsx',
  'components/dashboard/workbench/DashboardWorkbench.tsx',
  'components/dashboard/workbench/DashboardWorkbenchHeader.tsx',
  'components/dashboard/workbench/DashboardRealizedPnlHero.tsx',
  'components/dashboard/workbench/DashboardJournalGrid.tsx',
  'components/dashboard/workbench/DashboardEvidenceStack.tsx',
].map(readSource).join('\n')

test('active dashboard surface is limited to journal-safe data', () => {
  assert.doesNotMatch(activeDashboardSources, /MarketStatus|RiskAlert|risk_summary|sharpe_ratio|sortino_ratio|calmar_ratio|max_drawdown/)
  assert.doesNotMatch(activeDashboardSources, /core_type_allocation|market_allocation|risk_level_allocation|top_movers|bottom_movers|portfolio_flow/)
  assert.doesNotMatch(activeDashboardSources, /current_price|unrealized_pnl|total_equity|allPositions|MaeMfe|PortfolioSankey/)
  assert.doesNotMatch(activeDashboardSources, /AI_INSIGHTS|\/insights|周度摘要|净值|账户分布/)

  assert.match(activeDashboardSources, /累计已实现盈亏/)
  assert.match(activeDashboardSources, /已实现收益参考/)
  assert.match(activeDashboardSources, /各账户日志余额/)
  assert.match(activeDashboardSources, /持仓日志/)
})

test('dashboard data hook requests only stats, realized history, and open positions', () => {
  const hook = readSource('hooks/useDashboardData.ts')

  assert.match(hook, /dashboardAPI\.stats/)
  assert.match(hook, /dashboardAPI\.pnlHistory/)
  assert.match(hook, /positionsAPI\.list\(token, \{ status: 'OPEN' \}\)/)
  assert.doesNotMatch(hook, /positionsAPI\.list\(token\)\s*$/m)
})

test('open-position cards do not coerce unavailable valuation fields to zero', () => {
  const card = readSource('components/dashboard/PositionCard.tsx')

  assert.doesNotMatch(card, /current_price|unrealized_pnl|realized_pnl/)
  assert.doesNotMatch(card, /average_entry_price\s*\|\|\s*0/)
  assert.match(card, /average_entry_price === undefined \|\| position\.average_entry_price === null/)
  assert.match(card, /建仓均价/)
  assert.match(card, /当前数量/)
})

test('dashboard period controls expose every option without mobile horizontal scrolling', () => {
  const hero = readSource('components/dashboard/workbench/DashboardRealizedPnlHero.tsx')

  assert.match(hero, /grid w-full grid-cols-4/)
  assert.match(hero, /min-w-0 rounded-md px-2/)
  assert.match(hero, /md:flex md:w-auto/)
})
