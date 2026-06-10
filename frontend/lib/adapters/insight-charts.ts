import type { AnalysisResponse } from '../api.ts'
import type { ChartEmptyState, ChartSchema, ChartTrustMeta } from '../charts.ts'

export interface LegacyAnalysisChartRow {
  name: string
  pnl: number
  winRate: number | null
  count: number
}

export interface LegacyAnalysisChartView {
  data: LegacyAnalysisChartRow[]
  schema: ChartSchema
  trustMeta: ChartTrustMeta
  emptyState: ChartEmptyState
}

type LegacyAnalysisInput = Pick<AnalysisResponse, 'analysis_type' | 'raw_data' | 'created_at'>

function buildBaseSchema(): ChartSchema {
  return {
    schema_version: 'chart.v1',
    chart_type: 'bar',
    data_path: 'analysis.raw_data',
    dimensions: [{ field: 'name', label: 'Analysis bucket' }],
    series: [{ field: 'pnl', label: '平均盈亏' }],
  }
}

function buildTrustMeta(result: LegacyAnalysisInput | null | undefined): ChartTrustMeta {
  return {
    as_of: result?.created_at,
    freshness: 'DELAYED',
    source: 'LOCAL_LEGACY_ANALYSIS',
    source_refs: result ? [`analysis:${result.analysis_type}`] : ['analysis:legacy'],
  }
}

function buildEmptyView(
  result: LegacyAnalysisInput | null | undefined,
  reason: string
): LegacyAnalysisChartView {
  return {
    data: [],
    schema: buildBaseSchema(),
    trustMeta: buildTrustMeta(result),
    emptyState: {
      is_empty: true,
      reason,
      message: reason,
    },
  }
}

export function adaptLegacyAnalysisChart(result: LegacyAnalysisInput | null | undefined): LegacyAnalysisChartView {
  if (!result?.raw_data) return buildEmptyView(result, 'NO_LEGACY_ANALYSIS_DATA')

  if (result.raw_data.stats) {
    const rows = Object.entries(result.raw_data.stats).map(([name, value]: [string, any]) => ({
      name,
      pnl: Number(value.avg_pnl ?? 0),
      winRate: value.win_rate === undefined || value.win_rate === null
        ? null
        : Number((Number(value.win_rate) * 100).toFixed(1)),
      count: Number(value.count ?? 0),
    }))

    return {
      data: rows,
      schema: buildBaseSchema(),
      trustMeta: buildTrustMeta(result),
      emptyState: {
        is_empty: rows.length === 0,
        reason: rows.length === 0 ? 'NO_GROUPED_ANALYSIS_ROWS' : null,
        message: rows.length === 0 ? 'NO_GROUPED_ANALYSIS_ROWS' : undefined,
      },
    }
  }

  if (result.analysis_type === 'checklist_effect') {
    const completed = result.raw_data.checklist_completed
    const ignored = result.raw_data.checklist_ignored
    const rows = [
      { name: '已执行清单', pnl: Number(completed?.avg_pnl ?? 0), winRate: null, count: Number(completed?.count ?? 0) },
      { name: '未执行/未完成', pnl: Number(ignored?.avg_pnl ?? 0), winRate: null, count: Number(ignored?.count ?? 0) },
    ]

    return {
      data: rows,
      schema: buildBaseSchema(),
      trustMeta: buildTrustMeta(result),
      emptyState: { is_empty: false, reason: null },
    }
  }

  return buildEmptyView(result, 'UNSUPPORTED_LEGACY_ANALYSIS_CHART')
}
