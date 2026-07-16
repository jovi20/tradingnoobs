import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(scriptDir, '..')
const contractPath = path.resolve(frontendRoot, '../backend/app_config/journal_beta_v1.json')
const outputPath = path.resolve(frontendRoot, 'lib/generated/release-contract.ts')
const contract = JSON.parse(await readFile(contractPath, 'utf8'))

const capabilityIds = contract.capabilities.default_disabled
const runtimeNames = {
    BROKER_SYNC: 'BROKER_SYNC_RUNTIME_ENABLED',
    MARKET: 'MARKET_RUNTIME_ENABLED',
    AI_INSIGHTS: 'AI_INSIGHTS_RUNTIME_ENABLED',
    PDF_EXPORT: 'PDF_EXPORT_RUNTIME_ENABLED',
    RISK_CARDS: 'RISK_CARDS_RUNTIME_ENABLED',
    OPEN_REGISTRATION: 'OPEN_REGISTRATION_RUNTIME_ENABLED',
}
const runtimeNameIds = Object.keys(runtimeNames)
if (
    runtimeNameIds.length !== capabilityIds.length
    || runtimeNameIds.some((capability) => !capabilityIds.includes(capability))
) {
    throw new Error('Optional capability IDs and frontend runtime constant names must match exactly.')
}

const serializedContract = JSON.stringify(contract, null, 4)

const lines = [
    '// Generated from backend/app_config/journal_beta_v1.json. Do not edit.',
    `export const JOURNAL_BETA_RELEASE_CONTRACT = ${serializedContract} as const`,
    `export const RELEASE_CONTRACT_ID = ${JSON.stringify(contract.metadata.contract_id)} as const`,
    `export const RELEASE_BASE_CURRENCY = ${JSON.stringify(contract.currency.deployment_base_currency)} as const`,
    `export const RELEASE_POSITION_MODE = ${JSON.stringify(contract.lifecycle.position_mode)} as const`,
    `export const RELEASE_ASSET_TYPES = ${JSON.stringify(contract.instruments.asset_types)} as const`,
    `export const RELEASE_INSTRUMENT_TYPES = ${JSON.stringify(contract.instruments.instrument_types)} as const`,
    `export const RELEASE_IMPORT_ADAPTERS = ${JSON.stringify(contract.imports.adapter_allowlist)} as const`,
    `export const OPTIONAL_CAPABILITY_IDS = ${JSON.stringify(capabilityIds)} as const`,
    ...capabilityIds.map((capability) => `export const ${runtimeNames[capability]} = false as const`),
    '',
]
const expected = `${lines.join('\n')}`

if (process.argv.includes('--check')) {
    const current = await readFile(outputPath, 'utf8').catch(() => '')
    if (current !== expected) {
        console.error('Generated release contract is stale. Run npm run generate:release-contract.')
        process.exitCode = 1
    }
} else {
    await writeFile(outputPath, expected)
}
