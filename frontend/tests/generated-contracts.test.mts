import test from 'node:test'
import assert from 'node:assert/strict'

test('generated contract boundary module can be loaded', async () => {
  const generatedContracts = await import('../lib/generated/contracts.ts')

  assert.equal(typeof generatedContracts, 'object')
})
