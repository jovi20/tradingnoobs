import { ChartFrame } from '@/components/charts/ChartFrame'
import { SvgSankeyChart } from '@/components/charts/renderers/SvgSankeyChart'
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
                <div className={isMobile ? 'h-[320px] w-full' : 'h-[400px] w-full'}>
                    <SvgSankeyChart data={sankeyData} totalAssets={totalAssets} isMobile={isMobile} />
                </div>
            )}
        </ChartFrame>
    )
}
