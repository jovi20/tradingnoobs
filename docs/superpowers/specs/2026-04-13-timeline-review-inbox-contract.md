# Trading Noobs Timeline + Review Inbox Contract（v1）

> 日期：2026-04-13  
> 状态：冻结建议稿  
> 目的：定义默认首页 `时间线 + Review Inbox` 的用户侧 read model 与 API 合同

---

## 1. 文档定位

本合同对应前端默认首页：

- 顶部摘要条
- Review Inbox
- 主时间线事件流
- 右侧上下文栏

它不是原始 `TradingPosition / PositionEvent / InsightArtifact` 的直出接口，而是首页专用 read model。

---

## 2. 首页回答的问题

根响应必须直接支持回答以下问题：

1. 最近发生了什么
2. 现在最该处理什么
3. 有没有明显异常需要我知道

因此首页接口不允许要求前端再从多个旧接口现场拼装主叙事。

---

## 3. 建议路由

建议冻结为：

```http
GET /api/timeline/home
```

允许查询参数：

- `view=ALL|TRADING|REVIEW|AI|EXCEPTION`
- `cursor=<opaque-cursor>`
- `limit=<int>`
- `selected_object_public_id=<public_id>`

说明：

- 路由名称可以调整，但 contract shape 不应漂移
- `cursor` 用于时间线增量翻页
- `selected_object_public_id` 用于右侧上下文栏定向展开

---

## 4. 根响应结构

```ts
type TimelineHomeResponse = ReadModelEnvelope<{
  page_state: "ZERO" | "EMPTY_CONFIGURED" | "SMALL_DATA" | "READY"
  summary_bar: SummaryBar
  review_inbox: ReviewInbox
  timeline: TimelineFeed
  context_rail: ContextRail
}>
```

约束：

- 根响应必须使用 `ReadModelEnvelope<T>`
- `page_state` 由后端直接判断，前端不靠本地猜测
- `summary_bar / review_inbox / timeline / context_rail` 都允许带模块级 `trust`

---

## 5. 顶部摘要条合同

```ts
type SummaryBar = {
  period_label: "TODAY" | "THIS_WEEK"
  trade_count: number
  review_completion_rate: number | null
  net_equity_change: number | null
  priority_alert_count: number
  trust?: TrustMeta
}
```

字段说明：

- `trade_count`：周期内交易事件数量，不是持仓数
- `review_completion_rate`：已完成 review 的关闭交易占比
- `net_equity_change`：面向首页摘要的净值变化
- `priority_alert_count`：当前 Review Inbox 中高优先项数量

---

## 6. Review Inbox 合同

### 6.1 结构

```ts
type ReviewInbox = {
  counts: {
    total: number
    high_priority: number
  }
  items: ReviewInboxItem[]
  trust?: TrustMeta
}
```

### 6.2 Item 合同

```ts
type ReviewInboxItem = {
  public_id: string
  kind:
    | "MISSING_THESIS"
    | "MISSING_REVIEW"
    | "CHECKLIST_MISS"
    | "LOSING_STREAK"
    | "DATA_STALE"
    | "SYNC_EXCEPTION"
  severity: "INFO" | "NOTICE" | "WARNING" | "CRITICAL"
  summary: string
  reason: string
  recommended_action: {
    kind:
      | "OPEN_POSITION_DETAIL"
      | "START_REVIEW"
      | "COMPLETE_THESIS"
      | "OPEN_SYNC_STATUS"
      | "OPEN_INSIGHT"
    label: string
    href: string
  }
  linked_object: {
    object_type: "TRADING_POSITION" | "POSITION_EVENT" | "ACCOUNT" | "INSIGHT_ARTIFACT"
    public_id: string
    label: string
    href: string
  }
  due_at?: string
  occurred_at: string
  trust?: TrustMeta
}
```

### 6.3 规则

- `MISSING_THESIS` 优先绑定 `TradingPosition.public_id`
- `MISSING_REVIEW` 仅用于已关闭但未完成 review 的交易
- `DATA_STALE` 与 `SYNC_EXCEPTION` 只有在需要用户理解或处理时才进入 Inbox
- Inbox 不负责返回长文本分析，只返回行动导向摘要

---

## 7. 时间线主事件流合同

### 7.1 结构

```ts
type TimelineFeed = {
  active_view: "ALL" | "TRADING" | "REVIEW" | "AI" | "EXCEPTION"
  next_cursor?: string
  groups: TimelineGroup[]
  trust?: TrustMeta
}
```

