import Link from 'next/link'
import {
    ArrowRight, Wallet, PlusCircle, Upload, Layers,
    Clock3, ClipboardCheck,
} from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import { StatusPill } from '@/components/ui/StatusPill'

const startSteps = [
    { href: '/settings', icon: Wallet, title: '添加账户', detail: '先建立一个交易账户作为资金与仓位的归属。' },
    { href: '/positions/new', icon: PlusCircle, title: '录入第一笔交易', detail: '记录开仓理由、计划与信心，形成第一条事件。' },
    { href: '/positions/import', icon: Upload, title: '导入历史记录', detail: '用 CSV / Excel 批量导入既有交易，快速起步。' },
    { href: '/strategies', icon: Layers, title: '创建第一条策略', detail: '定义规则与检查清单，让复盘有纪律锚点。' },
]

export function TimelineZeroState() {
    return (
        <div className="mx-auto w-full max-w-6xl space-y-8">
            <header className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-canvas">
                    <Clock3 className="h-3.5 w-3.5" />
                    欢迎来到决策工作台
                </div>
                <h1 className="tn-display mt-4 text-3xl font-semibold tracking-tight text-ink md:text-[2.5rem] md:leading-tight">
                    从第一笔交易开始，
                    <br className="hidden sm:block" />
                    把记录变成可复盘的决策线程。
                </h1>
                <p className="mt-3 text-sm leading-6 text-ink-muted md:text-base">
                    录入交易后，时间线会把开仓、加减仓、平仓与复盘串成一条连续的决策记录。
                </p>
            </header>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
                {/* Left — getting started */}
                <section className="space-y-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">开始使用</p>
                    <div className="grid gap-3 sm:grid-cols-2">
                        {startSteps.map((step, index) => {
                            const Icon = step.icon
                            return (
                                <Link
                                    key={step.href}
                                    href={step.href}
                                    className="group flex flex-col rounded-lg border border-line bg-panel p-4 shadow-panel transition-colors hover:border-line-strong dark:shadow-none"
                                >
                                    <div className="flex items-center justify-between">
                                        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-panel-subtle text-ink-soft">
                                            <Icon className="h-[18px] w-[18px]" />
                                        </span>
                                        <span className="tn-nums text-xs font-semibold text-ink-faint">0{index + 1}</span>
                                    </div>
                                    <p className="mt-3 text-sm font-semibold text-ink">{step.title}</p>
                                    <p className="mt-1 text-xs leading-5 text-ink-muted">{step.detail}</p>
                                    <span className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-ink-soft transition-colors group-hover:text-ink">
                                        开始
                                        <ArrowRight className="h-3.5 w-3.5" />
                                    </span>
                                </Link>
                            )
                        })}
                    </div>
                </section>

                {/* Right — experience preview */}
                <section className="space-y-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">未来体验预览</p>
                    <Surface variant="rail" className="space-y-3 p-4">
                        {/* Sample timeline event */}
                        <div className="rounded-lg border border-line bg-panel p-4">
                            <div className="flex items-start gap-3">
                                <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-profit ring-4 ring-panel-subtle" />
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2">
                                        <StatusPill tone="exit">平仓</StatusPill>
                                        <span className="text-xs text-ink-faint">示例 · NVDA</span>
                                    </div>
                                    <p className="mt-2 text-sm font-semibold text-ink">按计划止盈，纪律执行到位</p>
                                    <p className="mt-1 text-sm leading-6 text-ink-muted">触及目标价后分批了结，未追高。</p>
                                </div>
                                <span className="tn-nums shrink-0 text-sm font-semibold text-profit">+$2,140</span>
                            </div>
                        </div>

                        {/* Sample review card */}
                        <div className="rounded-lg border border-line bg-panel p-4">
                            <div className="flex items-center gap-2">
                                <ClipboardCheck className="h-4 w-4 text-ai" />
                                <StatusPill tone="review">复盘</StatusPill>
                            </div>
                            <p className="mt-2 text-sm font-semibold text-ink">本周纪律评分 B+</p>
                            <p className="mt-1 text-sm leading-6 text-ink-muted">检查清单命中 82%，止损执行有 1 次偏移待改进。</p>
                        </div>
                    </Surface>
                    <p className="px-1 text-xs text-ink-faint">
                        一旦产生第一条真实事件，首页会自动切换为你的实时决策时间线。
                    </p>
                </section>
            </div>
        </div>
    )
}
