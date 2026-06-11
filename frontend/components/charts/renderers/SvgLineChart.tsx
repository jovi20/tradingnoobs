import { buildLinePath, scaleLinear } from './chartGeometry'

interface SvgLineChartProps<T> {
    data: T[]
    getXLabel: (item: T) => string
    getValue: (item: T) => number
    stroke?: string
    valueSuffix?: string
}

export function SvgLineChart<T>({
    data,
    getXLabel,
    getValue,
    stroke = '#0f766e',
    valueSuffix = '',
}: SvgLineChartProps<T>) {
    const width = 720
    const height = 320
    const padding = { top: 20, right: 24, bottom: 42, left: 54 }
    const innerWidth = width - padding.left - padding.right
    const innerHeight = height - padding.top - padding.bottom
    const values = data.map(getValue)
    const minValue = Math.min(...values)
    const maxValue = Math.max(...values)
    const points = data.map((item, index) => ({ x: index, y: getValue(item) }))
    const pathData = buildLinePath(points, innerWidth, innerHeight)
    const yScale = scaleLinear(minValue, maxValue, padding.top + innerHeight, padding.top)
    const zeroY = minValue <= 0 && maxValue >= 0 ? yScale(0) : null

    return (
        <svg role="img" aria-label="Line chart" className="h-full w-full" viewBox={`0 0 ${width} ${height}`}>
            <g transform={`translate(${padding.left},${padding.top})`}>
                <rect width={innerWidth} height={innerHeight} rx={18} fill="rgba(248,250,252,0.72)" />
                {zeroY !== null && (
                    <line
                        x1={0}
                        x2={innerWidth}
                        y1={zeroY - padding.top}
                        y2={zeroY - padding.top}
                        stroke="#cbd5e1"
                        strokeDasharray="4 4"
                    />
                )}
                <path d={pathData} fill="none" stroke={stroke} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
                {points.map((point, index) => {
                    const cx = data.length === 1 ? innerWidth / 2 : (point.x / Math.max(1, data.length - 1)) * innerWidth
                    const cy = yScale(point.y) - padding.top
                    return (
                        <g key={`${getXLabel(data[index])}-${index}`}>
                            <circle cx={cx} cy={cy} r={3.5} fill={stroke} />
                            <title>{`${getXLabel(data[index])}: ${point.y.toFixed(2)}${valueSuffix}`}</title>
                        </g>
                    )
                })}
            </g>
            {data.length > 0 && (
                <>
                    <text x={padding.left} y={height - 12} className="fill-slate-500 text-[11px]">
                        {getXLabel(data[0]).slice(5)}
                    </text>
                    <text x={width - padding.right} y={height - 12} textAnchor="end" className="fill-slate-500 text-[11px]">
                        {getXLabel(data[data.length - 1]).slice(5)}
                    </text>
                </>
            )}
        </svg>
    )
}
