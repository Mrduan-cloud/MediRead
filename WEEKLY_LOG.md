# WEEKLY_LOG · MediRead

> 每周复盘。Phase 1（90 天开局冲刺）按周轮转，周日把本周 `.scratch/daily-*` 汇总到这里。
> 本仓库是离职后基于公开技术栈重新 mock 的开源版本，不含任何前东家真实业务数据。

---

## W01 · 2026-05-25 → 2026-05-31 · 轮值副项目（依赖治理 + CI 健康）

> 对应简历：「报告解析 Agent · 多模板 OCR 解析与抽取」
> 本周角色：W01 主项目是 NutriCore，MediRead 作为轮值副项目在周二 / 周三推进。

### 这周做了什么

| 日期 | commit | 内容 |
|---|---|---|
| 5/26 Day2 | `8bfc702` / `4a28926` | 产品策略：冷分析 6 个潜在方向，决定**简历不动（保持 2 Agent 紧凑）**，把"健康管家 / 主动追踪 Agent"留到 Phase 2 GitHub 演进；README 加 Roadmap 章节（先写成 "Beyond Resume" 又按反馈改回正常 OSS 口吻——文案不过度解释） |
| 5/26 Day2 | `79557e9` / `5988d3b` | **PaddleOCR 依赖治理**：范围 pin 替代死 pin；`verify install in fresh venv` 暴露 **Python 3.13 没有 paddlepaddle 2.x wheel**（2.x 仅 cp38-cp312），用 `pyproject.toml` `requires-python = ">=3.11,<3.13"` 把"运行时崩"提前为"安装时报错"；新建三步走 `scripts/verify-paddle-pins.sh`；self-review 抓出范围 pin 过松（2.8+ 移除 `show_log`，2.10 会破 ocr.py）→ 收紧 cap 到 `<2.8.0` |
| 5/27 Day3 | `188732d` / `5bee0a1` | verify 脚本改为从 requirements.txt 读 pin（不再硬编码）+ 加 `--smoke`（真装 + 构造 `PaddleOCR(...)` 验证 API 假设）；接进 CI，依赖兼容性从"开发自觉"升级为"机器强制红绿灯" |
| 5/27 Day3 | `2896203` | **清 5 天历史欠债**：发现 CI 自 5/22 起连红 8 次无人察觉（ruff 早期 fail，后续步骤从没跑过）。148 个 ruff 错里区分误报（104 个中文医学术语 `γ-谷氨酰转移酶` RUF001/2/3 + FastAPI Depends B008 + 有意 lazy import PLC0415 → ignore）与真问题（30 个 `ruff --fix` + `zip(strict=True)` + 1 处 `<` vs `<=` off-by-one）；`__init__.py` 改 PEP 562 lazy import 让纯逻辑测试不必拉满 langchain/paddleocr 栈。**CI 首次真正转绿** |
| 5/27 Day3 | `885f6a3` / `c43282f` | 加 `docker-build` CI job（`build-push-action` + gha cache，cold 27min→缓存后 11min）；本地 build 验证 image **7.29 GB**（vs W11 目标 <1.5 GB，差 5 倍，已记入 W11 backlog）；用 `dorny/paths-filter` 让 docs-only PR 30 秒绿掉 |

### 现状与缺口

- ✅ 依赖治理 + CI 健康 + Docker build gate 已就位
- 🚧 **OCR 本体尚未接**：`wire PaddleOCR with sample image + smoke test` 是 W02 Day1（6/1）任务——这正是本周报后紧接着要做的
- 🚧 Docker image 7.29 GB 过大（paddlepaddle 占 9 min 装载），多阶段瘦身留到 W11

### 收获

1. **"verify install in fresh venv" 是任务里隐藏 ⭐ 的关键**：plan 写 ⭐⭐，把验证写认真就挖到 Python 版本天花板这种真问题。
2. **dry-run 能 resolve ≠ 装上能 import + 调用**：`5988d3b` 修的就是这个 gap——`--smoke` 模式补上真装 + 构造调用。
3. **CI 红灯 → 不绕过，要根因**：5 天没人看的红灯，选择花 30 分钟清干净而不是 ignore。
4. **简历真实性 > 简历丰满度**：加"智能客服 Agent"听起来诱人，冷分析 6 方向只有 1 个真值得做，且留到 Phase 2，简历不动。

---
