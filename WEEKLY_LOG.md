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

## W04 · 2026-06-15 → 2026-06-21 · 主项目（MediRead RAG 与医学知识库）

> 对应简历：「医学解读 Agent · 医学知识库 RAG（BM25 + BGE + RRF + Cross-Encoder）」
> 本周角色：MediRead 当主项目（周一/三/五/六），NutriCore / MemoMate 周二/周四轮值。
> 实际节奏：W04 日任务在数个工作时段内前移做完，本节按 plan 日期归档。

### 这周做了什么

| 日期 | 项目 · PR | 内容 |
|---|---|---|
| 6/15 | MediRead `#18` | 补齐 KB **尿常规 + 肾功能**面板（6 面板齐备，闭合 README 声称却缺的欠账）；`test_kb_docs.py` 文档结构守护进 CI |
| 6/16 | MemoMate `#10` (+`#11/#12/#13`) | **weather_cn** server（wttr.in，stdlib 零依赖、免 key）；实网 debug 发现 lang_zh 常装英文 → 本地 WWO 码表出中文；payload 形状漂移加固；文档索引对齐 |
| 6/17 | MediRead `#20` | KB 索引进 `medical_kb`（带 metadata + BM25 jsonl）。**实证挖出 2 个真 bug**：① collection 反复灌库堆积陈旧数据（auto_id 追加,127 行 vs 应 48）污染 RRF；② `app/rag/__init__` eager import 拖垮 CI 轻量环境。修：幂等灌库 `recreate=True` + RRF 同-run 去重 + `__init__` 瘦身 |
| 6/18 | NutriCore `#25` | meal_plan 真实管线 recall@5 评测（接 `retrieve_plan_evidence`）+ top-1 判别守卫；顺修同款 auto_id 陈旧数据（26→13 行） |
| 6/19+6/20 | MediRead `#22` | interpreter 检索分层评测：`app/evaluation/retrieval_eval.py`（recall@k/top1/mrr 纯函数进 CI）+ live 集成（11 医学 gold/6 面板）固化 hybrid recall@5 + 精排不丢窗口 |
| review 修复 | NutriCore `#24/#26` · MediRead `#21` | FC 工具接入 consult + BMR 去重 + 清死代码；两仓 **BM25 缓存 re-ingest 后失效**（`reload_indices()`）+ `count_entities` 去 flush |

### 现状

- ✅ MediRead RAG 全链路就位：KB（6 面板）→ `medical_kb` 索引 → hybrid（BM25+BGE+RRF）→ Cross-Encoder 精排 → interpreter 取证；recall@5=1.0 实测固化。
- ✅ 灌库一致性三处缺口（陈旧数据 / RRF 重复累加 / BM25 缓存陈旧）全堵上，均有回归测试守护。
- 🟡 跟进任务挂着：medical_kb 上 Cross-Encoder 负增益，待 KB 规模化复评。
- 🟡 W04 重头戏 interpreter 推理 / 风险分级链路（react_chain ReAct + risk_grading）按 v4 计划在 **W07** 深做。

### 收获

1. **「灌完库必须做检索复验」**：本周第 N 次撞上 `auto_id + insert ≠ upsert` 的陈旧堆积——"upserted 48 chunks"的成功日志完全掩盖库里 127 行脏数据。两仓已上 `recreate=True` 幂等灌库根治 + RRF 去重 + BM25 缓存失效三道防线。
2. **诚实负结果 > 假增益**：6 文档种子 KB 上 RRF 已分得很开，Cross-Encoder 反而把 top-1 从 0.909 拉到 0.727。选择**如实记录 + 只固化真实成立的契约（召回完整 + 精排不丢窗口）+ 挂跟进任务**，而非虚报"精排提升"。简历/面试里这比假装有用可信得多。
3. **重型 RAG 也能被持续守护**：评测分层 = 纯函数指标进 CI（算法正确性）+ live 集成跑真管线（skip 守卫，需 Milvus/重权重）。重依赖不该是"测不了"的借口。
4. **环境坑**：PowerShell `Get-Content|Set-Content` 默认 GBK，往返把 ci.yml 中文注释写成乱码——改含中文的文件一律走 Edit 工具，不用 Get/Set-Content。

### 下周预告 · W05（06/22–06/28）· NutriCore 已建能力固化

主项目切回 **NutriCore**，把"demo 冲刺"期建掉的能力补测固化：
- 6/22 `test(meal_plan)`：营养方案 RAG + generator 端到端测试（证据引用必带 KB 来源）⭐⭐⭐
- 6/24 `feat(risk_screening/report)`：ReportLab PDF + MinIO 归档（补 W04 缺口）⭐⭐⭐
- 6/26 `feat(data_insight/security)`：三层隔离审计补测 ⭐⭐⭐
- 轮值：6/23 MediRead 中英文指标别名归一化 · 6/25 MemoMate github_trending

---
