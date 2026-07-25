import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { buildAccountMetadataUpdate } from '../lib/accountUpdates.ts'

const testDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(testDir, '..')

test('account metadata payload excludes ledger-managed balances', () => {
    const contaminatedForm = {
        name: '主账户',
        broker: 'IBKR',
        account_type: 'Margin',
        currency: 'USD',
        description: '长期投资',
        initial_balance: 10_000,
        cash_balance: 0,
        current_balance: 0,
        total_assets: 0,
        total_liabilities: 0,
    }

    assert.deepEqual(buildAccountMetadataUpdate(contaminatedForm), {
        name: '主账户',
        broker: 'IBKR',
        account_type: 'Margin',
        currency: 'USD',
        description: '长期投资',
    })
})

test('account detail save always uses the metadata payload builder', () => {
    const source = readFileSync(
        resolve(frontendRoot, 'app/(product)/settings/accounts/[id]/page.tsx'),
        'utf8'
    )

    assert.match(source, /accountsAPI\.update\([\s\S]*?buildAccountMetadataUpdate\(form\)[\s\S]*?\)/)
    assert.doesNotMatch(
        source,
        /accountsAPI\.update\(\s*token,\s*account\.routeId,\s*form\s*\)/
    )
    assert.doesNotMatch(
        source,
        /\b(?:initial_balance|cash_balance|current_balance|total_assets|total_liabilities)\s*:/
    )
})

test('account transaction controls use consistent Chinese copy', () => {
    const formSource = readFileSync(resolve(frontendRoot, 'components/TransactionForm.tsx'), 'utf8')
    const listSource = readFileSync(resolve(frontendRoot, 'components/TransactionList.tsx'), 'utf8')

    assert.doesNotMatch(formSource, /\((?:Deposit|Withdrawal|Interest|Fee|Transfer In|Transfer Out)\)/)
    assert.doesNotMatch(listSource, /No transactions found|deleteTransaction|删除流水/)
    assert.match(formSource, /<option value="DEPOSIT">入金<\/option>/)
    assert.match(formSource, /setFormData\(\(current\) => \(\{[\s\S]*?amount: 0,[\s\S]*?description: ''/)
    assert.match(listSource, /aria-label=\{`冲正\$\{getTypeLabel\(tx\.type\)\}流水`\}/)
    assert.match(listSource, /accountsAPI\.reverseTransaction/)
})
