/**
 * Trading Noobs Frontend - Display Formatters
 *
 * Shared number/currency formatting so the same value renders identically
 * everywhere. Prefer these over inlining `getCurrencySymbol(...)` next to a
 * `.toFixed(2)` call.
 */
import { getCurrencySymbol } from './symbolUtils'

type Numeric = number | string | null | undefined

/** Money with its currency symbol and 2 decimals, e.g. `$150.00`, `HK$8.20`. */
export function formatMoney(value: Numeric, currency?: string): string {
    return `${getCurrencySymbol(currency)}${Number(value ?? 0).toFixed(2)}`
}

/**
 * Quantity at asset-appropriate precision: crypto and FX trade in fractional
 * units (up to 6 dp), everything else in whole-ish share counts (up to 2 dp).
 */
export function formatQuantity(value: Numeric, assetType?: string): string {
    const qty = Number(value ?? 0)
    const maximumFractionDigits =
        assetType === 'CRYPTO' || assetType === 'FOREX' ? 6 : 2
    return qty.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits })
}
