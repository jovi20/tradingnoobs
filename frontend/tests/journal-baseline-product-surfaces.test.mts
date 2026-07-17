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

test('settings and operations expose only journal baseline controls', () => {
  const settings = readSource('app/(product)/settings/page.tsx')
  const settingsAdapter = readSource('lib/adapters/settings.ts')
  const admin = readSource('app/(admin)/admin/ops/page.tsx')
  const transactionForm = readSource('components/TransactionForm.tsx')
  const api = readSource('lib/api.ts')

  assert.doesNotMatch(settings, /brokerSyncAPI|BROKER_SYNC_RUNTIME_ENABLED|ibkr_flex|binance_api|Flex Token|API Secret/)
  assert.doesNotMatch(settingsAdapter, /ibkr|binance|secret|\.\.\.userSettings/)
  assert.doesNotMatch(settings, /Margin|Unified|HKD|CNY|EUR|GBP/)
  assert.match(settings, /\{ value: 'Spot', label: '现金账户' \}/)
  assert.match(settings, /\{ value: 'USD', label: 'USD - 美元' \}/)

  assert.doesNotMatch(admin, /LLM|OpenAI|Finnhub|testLLM|IntegrationCredential/)
  assert.doesNotMatch(admin, /listIntegrationCredentials|upsertIntegrationCredential|updateIntegrationCredentialActive/)
  assert.match(admin, /存在失败任务/)

  assert.doesNotMatch(transactionForm, /TRANSFER_IN|TRANSFER_OUT/)
  assert.match(api, /JournalTransactionCreateType = 'DEPOSIT' \| 'WITHDRAWAL' \| 'INTEREST' \| 'FEE'/)
})

