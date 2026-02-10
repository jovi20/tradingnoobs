
import React, { useMemo } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, ZAxis, Cell } from 'recharts';
import { Position } from '@/lib/api';

interface MaeMfeScatterPlotProps {
    positions: Position[];
}

export function MaeMfeScatterPlot({ positions }: MaeMfeScatterPlotProps) {
    const data = useMemo(() => {
        return positions.map(p => {
            if (!p.average_entry_price || !p.max_price_during_hold || !p.min_price_during_hold) {
                return null;
            }

            const entry = Number(p.average_entry_price);
            const max = Number(p.max_price_during_hold);
            const min = Number(p.min_price_during_hold);

            let mae = 0;
            let mfe = 0;

            if (p.direction === 'LONG') {
                mfe = ((max - entry) / entry) * 100;
                mae = ((min - entry) / entry) * 100;
            } else {
                // Short
                mfe = ((entry - min) / entry) * 100;
                mae = ((entry - max) / entry) * 100;
            }

            return {
                id: p.id,
                symbol: p.symbol,
                mae: parseFloat(mae.toFixed(2)),
                mfe: parseFloat(mfe.toFixed(2)),
                pnl: p.realized_pnl,
                pnlPercent: p.realized_pnl / (entry * p.total_quantity || 1) * 100 // Approx if closed
            };
        }).filter(item => item !== null);
    }, [positions]);

    return (
        <div className="card">
            <div className="p-6 border-b border-slate-100 dark:border-slate-700">
                <h3 className="text-lg font-bold">MAE vs MFE 分析</h3>
            </div>
            <div className="p-6">
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
                                {data.map((entry: any, index: number) => (
                                    <Cell key={`cell-${index}`} fill={entry.pnl >= 0 ? '#10B981' : '#EF4444'} />
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
            </div>
        </div>
    );
}
