import type { TradingAccount, UserSettings } from '../api.ts'
import { adaptTradingAccounts, type TradingAccountViewModel } from './trading.ts'

export interface SettingsPageState extends Partial<UserSettings> {
    ibkr_flex_token_masked?: string | null
    ibkr_flex_token?: string
    binance_api_key_masked?: string | null
    binance_api_secret?: string
    binance_api_secret_configured?: boolean
    binance_symbols_text?: string
}

interface AdaptSettingsPageDataInput {
    userSettings: UserSettings
    accounts: TradingAccount[]
}

export function adaptSettingsPageData({
    userSettings,
    accounts,
}: AdaptSettingsPageDataInput): {
    settings: SettingsPageState
    accounts: TradingAccountViewModel[]
} {
    return {
        settings: {
            ...userSettings,
            ibkr_flex_token: '',
            ibkr_flex_token_masked: userSettings.ibkr_flex_token || null,
            binance_api_key: '',
            binance_api_key_masked: userSettings.binance_api_key || null,
            binance_api_secret: '',
            binance_api_secret_configured: userSettings.binance_api_secret_configured || false,
            binance_market_type: userSettings.binance_market_type || 'SPOT',
            binance_symbols: userSettings.binance_symbols || [],
            binance_symbols_text: (userSettings.binance_symbols || []).join(', '),
        },
        accounts: adaptTradingAccounts(accounts),
    }
}
