import type { TradingAccount, UserSettings } from '../api.ts'
import { adaptTradingAccounts, type TradingAccountViewModel } from './trading.ts'

export type SettingsPageState = Partial<Pick<UserSettings, 'theme' | 'up_color' | 'display_currency'>>

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
            theme: userSettings.theme,
            up_color: userSettings.up_color,
            display_currency: 'USD',
        },
        accounts: adaptTradingAccounts(accounts),
    }
}
