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
            eyebrow="Legacy analytics"
            title="MAE vs MFE 分析"
            description="从旧 Position 数据本地计算最大不利/有利波动，用于迁移期复盘。"
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
                        getColor={(entry) => (entry.pnl >= 0 ? '#10B981' : '#EF4444')}
                        xLabel="MAE (Adverse) %"
                        yLabel="MFE (Favorable) %"
                    />
                </div>
                <div className="mt-4 text-sm text-gray-500">
                    <p>
                        <strong>MAE (Maximum Adverse Excursion):</strong> Maximum loss % during the trade.
                        Closer to 0 means better entry timing.
                    </p>
                    <p>
                        <strong>MFE (Maximum Favorable Excursion):</strong> Maximum profit % during the trade.
                        Indicates potential profit that was available.
                    </p>
                </div>
            </>
        </ChartFrame>
    );
}
