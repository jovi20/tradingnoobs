import test from 'node:test'
import assert from 'node:assert/strict'

import { adaptSettingsPageData, buildIntegrationCredentialUpdates, buildPlatformSettingUpdates } from '../lib/adapters/settings.ts'

test('adaptSettingsPageData maps new admin config sources into safe local state', () => {
  const result = adaptSettingsPageData({
    userSettings: {
      id: 1,
      user_id: 1,
      theme: 'system',
      up_color: 'GREEN',
      display_currency: 'USD',
      ibkr_host: '127.0.0.1',
      ibkr_port: 7497,
      ibkr_client_id: 1,
      binance_api_key: 'masked-user-key',
      llm_api_url: null,
      llm_model: null,
    },
    accounts: [
      {
        id: 12,
        public_id: 'acct-public',
        user_id: 1,
        name: 'IBKR',
        broker: 'IBKR',
        currency: 'USD',
        initial_balance: 1000,
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
    ],
    platformSettings: [
      { id: 1, key: 'llm_api_url', value: 'https://api.openai.com/v1', description: null, created_at: null, updated_at: null },
      { id: 2, key: 'llm_model', value: 'gpt-5', description: null, created_at: null, updated_at: null },
    ],
    integrationCredentials: [
      {
        id: 1,
        provider_key: 'finnhub',
        credential_key: 'api_key',
        masked_value: 'finn********1234',
        description: null,
        is_active: true,
        is_configured: true,
        created_at: null,
        updated_at: null,
      },
      {
        id: 2,
        provider_key: 'openai',
        credential_key: 'api_key',
        masked_value: 'sk-t********abcd',
        description: null,
        is_active: true,
        is_configured: true,
        created_at: null,
        updated_at: null,
      },
    ],
  })

  assert.equal(result.settings.llm_api_url_system, 'https://api.openai.com/v1')
  assert.equal(result.settings.llm_model_system, 'gpt-5')
  assert.equal(result.settings.finnhub_api_key_system, '')
  assert.equal(result.settings.llm_api_key_system, '')
  assert.equal(result.settings.finnhub_api_key_masked, 'finn********1234')
  assert.equal(result.settings.llm_api_key_masked, 'sk-t********abcd')
  assert.equal(result.accounts[0].routeId, 'acct-public')
})

test('settings update builders avoid overwriting secrets with masked placeholders', () => {
  const settings = {
    finnhub_api_key_system: '',
    finnhub_api_key_masked: 'finn********1234',
    llm_api_url_system: 'https://api.openai.com/v1',
    llm_api_key_system: 'sk-live-new-secret',
    llm_api_key_masked: 'sk-t********abcd',
    llm_model_system: 'gpt-5',
  }

  assert.deepEqual(buildPlatformSettingUpdates(settings), [
    { key: 'llm_api_url', value: 'https://api.openai.com/v1', description: 'LLM API Base URL' },
    { key: 'llm_model', value: 'gpt-5', description: 'LLM Model Name' },
  ])

  assert.deepEqual(buildIntegrationCredentialUpdates(settings), [
    {
      providerKey: 'openai',
      credentialKey: 'api_key',
      secret_value: 'sk-live-new-secret',
      description: 'OpenAI API Key',
      is_active: true,
    },
  ])
})
