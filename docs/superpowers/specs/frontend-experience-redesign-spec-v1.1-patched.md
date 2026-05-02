# Trading Noobs 前端体验重构设计（Patched v1.1）

> 日期：2026-04-07  
> 状态：基于已确认前端设计基线补丁后的冻结建议稿，可进入 implementation planning  
> 范围：用户侧前端体验重构、信息架构重置、设计系统底座、以及与平台底座升级对齐的前端适配策略

---

## 1. 文档定位

这不是一次“视觉翻新”文档，而是一份把前端从“页面集合”升级为“决策复盘工作台”的产品体验修订稿。

本补丁版在既有设计基线之上，额外冻结以下内容：

- 从页面结构升级为 **产品循环设计**
- 从“时间线首页”升级为 **时间线 + Review Inbox 首页**
- 从“有 AI 内容”升级为 **有证据结构的 AI sidecar**
- 从“更好看”升级为 **更可信、更克制、更适合金融决策的视觉纪律**
- 从“支持空状态”升级为 **区分 zero / empty / stale / error / small-data** 的状态体系
- 从“前端适配后端变化”升级为 **显式对齐 TradingPosition / PositionEvent / freshness / audit cues**

本设计默认建立在以下前提之上：

- 产品仍处于 pre-production 阶段，可接受前端 hard cutover
- 旧页面结构与旧交互不要求长期兼容
- 新前端可围绕新的平台底座、交易真相模型、analytics 契约和 AI 工作流重新组织

---

## 2. 产品核心思想

### 2.1 产品主身份

新的用户侧前端必须明确被用户感知为：

- 决策复盘工作台
- timeline-first 的交易日志产品
- 由 AI 辅助、但不被 AI 霸占的交易反思环境

它不应该看起来像：

- 券商终端
- 通用管理后台
- 纯内容阅读产品
- 高刺激、强投机气质的加密赌场式界面

### 2.2 用户承诺

用户打开产品后，应能在极短时间内回答四个问题：

1. 我最近做了什么
2. 哪些交易或复盘动作现在最值得我处理
3. 我的决策和执行质量最近怎样
4. 我下一步该重复什么、停止什么、修正什么

### 2.3 产品闭环

本产品的前端体验必须围绕三条循环，而不只是围绕页面：

#### Capture Loop

快速记录真实事件，先完成 essential capture，再逐步补充高阶上下文。

典型动作：

- 记录开仓 / 加仓 / 减仓 / 平仓
- 记录情绪、信心、原因、标签
- 稍后补 thesis、invalidation、checklist、note

#### Review Loop

系统主动把用户拉回复盘，而不是等用户自己想起。

典型触发：

- 平仓后未完成 review
- checklist miss
- 连续亏损
- 执行明显偏离计划
- 同步或数据问题导致某些关键指标待确认

#### Learn Loop

系统把分析结论重新反馈到规则、清单、行为模式和后续执行中。

典型输出：

- 纪律问题归因
- 情绪与 PnL 相关模式
- 策略健康度变化
- 亏损连击分析
- 对下一次交易前检查动作的建议

---

## 3. 体验原则（补强版）

### 3.1 Timeline-First

默认首页必须是时间线，但不能是纯 feed，而必须是“事件流 + 下一步动作”的组合体验。

### 3.2 Review-Centric

PnL 很重要，但不应独占产品中心。复盘完成度、执行偏移、纪律表现、情绪轨迹与 thesis 质量必须进入主叙事。

### 3.3 Progressive Disclosure

首页先给摘要与动作，再逐层展开证据、细节与上下文，避免一上来就是数据墙。

### 3.4 Thread Continuity

同一笔交易必须从 `OPEN -> ADD/REDUCE -> CLOSE -> REVIEW -> AI conclusion` 连成线程。

### 3.5 AI as Copilot

AI 只能做 sidecar intelligence：

- 不做首页中心 Hero
- 不做聊天框霸屏
- 不在没有证据结构时输出“长段点评”

### 3.6 Trust Before Delight

