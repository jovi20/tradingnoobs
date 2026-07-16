export interface AccountMetadataForm {
    name: string
    broker: string
    account_type: string
    currency: string
    description: string
}

export interface AccountMetadataUpdate {
    name: string
    broker: string
    account_type: string
    currency: string
    description: string
}

/** Keep ledger-managed values out of ordinary account profile updates. */
export function buildAccountMetadataUpdate(form: AccountMetadataForm): AccountMetadataUpdate {
    return {
        name: form.name,
        broker: form.broker,
        account_type: form.account_type,
        currency: form.currency,
        description: form.description,
    }
}
