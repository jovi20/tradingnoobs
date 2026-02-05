---
sidebar_position: 2
---

# 部署与运维指南

本指南介绍如何在本地运行博客以及如何将其部署到 GitHub Pages。

## 本地运行

在 `website` 目录下：

```bash
# 安装依赖 (如果尚未安装)
npm install

# 启动开发服务器
npm start
```

浏览器将自动打开 `http://localhost:3000`。

## 构建

生成静态文件：

```bash
npm run build
```

构建产物位于 `website/build` 目录。

## 部署到 GitHub Pages

推荐使用 GitHub Actions 自动部署。

### 方法 1: GitHub Actions (推荐)

1. 确保您的仓库包含 `.github/workflows/deploy.yml` 文件。
2. 将代码推送到 GitHub 的 `main` 分支。
3. GitHub Actions 将自动构建并将生成的静态文件部署到 `gh-pages` 分支。
4. 在 GitHub 仓库设置 -> Pages 中，选择源为 `gh-pages` 分支。

### 方法 2: 手动部署

如果您想从本地手动部署：

Windows (cmd):
```bash
cmd /C "set GIT_USER=jovi20 && npm run deploy"
```

PowerShell:
```bash
$env:GIT_USER="jovi20"; npm run deploy
```

## 目录结构说明

- `blog/`: 博客文章 (Markdown 格式)
- `docs/`: 项目文档
- `src/`: 页面源码 (React 组件)
- `docusaurus.config.ts`: 站点配置