金融产品的高级感，先来自可信，再来自漂亮。时间戳、freshness、来源、口径、证据结构必须默认可见。

### 3.7 Mobile Capture, Desktop Analysis

移动端优先记录和轻复盘；桌面端优先深分析、比较和完整线程阅读。

---

## 4. 信息架构修订

### 4.1 用户侧一级导航（桌面）

建议冻结为：

- `时间线`
- `Dashboard`
- `交易`
- `规则与清单`
- `洞察`
- `设置`

说明：

- 原“持仓”对用户心智过窄，容易被理解为仅看 open positions；前台建议改为“交易”或“交易档案”。
- 原“策略”一词对 discretionary trader 过于硬核，建议改为“规则与清单”，更贴近本产品的纪律与方法定位。

### 4.2 用户侧一级导航（移动）

建议采用 **4 + 1** 的底部导航：

- `首页`
- `交易`
- 中央 `快速记录`
- `复盘/洞察`
- `我的`

说明：

- `Dashboard` 在移动端不强制常驻底栏，可作为首页里的次级视角或“我的”中的入口。
- `设置`、`账户`、`主题`、`连接器` 等进入“我的”。

### 4.3 Admin 独立化

Admin 继续独立为单独 route family：

- `/admin/platform`
- `/admin/users`
- `/admin/jobs`
- `/admin/market-data`
- `/admin/ai`
- `/admin/ops`

Admin 与 user 不仅路由分离，也应共享最少的视觉语义：用户侧是复盘工作台，后台是运维与治理平面。

---

## 5. 首页重构：时间线 + Review Inbox

### 5.1 首页职责

首页默认回答的不是“整体表现如何”，而是：

- 最近发生了什么
- 现在最该处理什么
- 是否有明显异常需要我知道

### 5.2 桌面端首页结构

建议冻结为以下四段：

1. **顶部摘要条**
   - `Today / This Week`
   - 本周交易数、复盘完成率、净值变化、当前重点提醒数量

2. **Review Inbox**
   - 待补 thesis
   - 已平仓未 review
   - checklist miss
   - losing streak
   - 数据 stale / 同步异常（仅在需要用户理解或处理时显示）

3. **主时间线事件流**
   - 按天或按交易对象分组
   - 支持视角切换：全部 / 仅交易 / 仅复盘 / 仅 AI / 仅异常

4. **右侧上下文栏**
   - 当前选中对象摘要
   - 本周纪律画像
   - 快速筛选
   - 相关洞察或待办

### 5.3 移动端首页结构

- 顶部：页面标题 + 当日/本周轻摘要
- 下方：Review Inbox 横滑卡或可收起卡组
- 中部：单列时间线
- 右侧上下文转为 bottom sheet / drawer
- 底部：一级导航 + 中央快速记录

### 5.4 时间线分层规则

时间线必须避免噪音化，建议固定两层分组：

- 第一层：按天 / 本周 / 上周分组
- 第二层：同一交易对象的相关事件在视觉上形成线程

额外规则：

- 交易决策事件优先
- 系统事件默认不混入主叙事
- 只有会影响用户判断或需要处理的系统事件，才进入首页主视野

### 5.5 时间线事件类型

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

### 5.6 事件卡协议

每张事件卡至少包含：

- 头部：时间、事件类型、标的/对象、影响值
- 摘要：一句话说明发生了什么
- 元数据：账户、规则/清单、情绪、信心、标签
- 展开区：thesis、invalidation、执行偏移、checklist、AI 注释、深链入口
- 信任信息：数据来源、生成时间、freshness 状态、是否为 AI 总结

事件卡必须看起来像“一个决策片段”，而不是“表格行换皮”。

---

## 6. Dashboard 重新定性

### 6.1 Dashboard 职责

Dashboard 继续保留，但它只负责回答：

- 整体状态怎么样
- 风险与表现结构是什么
- 过去一段时间有什么变化

它不再承担“最近发生了什么”的职责。

### 6.2 Dashboard 内容优先级

建议优先承载：

