import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'

import {
    AI_INSIGHTS_RUNTIME_ENABLED,
    BROKER_SYNC_RUNTIME_ENABLED,
    JOURNAL_BETA_RELEASE_CONTRACT,
    MARKET_RUNTIME_ENABLED,
    OPTIONAL_CAPABILITY_IDS,
    OPEN_REGISTRATION_RUNTIME_ENABLED,
    PDF_EXPORT_RUNTIME_ENABLED,
    RELEASE_ASSET_TYPES,
    RELEASE_BASE_CURRENCY,
    RELEASE_CONTRACT_ID,
    RELEASE_IMPORT_ADAPTERS,
    RELEASE_INSTRUMENT_TYPES,
    RELEASE_POSITION_MODE,
    RISK_CARDS_RUNTIME_ENABLED,
} from '../lib/generated/release-contract.ts'

const contractPath = path.resolve(process.cwd(), '../backend/app_config/journal_beta_v1.json')

test('generated frontend release constants match the machine contract', async () => {
    const contract = JSON.parse(await readFile(contractPath, 'utf8'))

    assert.equal(RELEASE_CONTRACT_ID, contract.metadata.contract_id)
    assert.deepEqual(JOURNAL_BETA_RELEASE_CONTRACT, contract)
    assert.equal(RELEASE_BASE_CURRENCY, contract.currency.deployment_base_currency)
    assert.equal(RELEASE_POSITION_MODE, contract.lifecycle.position_mode)
    assert.deepEqual(RELEASE_ASSET_TYPES, contract.instruments.asset_types)
    assert.deepEqual(RELEASE_INSTRUMENT_TYPES, contract.instruments.instrument_types)
    assert.deepEqual(RELEASE_IMPORT_ADAPTERS, contract.imports.adapter_allowlist)
    assert.deepEqual(OPTIONAL_CAPABILITY_IDS, contract.capabilities.default_disabled)
    assert.deepEqual(contract.currency.account_base_currencies, ['USD'])
    assert.deepEqual(contract.currency.stablecoin_aliases, {})
})

test('the journal Beta frontend artifact keeps every optional capability disabled by default', () => {
    assert.equal(BROKER_SYNC_RUNTIME_ENABLED, false)
    assert.equal(MARKET_RUNTIME_ENABLED, false)
    assert.equal(AI_INSIGHTS_RUNTIME_ENABLED, false)
    assert.equal(PDF_EXPORT_RUNTIME_ENABLED, false)
    assert.equal(RISK_CARDS_RUNTIME_ENABLED, false)
    assert.equal(OPEN_REGISTRATION_RUNTIME_ENABLED, false)
})
