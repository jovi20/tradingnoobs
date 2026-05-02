# Trading Noobs Lifecycle Detail Contract（v1）

> 日期：2026-04-13  
> 状态：冻结建议稿  
> 目的：定义单笔交易详情页的生命周期线程、evidence、AI sidecar 合同

---

## 1. 文档定位

本合同服务于前端单笔详情页。

页面目标不是展示字段表，而是让用户直接看见：

1. 为什么做这笔交易
2. 执行过程中发生了什么
3. 哪一步偏离了原计划
4. 结果如何形成
5. 最后学到了什么

因此本接口必须返回已经结构化好的 lifecycle read model，而不是要求页面用原始 event 自己拼故事。

---

## 2. 建议路由

建议冻结为：

```http
GET /api/trading-positions/{position_public_id}/lifecycle
```

其中：

- `{position_public_id}` 必须是 `TradingPosition.public_id`
- 不接受内部 bigint id 作为普通用户主路由键

---

## 3. 根响应结构

```ts
type LifecycleDetailResponse = ReadModelEnvelope<{
  review_status: "OPEN" | "CLOSED_PENDING_REVIEW" | "REVIEWED"
  position_summary: PositionSummary
  thesis_block: ThesisBlock
  lifecycle_thread: LifecycleThread
  result_summary: ResultSummary
  execution_quality: ExecutionQualityPanel
  discipline_profile?: DisciplineProfile
  emotion_path?: EmotionPath
  ledger_summary: LedgerSummary
  evidence_list: EvidenceList
  ai_sidecar: AiSidecar
}>
```

---

## 4. Position Summary 合同

```ts
type PositionSummary = {
  public_id: string
  title: string
  status: "OPEN" | "CLOSED" | "ARCHIVED" | "ERROR"
  side: "LONG" | "SHORT"
  account: {
    public_id: string
    label: string
  }
  asset: {
    symbol: string
    asset_label: string
    instrument_label: string
  }
  opened_at: string
  closed_at?: string
  realized_pnl_gross?: number
  realized_pnl_net?: number
  total_fees?: number
  holding_period_seconds?: number
  pnl_basis: {
    cost_basis_method: "FIFO"
    realized_definition: "EVENT_REALIZED"
    unrealized_definition: "MARK_TO_MARKET"
    fee_treatment: "NET_INCLUDED"
    fx_treatment: "EVENT_TIME_ACCOUNT_CCY"
  }
  trust?: TrustMeta
}
```

---

## 5. Thesis Block 合同

```ts
type ThesisBlock = {
  source_event_public_id: string
  thesis?: string
  invalidation_rule?: string
  planned_exit_rule?: string
  sizing_rationale?: string
  expected_holding_period?: string
  checklist_snapshot?: Array<{
    label: string
    checked: boolean
  }>
  trust?: TrustMeta
}
```

规则：

- `source_event_public_id` 默认指向 `OPEN` 事件
- 若 thesis 由后续补录完成，可由最新相关 event 作为 source
- 页面不应再从零散 note 字段拼 thesis block

---

## 6. Lifecycle Thread 合同

### 6.1 线程结构

```ts
type LifecycleThread = {
  nodes: LifecycleNode[]
  trust?: TrustMeta
}
```

### 6.2 节点类型冻结

支持以下节点：

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `REVIEW`
- `AI_CONCLUSION`

### 6.3 节点合同

```ts
type LifecycleNode = {
  node_public_id: string
  node_type: "OPEN" | "ADD" | "REDUCE" | "CLOSE" | "REVIEW" | "AI_CONCLUSION"
  occurred_at: string
  title: string
  summary: string
  related_event_public_id?: string
  quantities?: {
    quantity?: number
    price?: number
    currency?: string
  }
  pnl_delta?: {
    realized_gross?: number
    realized_net?: number
  }
  execution_drift?: {
    has_planned_data: boolean
    has_drift: boolean
    entry_drift_pct?: number
    entry_drift_direction?: "ABOVE" | "BELOW" | "ON_TARGET"
    execution_quality?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR"
  }
  emotion?: string
  confidence?: number
  note?: string
  evidence_refs?: EvidenceRef[]
  href?: string
  trust?: TrustMeta
}
```

规则：

- `REVIEW` 节点可引用 review artifact 或结构化 review 数据
- `AI_CONCLUSION` 节点必须引用 artifact，不允许只返回一段 markdown
- `related_event_public_id` 用于把节点与交易真相事件对齐

---

## 7. 结果与执行质量合同

