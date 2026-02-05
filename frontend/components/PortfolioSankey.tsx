import { Activity } from 'lucide-react'
import { ResponsiveContainer, Sankey, Tooltip } from 'recharts'

interface PortfolioSankeyProps {
    data: {
        nodes: any[];
        links: any[];
    };
    totalAssets: number;
    isMobile: boolean;
}

export default function PortfolioSankey({ data, totalAssets, isMobile }: PortfolioSankeyProps) {
    if (!data || data.nodes.length === 0) return null

    return (
        <div className="card p-6">
            <h3 className="text-sm font-semibold mb-6 flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-500" />
                资金流向 (Funds Flow)
            </h3>
            <div className="w-full h-[400px]">
                <ResponsiveContainer width="100%" height="100%">
                    <Sankey
                        data={data}
                        nodePadding={50}
                        margin={{ left: 20, right: isMobile ? 20 : 120, top: 40, bottom: 20 }}
                        link={{ stroke: '#cbd5e1', strokeOpacity: 0.3 }}
                        node={(props: any) => {
                            const { x, y, width, height, index, payload, containerWidth } = props;
                            const name = payload.name || '';
                            const value = payload.value;

                            // Calculate Percentage relative to Total Assets (Gross Exposure)
                            const total = totalAssets || 1;
                            const percent = (value / total * 100).toFixed(1) + '%';

                            const isTotalAssets = name.includes('Total Assets') || name.includes('总资产');

                            let fill = '#94a3b8';
                            if (name.includes('负债') || name.includes('Short') || name.includes('Borrowed')) fill = '#f87171';
                            else if (name.includes('资产') || name.includes('Long') || name.includes('Owned') || name.includes('Cash')) fill = '#34d399';
                            else if (isTotalAssets) fill = '#8b5cf6';

                            // Special Render for Total Assets (Center Node)
                            if (isTotalAssets) {
                                return (
                                    <g>
                                        <rect x={x} y={y} width={width} height={height} fill={fill} fillOpacity="0.9" rx={2} />
                                        {/* Label Above (Desktop Only) */}
                                        {!isMobile && (
                                            <text
                                                x={x + width / 2}
                                                y={15} // Move to the very top of the chart area
                                                textAnchor="middle"
                                                fill={fill}
                                                fontSize="14"
                                                fontWeight="bold"
                                            >
                                                {name}
                                            </text>
                                        )}
                                        {/* Percent Inside (Always Centered) */}
                                        <text
                                            x={x + width / 2}
                                            y={y + height / 2}
                                            textAnchor="middle"
                                            dominantBaseline="middle"
                                            fill="#fff"
                                            fontSize="12"
                                            fontWeight="500"
                                            style={{ textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}
                                        >
                                            {percent}
                                        </text>
                                    </g>
                                )
                            }

                            return (
                                <g>
                                    <rect x={x} y={y} width={width} height={height} fill={fill} fillOpacity="0.8" rx={2} />
                                    {!isMobile && (
                                        <>
                                            <text
                                                x={x > containerWidth / 2 ? x - 6 : x + width + 6}
                                                y={y + height / 2}
                                                dy={-6}
                                                textAnchor={x > containerWidth / 2 ? 'end' : 'start'}
                                                fill={fill}
                                                fontSize="12"
                                                fontWeight="600"
                                            >{name}</text>
                                            {/* Percent Label */}
                                            <text
                                                x={x > containerWidth / 2 ? x - 6 : x + width + 6}
                                                y={y + height / 2}
                                                dy={10}
                                                textAnchor={x > containerWidth / 2 ? 'end' : 'start'}
                                                fill="#64748b"
                                                fontSize="11"
                                            >
                                                {percent}
                                            </text>
                                        </>
                                    )}
                                </g>
                            );
                        }}
                    >
                        <Tooltip
                            isAnimationActive={false}
                            content={({ payload }) => {
                                if (!payload || !payload.length) return null;
                                const data = payload[0];
                                return (
                                    <div className="bg-slate-800 text-white p-2 rounded shadow text-xs border border-slate-700">
                                        {data.name || (data.payload && data.payload.name) || 'Flow'}: ${Number(data.value).toLocaleString()}
                                    </div>
                                )
                            }}
                        />
                    </Sankey>
                </ResponsiveContainer>
            </div>
        </div>
    )
}
