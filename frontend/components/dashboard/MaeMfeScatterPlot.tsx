import { ChartFrame } from '@/components/charts/ChartFrame';
import { SvgScatterChart } from '@/components/charts/renderers/SvgScatterChart';
import {
    buildMaeMfeScatterPoints,
    localLegacyAnalyticsTrust,
    maeMfeScatterSchema,
} from '@/lib/adapters/chart-views';
import type { Position } from '@/lib/api';

interface MaeMfeScatterPlotProps {
    positions: Position[];
}

export function MaeMfeScatterPlot({ positions }: MaeMfeScatterPlotProps) {
    const data = buildMaeMfeScatterPoints(positions);

    return (
        <ChartFrame
            eyebrow="迁移期分析"
            title="最大不利与有利波动（MAE / MFE）"
            description="从旧版持仓数据本地计算最大不利与有利波动，用于迁移期复盘。"
            schema={maeMfeScatterSchema}
            trustMeta={localLegacyAnalyticsTrust}
            emptyState={{
                is_empty: data.length === 0,
                reason: data.length === 0 ? 'NO_MAE_MFE_POINTS' : null,
                message: data.length === 0 ? '暂无可计算 MAE/MFE 的历史持仓。' : undefined,
            }}
            dataCount={data.length}
        >
            <>
                <div className="h-[300px] w-full">
                    <SvgScatterChart
                        data={data}
                        getX={(entry) => entry.mae}
                        getY={(entry) => entry.mfe}
                        getLabel={(entry) => String(entry.id)}
                        getColor={(entry) => (entry.pnl >= 0 ? '#1A7F5C' : '#B84A39')}
                        xLabel="最大不利波动（MAE）%"
                        yLabel="最大有利波动（MFE）%"
                    />
                </div>
                <div className="mt-4 text-sm text-ink-muted">
                    <p>
                        <strong>最大不利波动（MAE）：</strong>持仓期间的最大浮亏比例，越接近 0 通常表示入场时机越好。
                    </p>
                    <p>
                        <strong>最大有利波动（MFE）：</strong>持仓期间的最大浮盈比例，反映曾经出现过的潜在收益。
                    </p>
                </div>
            </>
        </ChartFrame>
    );
}
