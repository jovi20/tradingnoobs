import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ZAxis, Cell } from 'recharts';
import { ChartFrame } from '@/components/charts/ChartFrame';
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
                    <ResponsiveContainer width="100%" height="100%">
                        <ScatterChart
                            margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
                        >
                            <CartesianGrid />
                            <XAxis
                                type="number"
                                dataKey="mae"
                                name="MAE %"
                                unit="%"
                                label={{ value: 'MAE (Adverse) %', position: 'insideBottom', offset: -10 }}
                            />
                            <YAxis
                                type="number"
                                dataKey="mfe"
                                name="MFE %"
                                unit="%"
                                label={{ value: 'MFE (Favorable) %', angle: -90, position: 'insideLeft' }}
                            />
                            <ZAxis type="number" dataKey="id" range={[50, 50]} />
                            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                            <ReferenceLine y={0} stroke="#666" strokeDasharray="3 3" />
                            <ReferenceLine x={0} stroke="#666" strokeDasharray="3 3" />

                            <Scatter name="Positions" data={data} fill="#8884d8">
                                {data.map((entry) => (
                                    <Cell key={entry.id} fill={entry.pnl >= 0 ? '#10B981' : '#EF4444'} />
                                ))}
                            </Scatter>
                        </ScatterChart>
                    </ResponsiveContainer>
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
