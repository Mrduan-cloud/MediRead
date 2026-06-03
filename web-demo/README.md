# MediRead · Web Demo(演示模式纯前端)

面向 HR / 展示用的**纯前端**演示页:点开链接即可走完整流程 —— 上传报告 → OCR 解析动画 → 指标抽取表 → 4 级风险研判与就医建议。**无需后端**,数据为内置脱敏虚构样例,后端关着也完整可看。

> 真实解读链路(PaddleOCR 解析 · 版式识别 · 指标归一化 · RAG 知识库 · 风险分级)在主仓库后端;本页只做 UX 展示,临床问题以线下医生诊断为准。

## 技术栈

- **Next.js 14**(App Router)+ **TypeScript** + **Tailwind CSS**
- **Geist** 字体(Vercel 设计语言)· 深色极简、手写组件、零 UI 库依赖
- `output: "export"` → 纯静态产物,可部署到 **Vercel / Cloudflare Pages / 任意静态托管**

## 本地开发

```bash
pnpm install
pnpm dev      # http://localhost:3000
pnpm build    # 类型检查 + 静态导出到 out/
```

## 部署到 Vercel

1. New Project → 选本仓库。
2. **Root Directory** 设为 `web-demo`。
3. Framework 自动识别为 Next.js,默认命令即可(无需环境变量)。
4. Deploy → 得到公网链接。

> 这是「演示模式」:样例数据内置在前端(`lib/samples.ts`)。若日后要接真实后端(如本机 docker 栈 + Cloudflare Tunnel),再加一个「真实模式」开关指向后端 URL 即可。

## 数据来源

`lib/samples.ts` 中 3 份样例(血常规 / 血脂 / 肝功能)覆盖「关注观察 / 建议复查 / 建议就医」三档风险,**全部为虚构脱敏数据,无任何真实个人或医院信息**。