test('daily and trade-entry surfaces do not imply market data availability', () => {
  const daily = readSource('app/(product)/daily/page.tsx')
  const newPosition = readSource('app/(product)/positions/new/page.tsx')
  const addBatch = readSource('app/(product)/positions/[id]/add-batch/page.tsx')

  assert.doesNotMatch(daily, /marketAPI|MarketCalendar|MarketHoliday|buildLocalMarketCalendar/)
  assert.doesNotMatch(daily, /节假日|休市|isTradingDay|isHoliday/)
  assert.doesNotMatch(newPosition, /marketAPI|validateSymbol|SymbolValidation|detectSymbolType/)
  assert.doesNotMatch(addBatch, /marketAPI|validateSymbol|SymbolValidation|marketQuote/)
  assert.match(newPosition, /\{ value: 'STOCK', label:/)
  assert.match(newPosition, /\{ value: 'FUND', label:/)
  assert.match(newPosition, /\{ value: 'CRYPTO', label:/)
  assert.match(newPosition, /value="SPOT"/)
  assert.match(newPosition, /value="USD"/)
})

test('account and lifecycle surfaces avoid unsupported valuation claims', () => {
  const account = readSource('app/(product)/settings/accounts/[id]/page.tsx')
  const accountOverview = readSource('components/settings/domain/SettingsAccountsOverview.tsx')
  const position = readSource('app/(product)/positions/[id]/page.tsx')
  const migrationPanel = readSource('components/positions/lifecycle/LifecycleMigrationPanel.tsx')
  const workbench = readSource('components/positions/lifecycle/LifecycleWorkbench.tsx')
  const actionPanel = readSource('components/positions/lifecycle/LifecycleActionPanel.tsx')
  const lifecycleModals = readSource('components/positions/lifecycle/LifecycleModals.tsx')
  const lifecycleAdapter = readSource('lib/adapters/lifecycle.ts')
  const api = readSource('lib/api.ts')

  assert.match(account, /日志余额/)
  assert.doesNotMatch(account, /可用现金|持仓市值|账户净值|market_value|total_equity/)
  assert.doesNotMatch(account, /Margin|Unified/)
  assert.match(accountOverview, /日志余额/)
  assert.doesNotMatch(accountOverview, /账户净值|市值|现金|market_value|total_equity/)

  for (const source of [position, migrationPanel]) {
    assert.doesNotMatch(source, /current_price|unrealized_pnl|风险评级|getRiskLevelInfo/)
    assert.doesNotMatch(source, /handleAnalyze|onAnalyze|isAnalyzing|分析历史价格/)
    assert.doesNotMatch(source, /max_price_during_hold|min_price_during_hold|editingExtremes|onEditExtremes|MAE\/MFE/)
  }
  assert.doesNotMatch(position, /metadataForm|editingMetadata|handleUpdateMetadata|编辑行业板块/)
  assert.doesNotMatch(migrationPanel, /onEditMetadata|编辑旧版资产属性/)
  assert.doesNotMatch(position, /ALL_ASSET_CORE_TYPES|ALL_ASSET_MARKETS|现货、ETF、期货/)
  assert.doesNotMatch(workbench, /onAnalyze|isAnalyzing/)
  for (const source of [position, workbench, actionPanel, lifecycleModals, lifecycleAdapter, api]) {
    assert.doesNotMatch(source, /createTradingPositionManualAdjustment|onManualAdjustment|cashAdjustment|editingManualAdjustment|\/adjustments/)
  }
  assert.doesNotMatch(`${actionPanel}\n${lifecycleModals}`, /记录现金调整|现金调整流水|MANUAL_ADJUSTMENT|CASH_ADJUSTMENT/)
  assert.match(position, /计划止损/)
  assert.match(position, /计划执行对比/)
  assert.match(migrationPanel, /执行偏移/)
})

test('positions list exposes journal facts and realized PnL without risk or valuation fields', () => {
  const positions = readSource('app/(product)/positions/page.tsx')
  const positionsData = readSource('hooks/usePositionsData.ts')
  const activeSources = `${positions}\n${positionsData}`

  assert.doesNotMatch(activeSources, /\bRISK\b|risk_level|getRiskLevelInfo|AssetRiskLevel|ALL_ASSET_RISK_LEVELS/)
  assert.doesNotMatch(positions, /current_price|unrealized_pnl|持仓盈亏|现价/)
  assert.match(positions, /已实现盈亏/)
  assert.match(positions, /旧版批次记录/)
  assert.match(positions, /aria-label=\{`\$\{expandedId === position\.id \? '收起' : '展开'/)
})

test('timeline and lifecycle workbenches hard-off optional AI and estimated equity', () => {
  const timelinePage = readSource('app/(product)/timeline/page.tsx')
  const timelineWorkbench = readSource('components/timeline/workbench/TimelineWorkbench.tsx')
  const decisionRail = readSource('components/timeline/workbench/TimelineDecisionRail.tsx')
  const viewTabs = readSource('components/timeline/workbench/TimelineViewTabs.tsx')
  const zeroState = readSource('components/timeline/TimelineZeroState.tsx')
  const feedPanel = readSource('components/timeline/workbench/TimelineFeedPanel.tsx')
  const eventCard = readSource('components/timeline/workbench/TimelineEventCardV2.tsx')
  const contextRail = readSource('components/timeline/TimelineContextRail.tsx')
  const timelineAdapter = readSource('lib/adapters/timeline-workbench.ts')
  const timelineDataAdapter = readSource('lib/adapters/timeline.ts')
  const lifecycleWorkbench = readSource('components/positions/lifecycle/LifecycleWorkbench.tsx')
  const activeWorkbenches = [timelinePage, timelineWorkbench, decisionRail, lifecycleWorkbench].join('\n')
  const visibleTimelineSources = [timelinePage, timelineWorkbench, decisionRail, viewTabs, zeroState, feedPanel, eventCard].join('\n')

  assert.doesNotMatch(activeWorkbenches, /useInsightRuns|EvidenceLinkedInsightSidecar|LifecycleAiSidecarPanel|InsightRun|insightRuns|onRefreshInsights/)
  assert.doesNotMatch(visibleTimelineSources, /AI 洞察|AI 证据|AI 分析|ai_annotation|Sparkles/)
  assert.doesNotMatch(timelinePage, /检查同步设置/)
  assert.doesNotMatch(timelineDataAdapter, /检查同步(?:设置|配置)/)
  assert.doesNotMatch(viewTabs, /value: 'AI'/)
  assert.match(feedPanel, /event\.event_type !== 'AI_INSIGHT'/)
  assert.match(contextRail, /filter\(\(filter\) => filter\.key !== 'AI'\)/)
  assert.match(contextRail, /object_type === 'INSIGHT_ARTIFACT'/)
  assert.match(contextRail, /href\.startsWith\('\/insights'\)/)
  assert.doesNotMatch(timelineAdapter, /net_equity_change|equity_change|净值变化/)
  assert.match(timelineWorkbench, /md:grid-cols-3/)
  assert.match(lifecycleWorkbench, /LifecycleMigrationPanel/)
})
