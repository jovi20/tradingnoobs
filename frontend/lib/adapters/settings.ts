import type {
    IntegrationCredential,
    PlatformSetting,
    SystemSetting,
    TradingAccount,
    UserSettings,
} from '../api.ts'
import { adaptTradingAccounts, type TradingAccountViewModel } from './trading.ts'

export interface SettingsPageState extends Partial<UserSettings> {
    finnhub_api_key_system?: string
    finnhub_api_key_masked?: string | null
    llm_api_url_system?: string
    llm_api_key_system?: string
    llm_api_key_masked?: string | null
    llm_model_system?: string
    binance_api_secret?: string
}

interface AdaptSettingsPageDataInput {
    userSettings: UserSettings
    accounts: TradingAccount[]
    platformSettings?: PlatformSetting[]
    integrationCredentials?: IntegrationCredential[]
    legacySystemSettings?: SystemSetting[]
}

export function adaptSettingsPageData({
    userSettings,
    accounts,
    platformSettings = [],
    integrationCredentials = [],
    legacySystemSettings = [],
}: AdaptSettingsPageDataInput): {
    settings: SettingsPageState
    accounts: TradingAccountViewModel[]
} {
    const systemValues: Record<string, string> = {}
    for (const setting of legacySystemSettings) {
        systemValues[setting.key] = setting.value || ''
    }
    for (const setting of platformSettings) {
        systemValues[setting.key] = setting.value || ''
    }

    const findCredential = (providerKey: string, credentialKey: string) =>
        integrationCredentials.find(
            (credential) =>
                credential.provider_key === providerKey &&
                credential.credential_key === credentialKey
        )

    const finnhubCredential = findCredential('finnhub', 'api_key')
    const openAiCredential = findCredential('openai', 'api_key') || findCredential('llm', 'api_key')

    return {
        settings: {
            ...userSettings,
            binance_api_secret: '',
            finnhub_api_key_system: '',
            finnhub_api_key_masked: finnhubCredential?.masked_value || null,
            llm_api_url_system: systemValues['llm_api_url'] || '',
            llm_api_key_system: '',
            llm_api_key_masked: openAiCredential?.masked_value || null,
            llm_model_system: systemValues['llm_model'] || 'gpt-4',
        },
        accounts: adaptTradingAccounts(accounts),
    }
}

export function buildPlatformSettingUpdates(settings: SettingsPageState): Array<{
    key: string
    value: string
    description: string
}> {
    return [
        {
            key: 'llm_api_url',
            value: settings.llm_api_url_system || '',
            description: 'LLM API Base URL',
        },
        {
            key: 'llm_model',
            value: settings.llm_model_system || 'gpt-4',
            description: 'LLM Model Name',
        },
    ]
}

export function buildIntegrationCredentialUpdates(settings: SettingsPageState): Array<{
    providerKey: string
    credentialKey: string
    secret_value: string
    description: string
    is_active: boolean
}> {
    const updates = []

    if (settings.finnhub_api_key_system && settings.finnhub_api_key_system.trim()) {
        updates.push({
            providerKey: 'finnhub',
            credentialKey: 'api_key',
            secret_value: settings.finnhub_api_key_system,
            description: 'Finnhub API Key',
            is_active: true,
        })
    }

    if (settings.llm_api_key_system && settings.llm_api_key_system.trim()) {
        updates.push({
            providerKey: 'openai',
            credentialKey: 'api_key',
            secret_value: settings.llm_api_key_system,
            description: 'OpenAI API Key',
            is_active: true,
        })
    }

    return updates
}
