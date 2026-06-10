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
      is_empty: !data.nodes || data.nodes.length === 0,
      reason: !data.nodes || data.nodes.length === 0 ? 'NO_SANKEY_NODES' : null,
      message: !data.nodes || data.nodes.length === 0 ? '暂无资金流向数据' : undefined,
    } satisfies ChartEmptyState,
  }
}