- equity curve
- drawdown
- realized / unrealized 结构
- 风险暴露
- 规则与清单健康度
- 账户与持仓分布
- data freshness
- AI 周摘要

### 6.3 Dashboard 视觉纪律

- 一屏只允许一个 hero chart
- 其余模块采用中等密度网格
- 不把首页的时间线内容复制过来
- 强制展示 `as of` 时间与 freshness

### 6.4 移动端 Dashboard

移动端 Dashboard 不追求桌面等密度镜像，而是改为摘要视图，优先：

- 净值变化
- 本周表现
- 关键警示
- 一到两个最重要的图

---

## 7. 单笔详情页：从字段页到生命周期线程页

### 7.1 页面目标

单笔详情必须回答：

- 为什么做这笔交易
- 执行过程中发生了什么
- 哪一步偏离了原计划
- 结果是如何形成的
- 最后学到了什么

### 7.2 建议结构

主栏：

- 顶部对象摘要
- 生命周期线程
- 复盘结论

右栏：

- 结果摘要
- 执行质量
- 纪律画像
- 情绪轨迹
- AI key takeaways

### 7.3 生命周期线程节点

建议固定支持：

- `OPEN`
- `ADD`
- `REDUCE`
- `CLOSE`
- `REVIEW`
- `AI_CONCLUSION`

### 7.4 信息顺序原则

应优先展示：

1. thesis / invalidation / sizing rationale
2. 事件序列
3. 结果归因
4. 细节字段

而不是先堆参数和统计卡，再让用户自己拼故事。

### 7.5 详情页的信任提示

所有关键数值和分析块应可下钻查看：

- 来源：manual / imported / synced / AI-generated
- 计算口径：realized / unrealized / with fee / net / gross
- `as of` 时间
- freshness

---

## 8. 规则与清单页（原“策略”页）

### 8.1 页面定位

该页不是量化策略库，而是：

- 规则库
- checklist 体系
- 方法偏好与纪律表现页

### 8.2 页面回答的问题

- 哪些规则真正有效
- 哪些 checklist 经常 miss
- 某类决策模式的盈亏特征如何
- 我是否在执行上持续偏离自己认可的方法

### 8.3 适合承载的内容

- checklist 命中率
- 规则维度的表现分布
- 常见 miss 类型
- AI 规则健康度总结
- 高频偏差与改进建议

---

## 9. 洞察页：从内容容器到深读页

### 9.1 页面定位

洞察页应是“档案馆 + 深读页”，而不是 AI 唯一存在的地方。

真正有用的 AI 提示，应分布在：

- 首页时间线
- 详情页
- Dashboard
- 规则与清单页

### 9.2 洞察页内容

- 周报 / 周洞察
- 分析报告索引
- 可回看的专题分析
- 筛选与归档能力
- 与交易对象、账户、规则页的深链

### 9.3 AI Insight Card 协议

每张 AI insight card 必须至少包含：

- 一句结论
- 证据来源（交易范围 / 时间范围 / 维度）
- 置信度或适用范围
- 生成时间
- freshness / 数据覆盖提示
- 推荐动作
- 深链入口

AI 卡片默认不能只是 markdown 大段文字。

---

## 10. 状态体系补丁

### 10.1 必须统一的状态

所有核心页必须支持：

- `zero state`
- `loading state`
- `empty-but-configured state`
- `small-data state`
- `stale data state`
- `error state`

### 10.2 新增：Small-Data State

这是本产品非常关键但原 spec 未单列的一种状态。

场景：

- 用户已有少量交易数据，但样本不足
- 指标看起来能算，但统计意义不足
- AI 洞察可生成，但不够稳定

推荐呈现方式：

- 告知“已有基础数据，但当前更适合看事件线和单笔复盘”
- 告知“继续记录 N 笔后，将获得更稳定的规则/洞察分析”
- 引导优先补 thesis / checklist / review，而不是执着于宏观统计

### 10.3 新增：成熟度提示

针对洞察和 Dashboard 的某些分析，前端应支持显示成熟度，例如：

