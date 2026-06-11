interface SvgBarChartProps<T> {
    data: T[]
    getLabel: (item: T) => string
    getValue: (item: T) => number
    getColor?: (item: T) => string
    valueLabel?: string
}

export function SvgBarChart<T>({
    data,
    getLabel,
    getValue,
    getColor = () => '#38bdf8',
    valueLabel = 'Value',
}: SvgBarChartProps<T>) {
    const width = 640
    const height = 260
    const padding = { top: 18, right: 18, bottom: 58, left: 48 }
    const innerWidth = width - padding.left - padding.right
    const innerHeight = height - padding.top - padding.bottom
    const values = data.map(getValue)
    const minValue = Math.min(0, ...values)
    const maxValue = Math.max(0, ...values)
    const valueRange = maxValue - minValue || 1
    const barGap = 10
    const barWidth = Math.max(8, (innerWidth - barGap * Math.max(0, data.length - 1)) / Math.max(1, data.length))
    const zeroY = padding.top + innerHeight - ((0 - minValue) / valueRange) * innerHeight

    return (
        <svg role="img" aria-label={valueLabel} className="h-full w-full" viewBox={`0 0 ${width} ${height}`}>
            <line x1={padding.left} x2={width - padding.right} y1={zeroY} y2={zeroY} stroke="#cbd5e1" strokeDasharray="4 4" />
            {data.map((item, index) => {
                const value = getValue(item)
                const x = padding.left + index * (barWidth + barGap)
                const scaledY = padding.top + innerHeight - ((value - minValue) / valueRange) * innerHeight
                const y = Math.min(scaledY, zeroY)
                const barHeight = Math.max(2, Math.abs(zeroY - scaledY))
                return (
                    <g key={`${getLabel(item)}-${index}`}>
                        <rect x={x} y={y} width={barWidth} height={barHeight} rx={5} fill={getColor(item)} />
                        <text
                            x={x + barWidth / 2}
                            y={height - 28}
                            textAnchor="middle"
                            className="fill-slate-500 text-[11px]"
                        >
                            {getLabel(item).slice(0, 10)}
                        </text>
                        <title>{`${getLabel(item)} ${valueLabel}: ${value.toFixed(2)}`}</title>
                    </g>
                )
            })}
        </svg>
    )
}
