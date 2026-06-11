import type { Position } from '../api.ts'
import type { ChartEmptyState, ChartSchema, ChartTrustMeta } from '../charts.ts'

export interface MaeMfeScatterPoint {
  id: number
  symbol: string
  mae: number
  mfe: number
  pnl: number
  pnlPercent: number
}

export function buildMaeMfeScatterPoints(positions: Position[]): MaeMfeScatterPoint[] {
  return positions
    .map((position) => {
      if (!position.average_entry_price || !position.max_price_during_hold || !position.min_price_during_hold) return null

      const entry = Number(position.average_entry_price)
      const max = Number(position.max_price_during_hold)
      const min = Number(position.min_price_during_hold)
      const quantity = Number(position.total_quantity || 1)
      const mfe = position.direction === 'LONG'
        ? ((max - entry) / entry) * 100
        : ((entry - min) / entry) * 100
      const mae = position.direction === 'LONG'
        ? ((min - entry) / entry) * 100
        : ((entry - max) / entry) * 100
      const pnl = Number(position.realized_pnl ?? 0)

      return {
        id: position.id,
        symbol: position.symbol,
        mae: Number(mae.toFixed(2)),
        mfe: Number(mfe.toFixed(2)),
        pnl,
        pnlPercent: Number((pnl / (entry * quantity || 1) * 100).toFixed(2)),
      }
    })
    .filter((point): point is MaeMfeScatterPoint => point !== null)
}

export const maeMfeScatterSchema: ChartSchema = {
  schema_version: 'chart.v1',
  chart_type: 'scatter',
  data_path: 'positions',
  dimensions: [{ field: 'mae', label: 'MAE %' }],
  series: [{ field: 'mfe', label: 'MFE %' }],
}

export const localLegacyAnalyticsTrust: ChartTrustMeta = {
  freshness: 'DELAYED',
  source: 'LOCAL_LEGACY_ANALYTICS',
  source_refs: ['legacy:positions'],
}

export function buildPortfolioSankeyChartView(data: { nodes: unknown[]; links: unknown[] }) {
  const hasNodes = Array.isArray(data.nodes) && data.nodes.length >= 2
  const hasLinks = Array.isArray(data.links) && data.links.some((link) => {
    if (!link || typeof link !== 'object' || !('value' in link)) return false
    return Number((link as { value?: unknown }).value || 0) > 0
  })
  const isEmpty = !hasNodes || !hasLinks
  const emptyReason = !hasNodes ? 'NO_SANKEY_NODES' : 'NO_SANKEY_LINKS'

  return {
    schema: {
      schema_version: 'chart.v1',
      chart_type: 'sankey',
      data_path: 'portfolio.sankey',
      dimensions: [{ field: 'nodes', label: 'Nodes' }],
      series: [{ field: 'links', label: 'Links' }],
    } satisfies ChartSchema,
    trustMeta: {
      freshness: 'DELAYED',
      source: 'LOCAL_PORTFOLIO_FLOW_VIEW',
      source_refs: ['dashboard:portfolio-sankey'],
    } satisfies ChartTrustMeta,
    emptyState: {
      is_empty: isEmpty,
      reason: isEmpty ? emptyReason : null,
      message: isEmpty ? '暂无资金流向数据' : undefined,
    } satisfies ChartEmptyState,
  }
}

export function shouldRenderPortfolioSankey(view: ReturnType<typeof buildPortfolioSankeyChartView>) {
  return !view.emptyState.is_empty
}

export function shouldRenderEquityLineChart(
  history: Array<{ pnl?: number | null; pnl_percent?: number | null; total_equity?: number | null }>
) {
  return history.some((point) => (
    Number(point.pnl || 0) !== 0
    || Number(point.pnl_percent || 0) !== 0
    || Number(point.total_equity || 0) !== 0
  ))
}