### 7.2 分组合同

```ts
type TimelineGroup = {
  group_key: string
  group_label: string
  group_type: "DAY" | "WEEK_BUCKET"
  items: TimelineEventCard[]
}
```

### 7.3 事件类型冻结

首页至少支持：

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `REVIEW_COMPLETED`
- `AI_INSIGHT`
- `CHECKLIST_MISS`
- `LOSING_STREAK_ALERT`
- `DATA_STALE`
- `SYNC_EXCEPTION`

### 7.4 事件卡合同

```ts
type TimelineEventCard = {
  event_public_id: string
  thread_public_id: string
  event_type:
    | "OPEN"
    | "ADD"
    | "REDUCE"
    | "CLOSE"
    | "REVIEW_COMPLETED"
    | "AI_INSIGHT"
    | "CHECKLIST_MISS"
    | "LOSING_STREAK_ALERT"
    | "DATA_STALE"
    | "SYNC_EXCEPTION"
  occurred_at: string
  headline: string
  summary: string
  impact_value?: {
    amount?: number
    currency?: string
    percentage?: number
  }
  instrument: {
    asset_label: string
    instrument_label: string
    symbol: string
    href: string
  }
  account?: {
    public_id: string
    label: string
  }
  tags?: string[]
  emotion?: string
  confidence?: number
  checklist_summary?: string
  thesis_excerpt?: string
  invalidation_excerpt?: string
  execution_drift?: {
    has_drift: boolean
    entry_drift_pct?: number
    execution_quality?: "EXCELLENT" | "GOOD" | "FAIR" | "POOR"
  }
  ai_annotation?: {
    artifact_public_id: string
    summary: string
    href: string
  }
  href: string
  trust?: TrustMeta
}
```

### 7.5 时间线规则

- 第一层按天或周桶分组
- 第二层通过 `thread_public_id` 把同一笔交易的相关事件串起来
- 交易决策事件优先
- 纯系统事件默认不进入首页主时间线
- `AI_INSIGHT` 必须指向可下钻 artifact，不允许只有长 markdown

---

## 8. 右侧上下文栏合同

```ts
type ContextRail = {
  selected_object?: {
    object_type: "TRADING_POSITION" | "POSITION_EVENT" | "INSIGHT_ARTIFACT"
    public_id: string
    title: string
    subtitle?: string
    href: string
  }
  weekly_discipline_snapshot?: {
    headline: string
    summary: string
    trust?: TrustMeta
  }
  quick_filters: Array<{
    key: string
    label: string
    active: boolean
  }>
  related_items?: Array<{
    label: string
    href: string
  }>
  trust?: TrustMeta
}
```

---

## 9. 示例 payload

```json
{
  "data": {
    "page_state": "SMALL_DATA",
    "summary_bar": {
      "period_label": "THIS_WEEK",
      "trade_count": 4,
      "review_completion_rate": 0.5,
      "net_equity_change": 1280.55,
      "priority_alert_count": 2
    },
    "review_inbox": {
      "counts": {
        "total": 2,
        "high_priority": 1
      },
      "items": [
        {
          "public_id": "inbox_01js4a",
          "kind": "MISSING_REVIEW",
          "severity": "WARNING",
          "summary": "NVDA swing 已平仓，但还没有写复盘",
          "reason": "Closed position without completed review artifact",
          "recommended_action": {
            "kind": "START_REVIEW",
            "label": "开始复盘",
            "href": "/positions/pos_01js4p/review"
          },
          "linked_object": {
            "object_type": "TRADING_POSITION",
            "public_id": "pos_01js4p",
            "label": "NVDA swing",
            "href": "/positions/pos_01js4p"
          },
          "occurred_at": "2026-04-13T08:20:00Z"
        }
      ]
    },
    "timeline": {
      "active_view": "ALL",
      "groups": []
    },
    "context_rail": {
      "quick_filters": []
    }
  },
  "meta": {
    "as_of": "2026-04-13T09:30:00Z",
    "generated_at": "2026-04-13T09:30:03Z",
    "freshness": "DELAYED",
    "source": "DERIVED",
    "maturity": "EARLY_SIGNAL",
    "value_status": "ESTIMATED"
  }
}
```

---

## 10. 明确不做

本合同不负责冻结：

- 快速记录表单字段
- Timeline 卡片视觉布局
- 右侧上下文栏的完整排序策略
- Review 正文编辑器结构