- `样本不足`
- `初步可读`
- `较稳定`

这能直接提升信任感。

---

## 11. 信任与可解释性设计

### 11.1 必须默认可见的信息

以下信息必须成为视觉系统的一部分，而不是隐藏在 tooltip 深处：

- `as of` 时间
- 来源标签：manual / imported / synced / AI-generated
- freshness：fresh / delayed / stale / degraded
- 是否为估算值或最终值

### 11.2 数据质量提示层级

建议分三层：

- page-level：页面整体 freshness / degraded banner
- module-level：某张图、某个指标的数据质量提示
- item-level：事件或 AI 卡上的来源/生成信息

### 11.3 AI 可解释性

AI 输出至少要做到：

- 说明用的是什么范围
- 说明何时生成
- 说明是否受样本不足影响
- 允许用户跳转回支撑证据

---

## 12. 视觉方向补丁

### 12.1 总体气质

前端视觉必须传达：

- 冷静
- 克制
- 可信
- 有结构
- 适合深度阅读和复盘

### 12.2 禁止的气质

以下气质不应出现于主工作流页面：

- 大面积发光渐变
- 过强玻璃拟态
- 高饱和盈利/亏损刺激色
- 营销页式 hero 区块
- 高频 pulsing 动效

### 12.3 颜色纪律

建议采用 `neutral-first, dark-equal` 原则：

- Light mode 是首要参考，但 dark mode 不是附属主题
- 盈利/亏损色保持深、稳、克制
- AI / insight 色不抢主内容，只做结构提示
- warning 使用柔和琥珀，不做刺眼橙黄

### 12.4 字体纪律

建议继续采用三层角色，但补硬两条：

- 关键数字使用 mono 或 tabular lining
- Serif 仅用于极少数叙事标题，不进入主工作流正文

### 12.5 图表纪律

- 每页最多一个强主图
- 同一屏的图表风格必须统一
- 图表下必须有简要说明、时间语境与质量提示
- 图表不是为了“显得专业”，而是为了帮助决策理解

### 12.6 动效纪律

动效必须服务于层级变化：

- 卡片展开/收起
- 时间线进入
- drawer / bottom sheet
- 筛选切换反馈

不允许使用与金融决策无关的装饰性动画。

---

## 13. 设计系统补丁

### 13.1 Token 层

除颜色、字体、间距、圆角、阴影外，应新增明确 token：

- data-quality colors
- profit/loss semantic scale
- number typography scale
- card density scale
- page shell spacing scale

### 13.2 Primitive 组件层

补充要求：

- banner 组件必须支持 freshness / degraded / sample-size 提示
- badge 组件必须可表达来源、质量、成熟度、审计来源
- skeleton 要有列表型和图表型两类

### 13.3 Domain 组件层

建议固定建设：

- timeline event card
- review inbox card
- lifecycle thread block
- AI insight card
- evidence list
- freshness pill
- metric explanation row
- chart container

### 13.4 可访问性

V1 即应满足基本可访问性：

- 键盘可达
- 焦点可见
- 对比度达标
- 状态信息不能只靠颜色表达
- 移动端点击热区足够大

---

## 14. 前端架构与后端对齐补丁

### 14.1 Adapter / View Model 层

前端必须引入 adapter / view model 层，至少承担：

- 标准化 API 返回
- 吸收命名变化：`Position -> TradingPosition`、`TradeBatch -> PositionEvent`
- 输出页面专用 view model
- 屏蔽后端 DTO 的演进波动

### 14.2 Chart 契约层

所有图表容器必须从第一天开始消费 schema-first 数据，不再让页面直接吃接口特制形状。

### 14.3 交易对象展示层级

前端的“交易”页默认分组必须与后端保持一致：

1. 按上市资产分组
2. 组内按账户分组
3. 账户内按交易工具展示

### 14.4 Freshness 原生化

由于 Dashboard 和部分 analytics 读模型是异步刷新的，前端必须原生展示：

- 指标更新时间
- 图表更新时间
- 数据是否 delayed / stale
- 刷新入口或说明

