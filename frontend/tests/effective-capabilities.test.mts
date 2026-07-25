import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import test from 'node:test'
import { fileURLToPath } from 'node:url'

import {
  DISABLED_EFFECTIVE_CAPABILITIES,
  EFFECTIVE_CAPABILITY_IDS,
  isEffectiveCapabilityEnabled,
  normalizeEffectiveCapabilities,
} from '../lib/effective-capabilities.ts'
import { OPTIONAL_CAPABILITY_IDS } from '../lib/generated/release-contract.ts'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

function readSource(relativePath: string): string {
  return readFileSync(resolve(frontendRoot, relativePath), 'utf8')
}

test('missing or malformed effective snapshots fail closed for all six capabilities', () => {
  for (const input of [undefined, null, 'DEVELOPMENT_FULL', [], true]) {
    const capabilities = normalizeEffectiveCapabilities(input as never)
    assert.deepEqual(capabilities, DISABLED_EFFECTIVE_CAPABILITIES)
  }

  assert.deepEqual(EFFECTIVE_CAPABILITY_IDS, [
    'BROKER_SYNC',
    'MARKET',
    'AI_INSIGHTS',
    'PDF_EXPORT',
    'RISK_CARDS',
    'OPEN_REGISTRATION',
  ])
  assert.equal(EFFECTIVE_CAPABILITY_IDS, OPTIONAL_CAPABILITY_IDS)
})

test('only literal true values in an effective snapshot enable a capability', () => {
  const capabilities = normalizeEffectiveCapabilities({
    AI_INSIGHTS: true,
    PDF_EXPORT: false,
    MARKET: 'true',
    BROKER_SYNC: 1,
  })

  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'AI_INSIGHTS'), true)
  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'PDF_EXPORT'), false)
  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'MARKET'), false)
  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'BROKER_SYNC'), false)
  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'RISK_CARDS'), false)
  assert.equal(isEffectiveCapabilityEnabled(capabilities, 'OPEN_REGISTRATION'), false)

  const inherited = Object.create({ AI_INSIGHTS: true })
  assert.equal(normalizeEffectiveCapabilities(inherited).AI_INSIGHTS, false)
})

test('effective capability consumers do not derive permission from a release profile', () => {
  const model = readSource('lib/effective-capabilities.ts')
  const context = readSource('contexts/EffectiveCapabilitiesContext.tsx')

  assert.doesNotMatch(model, /DEVELOPMENT_FULL|RELEASE_PROFILE|RUNTIME_ENABLED|process\.env/)
  assert.doesNotMatch(context, /DEVELOPMENT_FULL|RELEASE_PROFILE|RUNTIME_ENABLED|process\.env/)
})

test('journal Beta does not include Insights route modules', () => {
  for (const relativePath of [
    'app/(product)/insights/page.tsx',
    'app/(product)/insights/[artifactId]/page.tsx',
  ]) {
    assert.equal(existsSync(resolve(frontendRoot, relativePath)), false)
  }

  assert.equal(existsSync(resolve(frontendRoot, 'app/(product)/insights/InsightsPageClient.tsx')), true)
  assert.equal(existsSync(resolve(frontendRoot, 'app/(product)/insights/[artifactId]/InsightArtifactDetailPageClient.tsx')), true)
})

test('optional UI entries are gated or absent from journal-only surfaces', () => {
  const commandPalette = readSource('components/navigation/CommandPalette.tsx')
  const dashboardHeader = readSource('components/dashboard/workbench/DashboardWorkbenchHeader.tsx')
  const insightsClient = readSource('app/(product)/insights/InsightsPageClient.tsx')

  assert.match(commandPalette, /requiredCapability: 'AI_INSIGHTS'/)
  assert.match(commandPalette, /isEffectiveCapabilityEnabled\(effectiveCapabilities, c\.requiredCapability\)/)
  assert.doesNotMatch(dashboardHeader, /AI_INSIGHTS|\/insights|useEffectiveCapabilities/)
  assert.match(insightsClient, /isEffectiveCapabilityEnabled\(effectiveCapabilities, 'PDF_EXPORT'\)/)
  assert.match(insightsClient, /\{canExportPdf && \(/)
})

test('invite registration is a baseline onboarding path independent of open registration', () => {
  const login = readSource('app/(auth)/login/page.tsx')
  const registerPath = resolve(frontendRoot, 'app/(auth)/register/page.tsx')
  const authContext = readSource('contexts/AuthContext.tsx')
  const api = readSource('lib/api.ts')

  assert.match(login, /\/register/)
  assert.equal(existsSync(registerPath), true)
  assert.match(authContext, /['"]\/register['"]/)
  assert.match(api, /register:\s*async|['"]\/auth\/register['"]/)
  const register = readSource('app/(auth)/register/page.tsx')
  assert.match(register, /invite_code/)
  assert.match(register, /timezone/)
})

test('legacy users must explicitly select a timezone before journal writes', () => {
  const settings = readSource('app/(product)/settings/page.tsx')

  assert.match(settings, /timezone:\s*user\?\.timezone\s*\|\|\s*['"]['"]/)
  assert.match(settings, /请选择时区/)
  assert.doesNotMatch(settings, /timezone:\s*profileForm\.timezone\s*\|\|\s*['"]Asia\/Shanghai['"]/)
})
