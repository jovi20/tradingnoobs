# Trading Noobs Frontend

Next.js 前端，负责交易工作台、Timeline、Dashboard、仓位生命周期、Insights、导入、设置和管理员操作界面。

更新时间：2026-07-06

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
npm run lint
npx tsc --noEmit
```

## 维护注意

- 新页面优先通过 `lib/adapters/` 使用 read model，不直接扩大 legacy DTO import。
- `lib/api.ts` 是当前 API client，不应继续演变成长期 DTO 契约层。
- 新图表优先接入 `components/charts/ChartFrame.tsx` 和 `lib/chartSchemas.ts`。
- `tsconfig.tsbuildinfo` 是 TypeScript 增量编译缓存，不应作为源文件维护。