### 14.5 路由家族

建议保持：

- `app/(user)/timeline`
- `app/(user)/dashboard`
- `app/(user)/positions`
- `app/(user)/playbook` 或 `app/(user)/rules`
- `app/(user)/insights`
- `app/(user)/settings`
- `app/(admin)/admin/...`

说明：前台 URL 不必强绑定后端领域对象命名，但页面语义必须与后端真相模型兼容。

---

## 15. 实施分期（修订版）

### Phase 1：Shell / Navigation / Design System / Trust Layer

先落地：

- user/admin shell 分离
- 新导航体系
- token system
- typography / number system
- primitive components
- freshness / source / sample-size banners
- adapter 层雏形

目标：

- 即使页面未完全迁完，产品气质、结构和信任层先成立

### Phase 2：Timeline + Review Inbox

再落地：

- 新首页
- Review Inbox
- 零数据首页
- small-data state
- 移动端快速记录与上下文抽屉

目标：

- Capture / Review 主循环先成立

### Phase 3：Lifecycle Detail + Rules & Checklist

再落地：

- 生命周期式单笔详情页
- 规则与清单页
- 详情页 evidence / AI sidecar
- 交易页新分组与信息结构

目标：

- 单笔交易与方法论页面真正承载 Learn Loop

### Phase 4：Dashboard + Insights

再落地：

- 新 Dashboard
- 洞察页
- chart container system
- chart schema 适配
- data freshness / maturity / risk context

目标：

- 宏观状态与分析体系成熟，但不反客为主

### Phase 5：Polish / Secondary Surfaces

最后落地：

- 设置页重构
- admin 前台壳统一
- 微动效
- 可访问性回补
- 暗色主题打磨

目标：

- 次级页面全部进入统一产品语言

---

## 16. 进入 implementation planning 前的冻结项（修订后）

以下内容建议视为冻结项：

- 默认首页是 `时间线 + Review Inbox`，不是纯 Dashboard，也不是纯 feed
- `Dashboard` 保留，但不是默认落点
- 移动端采用 `4 + 1` 导航结构，中央保留快速记录
- 用户主产品 mobile-first；深分析与 admin desktop-first
- 单笔详情采用生命周期线程结构，而不是 tab 拼盘
- AI 是 sidecar intelligence，必须具备证据结构
- 前端必须引入 adapter / view model 层
- chart 容器必须走 schema-first 契约
- 用户与 admin 必须分离 shell 与 route family
- 所有关键页面必须原生展示 freshness / source / maturity cues
- 必须新增 `small-data state`
- 视觉上采用克制、可信、工作台式风格，不走营销页或交易所终端风格

---

## 17. 成功标准（修订后）

这次前端重构成功的标志应是：

- 新用户一进入就知道这是一个帮助其复盘决策的产品
- 有数据的用户打开首页就能同时看到“最近发生了什么”和“现在最该处理什么”
- 一笔交易能被读成完整生命周期故事，而不是参数堆
- AI 内容有证据、有边界、有深链，而不是一段不可验证的话
- Dashboard 看起来像宏观驾驶舱，而不是首页副本
- 移动端记录与补复盘是顺手的
- 桌面端分析与比较是平静、可信、有结构的
- 后端契约继续变化时，主要由 adapter / schema 层承压，而不是页面全面碎裂

---

## 18. 总结

这次前端重构的真正目标，不是让页面更花，而是让产品更有中心思想：

- 从 `dashboard-first` 转向 `timeline + review-first`
- 从 `pnl-only` 转向 `decision-quality-aware`
- 从 `页面堆叠` 转向 `capture / review / learn` 产品闭环
- 从 `通用 SaaS 风格` 转向 `可信、克制、可深读` 的复盘工作台
- 从 `DTO 直连` 转向 `adapter + schema-first` 的可演进契约层

最终目标，是让 Trading Noobs 前端真正成为一个帮助用户看见行为模式、修正决策习惯、提高复盘质量的工作台，而不是一个长得比较整齐的交易后台。
