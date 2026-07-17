import { readFile, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const frontendRoot = path.resolve(scriptDir, '..')
const contractPath = path.resolve(frontendRoot, '../backend/app_config/journal_beta_v1.json')
const outputPath = path.resolve(frontendRoot, 'lib/generated/release-contract.ts')
const contract = JSON.parse(await readFile(contractPath, 'utf8'))

const capabilityIds = contract.capabilities.default_disabled
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