```ts
type ResultSummary = {
  headline: string
  summary: string
  key_numbers: Array<{
    label: string
    value: string
  }>
  trust?: TrustMeta
}

type ExecutionQualityPanel = {
  execution_quality?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR"
  drift_summary?: string
  checklist_miss_count?: number
  trust?: TrustMeta
}

type DisciplineProfile = {
  headline: string
  summary: string
  trust?: TrustMeta
}

type EmotionPath = {
  points: Array<{
    occurred_at: string
    emotion: string
    confidence?: number
  }>
  trust?: TrustMeta
}
```

---

## 8. Ledger Summary 合同

```ts
type LedgerSummary = {
  account_currency: string
  cash_effects: Array<{
    entry_public_id: string
    entry_type: "DIVIDEND" | "FEE" | "CASH_ADJUSTMENT" | "TRANSFER_IN" | "TRANSFER_OUT"
    amount: number
    currency: string
    amount_in_account_ccy?: number
    occurred_at: string
  }>
  total_fees?: number
  total_dividends?: number
  total_adjustments?: number
  trust?: TrustMeta
}
```

规则：

- `dividend / fee / cash adjustment` 以 ledger 为现金真相
- 页面不应再从 position event 重复推导现金变动

---

## 9. Evidence 与 AI Sidecar 合同

### 9.1 EvidenceList

```ts
type EvidenceRef = {
  ref_type: "POSITION_EVENT" | "LEDGER_ENTRY" | "REVIEW_ARTIFACT" | "INSIGHT_ARTIFACT" | "CHECKLIST_SNAPSHOT" | "CHART"
  public_id: string
  label: string
  href: string
}

type EvidenceList = {
  items: EvidenceRef[]
  trust?: TrustMeta
}
```

### 9.2 AI Sidecar

```ts
type AiSidecar = {
  items: Array<{
    insight_run_public_id: string
    insight_artifact_public_id: string
    title: string
    conclusion: string
    coverage_summary: string
    confidence_label?: string
    recommended_action?: string
    evidence_refs: EvidenceRef[]
    href: string
    trust?: TrustMeta
  }>
  trust?: TrustMeta
}
```

规则：

- 每条 AI sidecar item 必须回指 `insight_run_public_id` 与 `insight_artifact_public_id`
- `evidence_refs` 不能为空数组，除非该条目明确标记为不可展示
- AI sidecar 是辅助层，不替代 lifecycle thread 主叙事

---

## 10. 示例 payload

```json
{
  "data": {
    "review_status": "CLOSED_PENDING_REVIEW",
    "position_summary": {
      "public_id": "pos_01js4p",
      "title": "NVDA swing",
      "status": "CLOSED",
      "side": "LONG",
      "account": {
        "public_id": "acct_01js3n",
        "label": "IBKR Main"
      },
      "asset": {
        "symbol": "NVDA",
        "asset_label": "NVIDIA Corp.",
        "instrument_label": "Common Stock"
      },
      "opened_at": "2026-04-08T14:30:00Z",
      "closed_at": "2026-04-12T15:40:00Z",
      "realized_pnl_net": 820.15,
      "pnl_basis": {
        "cost_basis_method": "FIFO",
        "realized_definition": "EVENT_REALIZED",
        "unrealized_definition": "MARK_TO_MARKET",
        "fee_treatment": "NET_INCLUDED",
        "fx_treatment": "EVENT_TIME_ACCOUNT_CCY"
      }
    },
    "thesis_block": {
      "source_event_public_id": "evt_01js4pe",
      "thesis": "Breakout continuation after earnings reset",
      "invalidation_rule": "Lose prior day low with volume expansion",
      "planned_exit_rule": "Scale out into extension above 2R"
    },
    "lifecycle_thread": {
      "nodes": []
    },
    "result_summary": {
      "headline": "计划基本兑现，但减仓节奏偏慢",
      "summary": "执行质量良好，主要偏差出现在首个减仓节点。"
    },
    "execution_quality": {
      "execution_quality": "GOOD",
      "checklist_miss_count": 1
    },
    "ledger_summary": {
      "account_currency": "USD",
      "cash_effects": []
    },
    "evidence_list": {
      "items": []
    },
    "ai_sidecar": {
      "items": []
    }
  },
  "meta": {
    "as_of": "2026-04-13T09:30:00Z",
    "generated_at": "2026-04-13T09:30:05Z",
    "freshness": "FRESH",
    "source": "DERIVED",
    "maturity": "EARLY_SIGNAL",
    "value_status": "FINAL"
  }
}
```

---

## 11. 明确不做

本合同不冻结：

- 详情页视觉布局
- MAE/MFE 等高级图表细节
- review 编辑器字段定义
- AI artifact 长文正文的渲染方式
