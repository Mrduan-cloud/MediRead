# MediRead 前端 · Vue 3 + Vite

体检报告智能解读平台的 Web 前端,深色高级风(医疗科技青蓝),与后端**前后端分离**。

## 技术栈

- **Vue 3.5** + **TypeScript** + **Vite 5**
- **Naive UI**(深色主题 + 青蓝主色)
- **Pinia**(JWT 鉴权态,localStorage 持久化)+ **Vue Router**(路由守卫)
- **axios**(请求拦截器自动带 JWT;响应 401 自动登出)
- **ECharts**(历史趋势曲线)

## 本地开发

前置:后端已起在 `:8000`(见仓库根 [`README.md`](../README.md) 的「快速开始」)。

```bash
pnpm install
pnpm dev          # → http://localhost:5173,开发期 /api 自动代理到 :8000
```

演示账号:`demo-001` / `mediread2024`(后端 `scripts.seed` 已灌入一份体检报告,登录即可解读)。

## 页面

| 路由       | 说明                                                                              |
| ---------- | --------------------------------------------------------------------------------- |
| `/login`   | 登录 / 注册,演示账号一键填充                                                      |
| `/report`  | **报告解读**(主):上传图片/PDF → PaddleOCR 解析 → 结构化指标 → AI 解读(风险分级 + 联合分析 + 证据引用) |
| `/history` | **历史趋势**:同一指标随多次报告的变化曲线(ECharts)                              |

## 构建

```bash
pnpm build        # vue-tsc 类型检查 + vite build → dist/
```

生产可由后端 StaticFiles 或 nginx 托管 `dist/`。

## 设计说明

视觉沿用 MediRead 已验证的深色语言(近黑底 `#0a0a0a` + cyan 顶部辉光);风险四级配色(绿 → 黄 → 橙 → 红)与后端 `app/agents/interpreter/risk_grading.py` 的 `RiskLevel` 严格对齐。前端为 AI 辅助开发的演示层,工程重心在后端 OCR / RAG / 风险分级链路。
