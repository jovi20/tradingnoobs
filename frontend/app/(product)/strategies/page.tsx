'use client'

import { useState, useEffect, useEffectEvent } from 'react'
import {
    Plus, Layers, Edit2, Trash2, CheckCircle, PauseCircle, Archive, X,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { strategiesAPI, Strategy, StrategyCreate, ChecklistItem } from '@/lib/api'

import { PageFrame } from '@/components/ui/PageFrame'
import { Button } from '@/components/ui/Button'
import { Input, Textarea, Field } from '@/components/ui/Input'
import { StatusPill } from '@/components/ui/StatusPill'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { LoadingState } from '@/components/ui/Spinner'
import { Checkbox } from '@/components/ui/Checkbox'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '@/components/ui/Dialog'
import type { Tone } from '@/components/ui/tone'

const statusConfig: Record<Strategy['status'], { label: string; tone: Tone; icon: typeof CheckCircle }> = {
    ACTIVE: { label: '使用中', tone: 'positive', icon: CheckCircle },
    PAUSED: { label: '已暂停', tone: 'warning', icon: PauseCircle },
    ARCHIVED: { label: '已归档', tone: 'neutral', icon: Archive },
}

const ruleBlocks: Array<{ key: 'entry_rules' | 'exit_rules' | 'risk_rules'; label: string; tone: string }> = [
    { key: 'entry_rules', label: '入场规则', tone: 'text-profit' },
    { key: 'exit_rules', label: '出场规则', tone: 'text-ai' },
    { key: 'risk_rules', label: '风控规则', tone: 'text-warning' },
]

function StrategyCard({ strategy, onEdit, onDelete }: { strategy: Strategy; onEdit: () => void; onDelete: () => void }) {
    const status = statusConfig[strategy.status]
    const StatusIcon = status.icon

    return (
        <div className="rounded-lg border border-line bg-panel p-5 shadow-panel transition-colors hover:border-line-strong dark:shadow-none">
            <div className="mb-4 flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-md bg-panel-subtle text-ink-soft">
                        <Layers className="h-5 w-5" />
                    </span>
                    <div>
                        <h3 className="text-base font-semibold text-ink">{strategy.name}</h3>
                        <div className="mt-1 flex items-center gap-1.5 text-xs text-ink-muted">
                            <StatusIcon className="h-3.5 w-3.5" />
                            <span>{status.label}</span>
                        </div>
                    </div>
                </div>
                <div className="flex gap-1">
                    <button
                        onClick={onEdit}
                        className="rounded-md p-2 text-ink-muted transition-colors hover:bg-panel-subtle hover:text-ink"
                        aria-label={`编辑策略：${strategy.name}`}
                    >
                        <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                        onClick={onDelete}
                        className="rounded-md p-2 text-ink-muted transition-colors hover:bg-loss/10 hover:text-loss"
                        aria-label={`删除策略：${strategy.name}`}
                    >
                        <Trash2 className="h-4 w-4" />
                    </button>
                </div>
            </div>

            {strategy.description && (
                <p className="mb-4 text-sm leading-6 text-ink-muted">{strategy.description}</p>
            )}

            {strategy.symbols && strategy.symbols.length > 0 && (
                <div className="mb-4 flex flex-wrap gap-1.5">
                    {strategy.symbols.map((symbol) => (
                        <span key={symbol} className="rounded-md bg-panel-subtle px-2 py-1 text-xs font-medium text-ink-soft">{symbol}</span>
                    ))}
                </div>
            )}

            <div className="space-y-2 text-sm">
                {ruleBlocks.map(({ key, label, tone }) => strategy[key] ? (
                    <div key={key} className="rounded-md border border-line bg-panel-subtle/60 p-3">
                        <p className={`mb-1 text-xs font-semibold ${tone}`}>{label}</p>
                        <p className="text-ink-muted">{strategy[key]}</p>
                    </div>
                ) : null)}
            </div>
        </div>
    )
}

const emptyForm: StrategyCreate = {
    name: '', description: '', entry_rules: '', exit_rules: '', risk_rules: '', symbols: [], checklist_items: [],
}

export default function StrategiesPage() {
    const { token } = useAuth()
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null)
    const [form, setForm] = useState<StrategyCreate>(emptyForm)

    const fetchStrategies = async () => {
        if (!token) return
        try {
            setIsLoading(true)
            const data = await strategiesAPI.list(token)
            setStrategies(data)
        } catch (err) {
            console.error(err)
        } finally {
            setIsLoading(false)
        }
    }

    const fetchStrategiesFromEffect = useEffectEvent(() => {
        void fetchStrategies()
    })

    useEffect(() => {
        if (!token) return
        const fetchTimer = window.setTimeout(() => {
            fetchStrategiesFromEffect()
        }, 0)
        return () => window.clearTimeout(fetchTimer)
    }, [token])

    const openCreateModal = () => {
        setEditingStrategy(null)
        setForm(emptyForm)
        setShowModal(true)
    }

    const openEditModal = (strategy: Strategy) => {
        setEditingStrategy(strategy)
        setForm({
            name: strategy.name,
            description: strategy.description || '',
            entry_rules: strategy.entry_rules || '',
            exit_rules: strategy.exit_rules || '',
            risk_rules: strategy.risk_rules || '',
            symbols: strategy.symbols || [],
            checklist_items: strategy.checklist_items || [],
        })
        setShowModal(true)
    }

    const handleSubmit = async () => {
        if (!token || !form.name) return
        setIsSubmitting(true)
        try {
            if (editingStrategy) {
                await strategiesAPI.update(token, editingStrategy.id, form)
            } else {
                await strategiesAPI.create(token, form)
            }
            setShowModal(false)
            fetchStrategies()
        } catch (err) {
            console.error(err)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDelete = async (strategy: Strategy) => {
        if (!token) return
        if (!confirm(`确定要删除策略“${strategy.name}”吗？`)) return
        try {
            await strategiesAPI.delete(token, strategy.id)
            fetchStrategies()
        } catch (err) {
            console.error(err)
        }
    }

    if (isLoading) {
        return <LoadingState label="正在加载策略…" />
    }

    return (
        <PageFrame>
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-[11px] font-semibold text-ink-faint">策略管理</p>
                    <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">交易策略</h1>
                </div>
                <Button onClick={openCreateModal}>
                    <Plus className="h-4 w-4" />
                    新增策略
                </Button>
            </div>

            {strategies.length === 0 ? (
                <EmptyStatePanel
                    icon={<Layers className="h-10 w-10" />}
                    title="暂无交易策略"
                    detail="策略定义你的规则与检查清单，让复盘有明确的纪律锚点。"
                    action={<Button onClick={openCreateModal}><Plus className="h-4 w-4" />创建第一个策略</Button>}
                />
            ) : (
                <div className="grid gap-4 md:grid-cols-2">
                    {strategies.map((strategy) => (
                        <StrategyCard
                            key={strategy.id}
                            strategy={strategy}
                            onEdit={() => openEditModal(strategy)}
                            onDelete={() => handleDelete(strategy)}
                        />
                    ))}
                </div>
            )}

            <Dialog open={showModal} onOpenChange={setShowModal}>
                <DialogContent size="lg" className="max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                        <DialogTitle>{editingStrategy ? '编辑策略' : '新增策略'}</DialogTitle>
                    </DialogHeader>

                    <div className="space-y-4">
                        <Field label="策略名称 *" htmlFor="name">
                            <Input id="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="例如：趋势突破策略" />
                        </Field>
                        <Field label="策略描述" htmlFor="desc">
                            <Textarea id="desc" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="简要描述策略的核心逻辑..." />
                        </Field>
                        <Field label="入场规则" htmlFor="entry">
                            <Textarea id="entry" value={form.entry_rules} onChange={(e) => setForm({ ...form, entry_rules: e.target.value })} placeholder="描述入场条件..." />
                        </Field>
                        <Field label="出场规则" htmlFor="exit">
                            <Textarea id="exit" value={form.exit_rules} onChange={(e) => setForm({ ...form, exit_rules: e.target.value })} placeholder="描述止盈止损条件..." />
                        </Field>
                        <Field label="风控规则" htmlFor="risk">
                            <Textarea id="risk" value={form.risk_rules} onChange={(e) => setForm({ ...form, risk_rules: e.target.value })} placeholder="描述仓位管理和风险控制..." />
                        </Field>

                        <div className="border-t border-line pt-4">
                            <div className="mb-1 flex items-center justify-between">
                                <span className="text-sm font-semibold text-ink-soft">交易前检查清单</span>
                                <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => {
                                        const newItem: ChecklistItem = { id: Date.now(), label: '', category: 'entry', required: false }
                                        setForm({ ...form, checklist_items: [...(form.checklist_items || []), newItem] })
                                    }}
                                >
                                    <Plus className="h-3.5 w-3.5" />添加检查项
                                </Button>
                            </div>
                            <p className="mb-3 text-xs text-ink-muted">开仓时需要确认的检查项，帮助执行交易纪律</p>

                            {(form.checklist_items || []).length === 0 ? (
                                <p className="rounded-md border border-dashed border-line-strong py-4 text-center text-sm text-ink-faint">
                                    暂无检查项，点击上方按钮添加
                                </p>
                            ) : (
                                <div className="space-y-2">
                                    {(form.checklist_items || []).map((item, index) => (
                                        <div key={item.id} className="flex items-center gap-2 rounded-md bg-panel-subtle p-2">
                                            <Input
                                                value={item.label}
                                                onChange={(e) => {
                                                    const updated = [...(form.checklist_items || [])]
                                                    updated[index] = { ...item, label: e.target.value }
                                                    setForm({ ...form, checklist_items: updated })
                                                }}
                                                className="h-8 flex-1 py-1 text-sm"
                                                placeholder="例如：成交量确认"
                                            />
                                            <Select
                                                value={item.category || 'entry'}
                                                onValueChange={(value) => {
                                                    const updated = [...(form.checklist_items || [])]
                                                    updated[index] = { ...item, category: value as 'entry' | 'risk' | 'exit' | 'other' }
                                                    setForm({ ...form, checklist_items: updated })
                                                }}
                                            >
                                                <SelectTrigger size="sm" className="w-24"><SelectValue /></SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="entry">入场</SelectItem>
                                                    <SelectItem value="risk">风控</SelectItem>
                                                    <SelectItem value="exit">出场</SelectItem>
                                                    <SelectItem value="other">其他</SelectItem>
                                                </SelectContent>
                                            </Select>
                                            <label className="flex items-center gap-1.5 text-xs text-ink-muted">
                                                <Checkbox
                                                    checked={item.required || false}
                                                    onCheckedChange={(checked) => {
                                                        const updated = [...(form.checklist_items || [])]
                                                        updated[index] = { ...item, required: checked === true }
                                                        setForm({ ...form, checklist_items: updated })
                                                    }}
                                                />
                                                必填
                                            </label>
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    const updated = (form.checklist_items || []).filter((_, i) => i !== index)
                                                    setForm({ ...form, checklist_items: updated })
                                                }}
                                                className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-loss/10 hover:text-loss"
                                                aria-label={`删除第 ${index + 1} 个检查项`}
                                            >
                                                <X className="h-4 w-4" />
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setShowModal(false)}>取消</Button>
                        <Button onClick={handleSubmit} loading={isSubmitting} disabled={!form.name}>
                            {editingStrategy ? '保存修改' : '创建策略'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </PageFrame>
    )
}
