# Trading Noobs 用户侧 Trust Metadata Contract（v1）

> 日期：2026-04-13  
> 状态：冻结建议稿  
> 目的：统一用户侧 read model 的 `public_id / as_of / freshness / source / maturity / value_status` 协议，支撑 Timeline、Dashboard、Lifecycle Detail、Insights 的 trust layer

---

## 1. 文档定位

本合同不是业务数据 schema，而是用户侧展示协议的公共元层。

它解决的问题是：

- 前端不再为每个页面单独发明一套 freshness/source 字段
- 后端 read model 可以稳定产出 page-level / module-level / item-level trust 信息
- adapter / view model 层可以围绕统一 contract 建立复用逻辑

本合同默认服务于 user-facing API，不用于 admin 专用内部运维接口。

---

## 2. 冻结目标

以下规则自本版本起冻结：

- 用户侧页面主对象默认以 `public_id` 作为路由与深链标识
- 所有用户侧 read model 根响应必须带 `meta`
- 任何可能因异步派生、样本不足、来源差异而影响用户判断的模块或条目，必须带 `trust`
- `freshness / source / maturity / value_status` 使用统一枚举，不允许页面自行造词

---

## 3. 对象标识规则

### 3.1 主标识

对外返回给前端的核心对象，默认规则如下：

- `User`：返回 `public_id`
- `TradingPosition`：返回 `public_id`
- `PositionEvent`：返回 `public_id`
- `AccountLedgerEntry`：返回 `public_id`
- `InsightRun`：返回 `public_id`
- `InsightArtifact`：返回 `public_id`

内部 bigint `id` 允许存在于数据库、join、后台排障中，但普通用户接口不暴露为主标识。

### 3.2 深链规则

所有可点击对象都应至少提供：

- `public_id`
- `href`
- `object_type`

示例：

```json
{
  "object_type": "TRADING_POSITION",
  "public_id": "pos_01js3rj9v7l5z6t8x2m4q0n1p",
  "href": "/positions/pos_01js3rj9v7l5z6t8x2m4q0n1p"
}
```

---

## 4. 元信息层级

### 4.1 Page-Level

每个根响应必须有：

```json
{
  "meta": {
    "as_of": "2026-04-13T09:30:00Z",
    "generated_at": "2026-04-13T09:30:04Z",
    "freshness": "FRESH",
    "source": "DERIVED",
    "maturity": "STABLE",
    "value_status": "FINAL"
  }
}
```

用途：

- 页面 banner
- 页面级 freshness / degraded 提示
- 通用 adapter 默认 trust 来源

### 4.2 Module-Level

若某个模块的数据状态不同于页面根响应，模块必须携带 `trust`：

```json
{
  "module_key": "weekly_discipline_snapshot",
  "trust": {
    "as_of": "2026-04-13T09:15:00Z",
    "generated_at": "2026-04-13T09:15:08Z",
    "freshness": "DELAYED",
    "source": "DERIVED",
    "maturity": "EARLY_SIGNAL",
    "value_status": "ESTIMATED"
  }
}
```

### 4.3 Item-Level

若单个 item 的来源或 freshness 与所属模块不同，item 必须携带 `trust`。

典型场景：

- timeline 中混合 manual event 与 AI insight
- Review Inbox 中混合同步异常和 checklist miss
- AI insight card 的生成时间晚于页面整体查询时间

---

## 5. 枚举冻结

### 5.1 `freshness`

```ts
type Freshness = "FRESH" | "DELAYED" | "STALE" | "DEGRADED"
```

解释：

- `FRESH`：在约定 SLA 内，可直接信任为当前可用结果
- `DELAYED`：稍晚于目标 SLA，但仍可读
- `STALE`：明显过旧，应提示用户谨慎使用
- `DEGRADED`：不是单纯“旧”，而是存在缺口、失败、降级或覆盖不足

### 5.2 `source`

```ts
type Source = "MANUAL" | "IMPORTED" | "SYNCED" | "DERIVED" | "AI_GENERATED"
```

解释：

- `MANUAL`：用户手工录入
- `IMPORTED`：导入文件得到
- `SYNCED`：外部连接器同步得到
- `DERIVED`：由规则、聚合、物化或分析计算得到
- `AI_GENERATED`：由 AI workflow 产出

### 5.3 `maturity`

```ts
type Maturity = "INSUFFICIENT_SAMPLE" | "EARLY_SIGNAL" | "STABLE"
```

解释：

- `INSUFFICIENT_SAMPLE`：样本不足，主要用于提示不要过度解释
- `EARLY_SIGNAL`：已有趋势，但仍不稳定
- `STABLE`：可作为较成熟结论阅读

### 5.4 `value_status`

```ts
type ValueStatus = "ESTIMATED" | "FINAL"
```

解释：

- `ESTIMATED`：估算值、临时值、待回填值
- `FINAL`：当前口径下的最终值

---

## 6. TypeScript 合同

```ts
export type TrustMeta = {
  as_of: string
  generated_at?: string
  freshness: "FRESH" | "DELAYED" | "STALE" | "DEGRADED"
  source: "MANUAL" | "IMPORTED" | "SYNCED" | "DERIVED" | "AI_GENERATED"
  maturity?: "INSUFFICIENT_SAMPLE" | "EARLY_SIGNAL" | "STABLE"
  value_status?: "ESTIMATED" | "FINAL"
  source_refs?: string[]
  note?: string
}

export type ReadModelEnvelope<T> = {
  data: T
  meta: TrustMeta
}
```

约束：

- `as_of` 必填
- `generated_at` 对异步派生结果强烈建议返回
- `maturity` 对统计、洞察、AI 结果建议必填，对纯手工事件可省略
- `value_status` 对金额、估值、派生指标建议必填

---

## 7. 后端落地规则

### 7.1 根响应规则

后端所有用户侧 read model handler：

- 返回统一 `ReadModelEnvelope<T>`
- 不直接裸返回数组或裸对象
- 若历史接口暂未切换，可由 adapter 层短期补壳，但新接口从第一天起直接返回 envelope

### 7.2 异步派生规则

凡由 `derived` 或 `ai` schema 提供的数据：

- 必须带 `generated_at`
- 必须带 `freshness`
- 必须明确 `value_status`

### 7.3 AI 规则

AI artifact 除 `TrustMeta` 外，还应额外返回：

- `coverage_summary`
- `input_range`
- `evidence_refs`

这些字段不替代 `trust`，而是 AI explainability 的补充。

---

## 8. 前端消费规则

前端 adapter / view model 层必须遵守：

- 优先读取模块自身 `trust`，否则回退到根 `meta`
- 若 `freshness` 为 `STALE` 或 `DEGRADED`，默认触发 banner / pill / inline cue
- 若 `maturity` 为 `INSUFFICIENT_SAMPLE`，默认走 small-data 提示
- 若 `value_status` 为 `ESTIMATED`，关键数字旁必须能看见估算提示

---

## 9. 示例

```json
{
  "data": {
    "headline": "This Week",
    "net_equity_change": 1280.55
  },
  "meta": {
    "as_of": "2026-04-13T09:30:00Z",
    "generated_at": "2026-04-13T09:30:04Z",
    "freshness": "DELAYED",
    "source": "DERIVED",
    "maturity": "EARLY_SIGNAL",
    "value_status": "ESTIMATED",
    "note": "Waiting for one broker sync job to complete"
  }
}
```

---

## 10. 不在本合同内

以下内容不在本合同内冻结：

- 具体页面模块字段
- chart schema 的业务字段定义
- AI artifact 正文结构
- admin 运维接口的内部诊断字段
