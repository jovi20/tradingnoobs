import test from 'node:test'
import assert from 'node:assert/strict'

import { adaptSettingsPageData } from '../lib/adapters/settings.ts'

test('adaptSettingsPageData exposes only journal appearance settings', () => {
  const result = adaptSettingsPageData({
    userSettings: {
      id: 1,
      user_id: 1,
      theme: 'system',
      up_color: 'GREEN',
      display_currency: 'USD',
      ibkr_flex_query_id: '123456',
      ibkr_flex_token: 'masked-flex-token',
      ibkr_flex_start_date: '2024-01-01',
      binance_api_key: 'masked-user-key',
      binance_api_secret: null,
      binance_api_secret_configured: true,
      binance_market_type: 'SPOT',
      binance_symbols: ['BTCUSDT', 'ETHUSDT'],
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
  })

  assert.deepEqual(result.settings, {
    theme: 'system',
    up_color: 'GREEN',
    display_currency: 'USD',
  })
  assert.equal(result.accounts[0].routeId, 'acct-public')
})
