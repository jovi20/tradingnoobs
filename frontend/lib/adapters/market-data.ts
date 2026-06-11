export type MarketFreshnessTone = 'positive' | 'neutral' | 'warning' | 'danger'

export interface MarketDataFreshnessMeta {
  provider?: string | null
  freshness?: string | null
  degraded?: boolean | null
  degraded_reason?: string | null
  source_refs?: string[] | null
}

export interface MarketDataStatusView {
  providerLabel: string
  freshnessLabel: string
  tone: MarketFreshnessTone
  degradedReason: string | null
  sourceRefs: string[]
}

const PROVIDER_LABELS: Record<string, string> = {
  akshare: 'AKShare',
  binance: 'Binance',
  finnhub: 'Finnhub',
  yfinance: 'YFinance',
}

const FRESHNESS_LABELS: Record<string, string> = {
  FRESH: '实时',
  CACHED: '缓存',
  DELAYED: '延迟',
  STALE: '过期',
  DEGRADED: '降级',
  UNAVAILABLE: '不可用',
}

export function getMarketProviderLabel(provider?: string | null): string {
  if (!provider) return '自动路由'
  return PROVIDER_LABELS[provider.toLowerCase()] || provider
}

export function getMarketFreshnessLabel(freshness?: string | null): string {
  if (!freshness) return '未知'
  return FRESHNESS_LABELS[freshness.toUpperCase()] || '未知'
}

export function getMarketFreshnessTone(meta: Pick<MarketDataFreshnessMeta, 'freshness' | 'degraded'>): MarketFreshnessTone {
  if (meta.degraded) {
    return meta.freshness === 'UNAVAILABLE' ? 'danger' : 'warning'
  }
  switch ((meta.freshness || '').toUpperCase()) {
    case 'FRESH':
      return 'positive'
    case 'CACHED':
      return 'neutral'
    case 'DELAYED':
    case 'STALE':
    case 'DEGRADED':
      return 'warning'
    case 'UNAVAILABLE':
      return 'danger'
    default:
      return 'neutral'
  }
}

export function buildMarketDataStatus(meta: MarketDataFreshnessMeta): MarketDataStatusView {
  return {
    providerLabel: getMarketProviderLabel(meta.provider),
    freshnessLabel: getMarketFreshnessLabel(meta.freshness),
    tone: getMarketFreshnessTone(meta),
    degradedReason: meta.degraded_reason || null,
    sourceRefs: meta.source_refs || [],
  }
}
