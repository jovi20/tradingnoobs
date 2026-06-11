import { buildScatterPoints, scaleLinear } from './chartGeometry'

interface SvgScatterChartProps<T> {
    data: T[]
    getX: (item: T) => number
    getY: (item: T) => number
    getLabel: (item: T) => string
    getColor?: (item: T) => string
    xLabel?: string
    yLabel?: string
}

export function SvgScatterChart<T>({
    data,
    getX,
    getY,
    getLabel,
    getColor = () => '#38bdf8',
    xLabel = 'X',
    yLabel = 'Y',
}: SvgScatterChartProps<T>) {
    const width = 620
    const height = 300
    const padding = { top: 22, right: 24, bottom: 48, left: 58 }
    const innerWidth = width - padding.left - padding.right
    const innerHeight = height - padding.top - padding.bottom
    const sourcePoints = data.map((item) => ({ x: getX(item), y: getY(item) }))
    const points = buildScatterPoints(sourcePoints, innerWidth, innerHeight)
    const xValues = sourcePoints.map((point) => point.x)
    const yValues = sourcePoints.map((point) => point.y)
    const minX = Math.min(...xValues, 0)
    const maxX = Math.max(...xValues, 0)
    const minY = Math.min(...yValues, 0)
    const maxY = Math.max(...yValues, 0)
    const xScale = scaleLinear(minX, maxX, 0, innerWidth)
    const yScale = scaleLinear(minY, maxY, innerHeight, 0)

    return (
        <svg role="img" aria-label={`${xLabel} ${yLabel} scatter chart`} className="h-full w-full" viewBox={`0 0 ${width} ${height}`}>
            <g transform={`translate(${padding.left},${padding.top})`}>
                <rect width={innerWidth} height={innerHeight} rx={18} fill="rgba(248,250,252,0.72)" />
                <line x1={0} x2={innerWidth} y1={yScale(0)} y2={yScale(0)} stroke="#94a3b8" strokeDasharray="4 4" />
                <line x1={xScale(0)} x2={xScale(0)} y1={0} y2={innerHeight} stroke="#94a3b8" strokeDasharray="4 4" />
                {points.map((point, index) => (
                    <g key={`${getLabel(data[index])}-${index}`}>
                        <circle
                            cx={point.cx}
                            cy={point.cy}
                            r={5}
                            fill={getColor(data[index])}
                            stroke="white"
                            strokeWidth={1.5}
                        />
                        <title>{`${getLabel(data[index])}: ${xLabel} ${point.x.toFixed(2)}, ${yLabel} ${point.y.toFixed(2)}`}</title>
                    </g>
                ))}
            </g>
            <text x={width / 2} y={height - 10} textAnchor="middle" className="fill-slate-500 text-[11px]">
                {xLabel}
            </text>
            <text x={16} y={height / 2} textAnchor="middle" transform={`rotate(-90 16 ${height / 2})`} className="fill-slate-500 text-[11px]">
                {yLabel}
            </text>
        </svg>
    )
}
