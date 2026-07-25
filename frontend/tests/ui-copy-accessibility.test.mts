import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readSource(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('desktop sidebar renders a separated administrator operations section', () => {
  const source = readSource('components/navigation/AppSidebar.tsx')

  assert.match(source, /const opsItems = items\.filter/)
  assert.match(source, /opsItems\.map/)
  assert.match(source, />管理</)
})

test('confirmed icon-only controls expose accessible names', () => {
  const topBar = readSource('components/navigation/AppTopBar.tsx')
  const strategies = readSource('app/(product)/strategies/page.tsx')
  const daily = readSource('app/(product)/daily/page.tsx')
  const insightSidecar = readSource('components/insights/EvidenceLinkedInsightSidecar.tsx')
  const positions = readSource('app/(product)/positions/page.tsx')
  const positionDetail = readSource('app/(product)/positions/[id]/page.tsx')
  const addBatch = readSource('app/(product)/positions/[id]/add-batch/page.tsx')
  const newPosition = readSource('app/(product)/positions/new/page.tsx')
  const lifecycleModals = readSource('components/positions/lifecycle/LifecycleModals.tsx')
  const adminShell = readSource('components/navigation/AdminShell.tsx')

  assert.match(topBar, /aria-label="搜索和快速跳转"/)
  assert.match(topBar, /aria-label=\{user\?\.email/)
  assert.match(strategies, /aria-label=\{`编辑策略：\$\{strategy\.name\}`\}/)
  assert.match(strategies, /aria-label=\{`删除策略：\$\{strategy\.name\}`\}/)
  assert.match(daily, /aria-label="上一个月"/)
  assert.match(daily, /aria-label="下一个月"/)
  assert.match(insightSidecar, /aria-label=\{`刷新\$\{title\}`\}/)
  assert.match(positions, /aria-label=\{`\$\{expandedId === position\.id \? '收起' : '展开'\}/)
  assert.match(positionDetail, /aria-label="返回交易记录"/)
  assert.match(positionDetail, /aria-label="关闭修改交易记录对话框"/)
  assert.doesNotMatch(positionDetail, /编辑行业板块/)
  assert.match(addBatch, /aria-label="返回持仓详情"/)
  assert.match(newPosition, /aria-label="返回交易记录"/)
  assert.match(lifecycleModals, /aria-label="关闭交易叙事编辑"/)
  assert.match(adminShell, /aria-label="返回产品"/)
  assert.match(adminShell, /aria-label=\{item\.label\}/)
})

test('new-position identity and direction controls expose programmatic semantics', () => {
  const source = readSource('app/(product)/positions/new/page.tsx')

  for (const id of [
    'position-symbol',
    'position-exchange-code',
    'position-entry-price',
    'position-quantity'
  ]) {
    assert.match(source, new RegExp(`htmlFor="${id}"`))
    assert.match(source, new RegExp(`id="${id}"`))
  }
  assert.match(source, /role="group" aria-labelledby="position-direction-label"/)
  assert.match(source, /aria-pressed=\{form\.direction === 'LONG'\}/)
  assert.match(source, /aria-pressed=\{form\.direction === 'SHORT'\}/)
})

test('auth errors are announced and primary product headings do not mix English labels', () => {
  const login = readSource('app/(auth)/login/page.tsx')
  const sidebar = readSource('components/navigation/AppSidebar.tsx')
  const timeline = readSource('components/timeline/workbench/ReviewInboxPanel.tsx')
  const dashboard = readSource('components/dashboard/workbench/DashboardWorkbenchHeader.tsx')
  const insights = readSource('app/(product)/insights/InsightsPageClient.tsx')
  const admin = readSource('app/(admin)/admin/ops/page.tsx')
  const importPage = readSource('app/(product)/positions/import/page.tsx')
  const importTable = readSource('components/import/ImportPreviewTable.tsx')

  assert.match(login, /role="alert"/)
  assert.doesNotMatch(sidebar, />Decision Journal</)
  assert.doesNotMatch(timeline, /eyebrow="Review Inbox"/)
  assert.doesNotMatch(dashboard, /eyebrow="Macro Command Center"/)
  assert.doesNotMatch(insights, /title="Auditable Insight Artifacts"/)
  assert.doesNotMatch(admin, />\s*Admin Ops\s*</)
  assert.doesNotMatch(importPage, />\s*Preview\s*</)
  assert.doesNotMatch(importTable, />\s*Identity\s*</)
  assert.doesNotMatch(importTable, /\{err\.message\}|\{warning\.message\}/)
  assert.match(importTable, /LONG: '多头'/)
  assert.match(importTable, /aria-label="选择全部有效行"/)
  assert.match(importTable, /aria-label=\{`选择第 \$\{row\.row_number\} 行`\}/)
  assert.match(importPage, /positionsAPI\.confirmImport/)
  assert.match(importPage, /'确认导入'/)
})

test('settings presents Chinese labels while retaining technical identifiers as metadata', () => {
  const settings = readSource('app/(product)/settings/page.tsx')
  const accounts = readSource('components/settings/domain/SettingsAccountsOverview.tsx')

  assert.doesNotMatch(settings, />\s*Settings\s*</)
  assert.doesNotMatch(settings, /'(?:Unknown|Admin|User|Active|Inactive|None)'/)
  assert.doesNotMatch(settings, /\$\{activeAccountCount\} active|\$\{completionItems[^\n]+ ready/)
  assert.doesNotMatch(accounts, /\} accounts|\} active|'(?:Active|Inactive|None|General)'|label="NAV"/)
  assert.match(settings, /aria-label="关闭添加账户对话框"/)
  assert.match(settings, /getLocalizedUiError\(err,/)
})

test('administrator workbench grid can shrink to a mobile viewport', () => {
  const admin = readSource('app/(admin)/admin/ops/page.tsx')

  assert.match(admin, /grid-cols-\[minmax\(0,1fr\)\]/)
  assert.match(admin, /<div className="min-w-0 space-y-5">/)
  assert.match(admin, /<div className="min-w-0 rounded-lg border border-line bg-panel/)
})

test('mobile product navigation fits every visible item without horizontal scrolling', () => {
  const source = readSource('components/navigation/MobileBottomNav.tsx')

  assert.match(source, /gridTemplateColumns: `repeat\(\$\{Math\.max\(visible\.length, 1\)\}, minmax\(0, 1fr\)\)`/)
  assert.match(source, /flex min-w-0 flex-col/)
  assert.doesNotMatch(source, /overflow-x-auto|min-w-\[4\.25rem\]/)
})
