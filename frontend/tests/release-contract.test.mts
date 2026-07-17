import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'

import {
    JOURNAL_BETA_RELEASE_CONTRACT,
    OPTIONAL_CAPABILITY_IDS,
    RELEASE_ASSET_TYPES,
    RELEASE_BASE_CURRENCY,
    RELEASE_CONTRACT_ID,
    RELEASE_IMPORT_ADAPTERS,
    RELEASE_INSTRUMENT_TYPES,
    RELEASE_POSITION_MODE,
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
