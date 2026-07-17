# Trading Noobs Frontend

Next.js 前端，负责交易工作台、Timeline、Dashboard、仓位生命周期、设置和管理员操作界面。

更新时间：2026-07-17

## JOURNAL Beta 边界

当前 Beta 默认关闭 Broker network sync、Market、AI/Insights、PDF export、risk cards 和 open registration。对应 optional 页面或组件即使仍存在于源码中，也必须从导航和普通设置中移除，并在直接访问时 fail-closed；不要把代码存在描述为用户可用能力。`/register` 路由模块已删除，受控 invite-only onboarding 由 `JRN-003` 实现后才重新开放。

`IBKR_FLEX_XML_V1` 是 `JRN-013` 至 `JRN-015` 计划中的本地文件导入 adapter，目前尚未实现。前端当前不得展示 Broker Token/Query ID 配置、网络同步按钮或“已连接”状态。

旧 CSV/Excel Import 不满足 owner-bound 持久会话和 canonical identity 合同，已在 API 与 UI 同时关闭；`/positions/import` 直达访问进入框架 not-found 视图。`JRN-011`/`JRN-012` 完成新的 `GENERIC_BOOTSTRAP` preview/confirm 后才可重新开放。

## 技术栈

| 项目 | 当前实现 |
|------|----------|
| 框架 | Next.js 16 / React 19 |
| 语言 | TypeScript |
| 样式 | Tailwind CSS |
| 数据请求 | React Query + 本地 API client / adapters |
| 图表 | 内部 SVG renderer + `chart.v1` schema |

## 目录结构

| 路径 | 说明 |
|------|------|
| `app/` | Next.js App Router 页面入口。 |
| `components/` | 页面组件、领域组件和共享 UI。 |
| `components/charts/` | 图表框架和内部 SVG renderer。 |
| `components/*/domain/` | 领域展示组件。 |
| `components/*/workbench/` | 工作台页面组合组件。 |
| `contexts/` | React context，例如认证状态。 |
| `hooks/` | 页面数据和 UI 逻辑 hooks。 |
| `lib/api.ts` | 当前 API client。 |
| `lib/adapters/` | API DTO 到 read model / UI model 的 adapter 层。 |
| `lib/generated/` | 生成契约输出边界。 |
| `public/` | 静态资源。 |
| `tests/` | 前端 adapter、契约、图表和边界测试。 |

## 本地开发

```bash
cd frontend
npm install
npm run dev
```

默认地址：`http://localhost:3000`

如需连接本地后端，后端默认地址为 `http://localhost:8000`。

## 常用命令

```bash
npm run dev
npm run build
npm run start
npm test
npm run test:browser
npm run lint
npx tsc --noEmit
```

首次运行浏览器门禁前执行 `npx playwright install chromium`。`test:browser` 固定覆盖 `1440x900` 与 `390x844` 两个 viewport。

## 维护注意

- 新页面优先通过 `lib/adapters/` 使用 read model，不直接扩大 legacy DTO import。
- `lib/api.ts` 是当前 API client，不应继续演变成长期 DTO 契约层。
- 新图表优先接入 `components/charts/ChartFrame.tsx` 和 `lib/chartSchemas.ts`。
- Optional capability UI 必须同时服从 deployment ceiling 与 runtime rollout；隐藏入口之外，服务端仍必须独立拒绝。
- 不要为 Broker Sync、Market、AI/Insights、PDF、risk cards 或 open registration 新增 Beta 导航、设置说明或可用性文案。
- `tsconfig.tsbuildinfo` 是 TypeScript 增量编译缓存，不应作为源文件维护。
