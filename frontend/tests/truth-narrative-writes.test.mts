import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readFrontendFile(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('position detail saves ordinary narrative edits through truth event API', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/page.tsx')

  assert.match(source, /updateTradingPositionEventNarrative/)
  assert.match(source, /getLifecycleNarrativeDraft/)
  assert.doesNotMatch(source, /positionsAPI\.update\([^)]*trade_review/s)
})

test('truth narrative UI explains the canonical review location', () => {
  const actionPanel = readFrontendFile('components/positions/lifecycle/LifecycleActionPanel.tsx')
  const narrativeModal = readFrontendFile('components/positions/lifecycle/LifecycleModals.tsx')
  const migrationPanel = readFrontendFile('components/positions/lifecycle/LifecycleMigrationPanel.tsx')

  assert.match(actionPanel, /持仓事件（PositionEvent）是复盘叙事的权威来源/)
  assert.match(narrativeModal, /更新持仓事件的叙事字段/)
  assert.match(migrationPanel, /权威复盘叙事记录在审计事件中/)
})

test('truth lifecycle modals render outside the legacy-only detail branch', () => {
  const source = readFrontendFile('app/(product)/positions/[id]/page.tsx')

  assert.match(
    source,
    /<\/>\s*\)\}\s*<LifecycleModals/,
    'LifecycleModals must remain available when truthLifecycle is active',
  )
})
