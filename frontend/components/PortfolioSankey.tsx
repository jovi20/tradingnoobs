import { useState } from 'react'
import { ResponsiveContainer, Sankey } from 'recharts'
import { ChartFrame } from '@/components/charts/ChartFrame'
import { buildPortfolioSankeyChartView, shouldRenderPortfolioSankey } from '@/lib/adapters/chart-views'

interface PortfolioSankeyProps {
    data: {
        nodes: any[];
        links: any[];
    };
    totalAssets: number;
    isMobile: boolean;
}

export default function PortfolioSankey({ data, totalAssets, isMobile }: PortfolioSankeyProps) {
    const [activeIndex, setActiveIndex] = useState<number | null>(null)
    const sankeyData = data ?? { nodes: [], links: [] }
    const chartView = buildPortfolioSankeyChartView(sankeyData)

    return (
        <ChartFrame
            eyebrow="Funds Flow"
            title="资金流向"
            description="本地组合资金流向视图，等待后端 schema-first sankey payload。"
            schema={chartView.schema}
            trustMeta={chartView.trustMeta}
            emptyState={chartView.emptyState}
            dataCount={sankeyData.nodes.length}
        >
            {shouldRenderPortfolioSankey(chartView) && (
                <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <Sankey
                            data={sankeyData}
                            nodePadding={10}
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

                                const isActive = index === activeIndex;

                                return (
                                    <g
                                        onMouseEnter={() => setActiveIndex(index)}
                                        onMouseLeave={() => setActiveIndex(null)}
                                        style={{ cursor: 'pointer' }}
                                    >
                                        <rect x={x} y={y} width={width} height={height} fill={fill} fillOpacity="0.8" rx={2} />
                                        {!isMobile && (
                                            <>
                                                <text
                                                    x={x > containerWidth / 2 ? x - 6 : x + width + 6}
                                                    y={y + height / 2}
                                                    dy={isActive ? -8 : 0} // Shift up if details shown
                                                    textAnchor={x > containerWidth / 2 ? 'end' : 'start'}
                                                    dominantBaseline="middle"
                                                    fill={fill}
                                                    fontSize="12"
                                                    fontWeight="600"
                                                >{name}</text>

                                                {/* Percent & Value Label - Only on Hover */}
                                                {isActive && (
                                                    <text
                                                        x={x > containerWidth / 2 ? x - 6 : x + width + 6}
                                                        y={y + height / 2}
                                                        dy={12}
                                                        textAnchor={x > containerWidth / 2 ? 'end' : 'start'}
                                                        dominantBaseline="middle"
                                                        fill="#64748b"
                                                        fontSize="11"
                                                        fontWeight="500"
                                                    >
                                                        {percent} (${Number(value).toLocaleString()})
                                                    </text>
                                                )}
                                            </>
                                        )}
                                    </g>
                                );
                            }}
                        >
                        </Sankey>
                    </ResponsiveContainer>
                </div>
            )}
        </ChartFrame>
    )
}
