import Link from 'next/link'
import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react'

import { getReviewInboxSummary } from '@/lib/adapters/timeline'
import { getReviewInboxKindLabel, getReviewInboxTone } from '@/lib/adapters/timeline-workbench'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import { StatusPill } from '@/components/ui/StatusPill'

interface ReviewInboxPanelProps {
    reviewInbox: TimelineHomeViewModel['reviewInbox']
}

export function ReviewInboxPanel({ reviewInbox }: ReviewInboxPanelProps) {
    return (
        <Surface variant="rail" className="p-4">
            <SectionHeader
                eyebrow="复盘待办"
                title="待处理复盘"
                description={getReviewInboxSummary(reviewInbox)}
            />

            {reviewInbox.items.length === 0 ? (
                <div className="mt-5 rounded-md border border-dashed border-line-strong p-5 text-sm text-ink-muted">
                    当前没有需要立即处理的复盘待办。
                </div>
            ) : (
                <div className="mt-5 space-y-3">
                    {reviewInbox.items.map((item) => (
                        <div key={item.public_id} className="rounded-md border border-line bg-panel p-4">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <StatusPill tone={getReviewInboxTone(item)}>
                                        {getReviewInboxKindLabel(item.kind)}
                                    </StatusPill>
                                    <p className="mt-2 text-sm font-semibold text-ink">{item.summary}</p>
                                    <p className="mt-1 text-xs leading-5 text-ink-muted">{item.reason}</p>
                                </div>
                                {item.severity === 'CRITICAL' ? (
                                    <AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-loss" />
                                ) : (
                                    <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-ink-faint" />
                                )}
                            </div>
                            <Link href={item.recommended_action.href} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-ink-soft transition-colors hover:text-ink">
                                {item.recommended_action.label}
                                <ChevronRight className="h-3.5 w-3.5" />
                            </Link>
                        </div>
                    ))}
                </div>
            )}
        </Surface>
    )
}
