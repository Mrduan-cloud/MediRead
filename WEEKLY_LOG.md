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

## W07 · 2026-07-06 → 2026-07-12 · 主项目（MediRead Interpreter 推理 + 风险分级）

> 对应简历：「医学解读 Agent · ReAct 推理 · 多指标联合 · 风险分级 / 就医分级」
> 本周角色：MediRead 当主项目。完成驱动,本节按 plan 标称日期归档（实际在一个工作 session 内做完 + 真实栈 live 验证）。

### 这周做了什么

三连查先行：interpreter 其实**已大半实现**（risk_grading 4 级 + 危急值、joint_analysis 规则、react_chain 链路都在），真缺口是「**引用守卫 + ReAct 边界 + medical_advice 独立成层 + e2e golden**」,而非从零造。据此一个 PR（`#26`）补齐：

| 增量 | 内容 |
|---|---|
| `citation_guard.py`（新·纯逻辑） | 抽 `[doc_id:chunk_id]` 对照**本轮证据**校验,识别编造/未接地引用;当有界重试循环的停止条件。11 测试 |
| `react_chain` 重写 | 线性单趟 → **引用守卫驱动的有界重试** ReAct（max 3 步）:未接地→放宽检索（扩窗 4/8/12 + 带方向/联合信号）累积证据重试;三步仍不接地→**不输出未核验解读**,改安全降级文案 |
| `medical_advice.py`（新·纯逻辑） | 确定性**临床红线层**:只产就医分级 + 安全生活方式(饮食运动作息,绝不含药物/诊断)+ 免责;危急值/建议就医/未接地强制升级就医;LLM 自由文本命中用药/诊断特征即弃。16 测试 |
| risk_grading 测试补强 | WATCH/RECHECK 档、低侧偏离、非数值、无参考范围、0.6 边界 |
| e2e golden snapshot | monkeypatch 检索/LLM 跑完整链路钉确定性快照(接地+肝三联一步收尾 / 危急值兜底 / 始终未接地→重试 3 步+红线强制就医) |
| 工程 | `react_chain` 重型 RAG(pymilvus/sentence-transformers)+openai **惰性化** + LLM 走 `_llm_complete` 包装,使 golden 进 CI 轻量环境(allowlist + prometheus-client);「屏蔽重依赖子进程」验证可导入 |

合并后**重建 api 镜像做真实栈 live 验证**（真 Milvus medical_kb + 真 DeepSeek）。

### 现状

- ✅ interpreter 四件套就位:引用守卫 + 有界重试 ReAct + 临床红线建议 + golden;CI（lint-test/docker-build/changes）三绿,本地 121 passed。
- ✅ live 验证链路全通:解读文本医学上稳妥克制(无诊断/用药)、risk/triage 正确、肝三联命中、red-line 干净、守卫接受真实引用 grounded=True。
- 🟡 **live 发现「接地但跨面板引用」**:肝酶 ALT/AST 的引用指向了 `tumor_markers_panel`。引用守卫挡得住「编造」,挡不住「真实但语义不相关」——根因是 6 文档小 KB 上 Cross-Encoder 负增益致检索混入错面板 chunk,`grounded=True` 一步即停、有界重试没机会扩检索。已 spawn 跟进 `task_54b9677e`（面板感知检索 / 收紧接地判据,与既有 Cross-Encoder 负增益复评同源,等 KB 规模化再做）。

### 收获

1. **三连查省下重复造轮子**:动手前先盘清现状,发现 interpreter 已大半实现,把一周硬活精准收敛到「真缺口」(守卫/边界/红线/golden),而不是推倒重写。
2. **「ReAct」要诚实落地**:在「真全 ReAct 多步漫游」「纯线性还硬叫 ReAct」「接地驱动的有界重试」之间选了第三个——循环由引用守卫反馈驱动、有界 3 步、未接地不输出未核验结论。简历 bullet 名副其实,且面试能讲清「为什么这样克制」。
3. **临床红线交给确定性代码,不交给 LLM**:建议层只产安全三类内容,危急/未接地强制就医,LLM 越界文本即弃。医疗场景里「能不能给用药/诊断」不该赌模型自觉。
4. **惰性化让重模块的确定性测试也能进 CI**:延续 W04 的评测分层 / `__init__` 瘦身纪律,把 react_chain 的重依赖推到函数内,monkeypatch golden 就能在 CI 轻量环境守护整条链路。
5. **live 验证抓到 monkeypatch 测不出的问题**（本周最有价值）:「接地但跨面板引用」只有真栈 + 真 LLM 能暴露——确定性 golden 把检索/LLM 都打桩了,自然看不到检索混面板。延续 W04「诚实负结果 > 假增益」「别在 6 文档微 KB 上盲调」:如实记录 + spawn 跟进,不 hack quick-fix。**确定性测试保正确性,live 验证保真实性,两者缺一不可。**

### 下周预告 · W08（07/13–07/19）· MemoMate servers 扩充

主项目切到 **MemoMate**:落地 W06 主动留下的 `wechat_mp`（公开公众号文章解析,优先 stdlib 正则路线）/ `12306`（余票查询,需评估反爬与可验证性）等;副项目穿插 NutriCore 画像字段、MediRead `task_54b9677e` 面板感知检索（视 KB 规模化进度）。

---

## W10 · 2026-07-27 → 2026-08-02 · 主项目（MediRead 多指标联合分析深化）

> 对应简历：「医学解读 Agent · ReAct 推理 · 多指标联合 · 风险分级 / 就医分级」
> 本周角色：MediRead 当主项目（停滞仓轮到）。完成驱动,本节按 plan 标称日期归档（实际在一个工作 session 内做完 + 真实 seed 实证 + 两轮 code-review 收口）。

### 这周做了什么

三连查先行：盘清 git / repo / plan 后,interpreter 的真缺口 = `joint_analysis` 是最薄的一层（47 行 / 3 条规则 / **方向盲目**）；而「接地但跨面板错引」follow-up 的门槛（medical_kb 规模化）仍未满足 → 继续延后,本周聚焦联合分析本体。一个 PR（`#30`）收口：

| 增量 | 内容 |
|---|---|
| 方向感知 | 规则标注预期 high/low；`detect_joint_signals` 新增可选 `directions`,参与某规则的指标方向须与预期一致才命中 —— 抑制「ALT 偏低也判肝损伤」「血红蛋白偏高也判贫血」式方向错配。`normalize_direction` 兼容 high/low/偏高/偏低/↑↓,未知方向保守不报 |
| 扩规则 3→6 | liver_injury / **hypercholesterolemia(新)** / dyslipidemia / **renal_impairment(新)** / **dysglycemia(新)** / anemia,全部有 KB 面板文档接地；每条标注 `panel`（指标→面板映射） |
| 结论落指标 | 联合结论 `hint` 从只停报告级 `joint_signals` 回填到 per-indicator `joint_hints`,前端可在指标卡片展示参与的联合判定 |
| 顺手修 bug | `matched_indicators` 不再别名共享模块级 `JOINT_RULES`（改 `list(req)`）,加 mutation-safety 回归测试守护 |
| 测试 | `test_joint_analysis` 扩到 17 例（向后兼容 / 方向匹配 / 错配抑制 / 未知方向保守 / require_any 方向过滤 / 新规则 / 归一化 / 别名安全）+ e2e golden 加 `joint_hints` 落指标 |

合并前**真实 seed 数据实证**：`sample_indicators.json` 经 normalizer → `detect_joint_signals` 正确触发 liver_injury + hypercholesterolemia + dyslipidemia（方向皆 high）。

### 现状

- ✅ joint_analysis 从「集合包含判定」升级为「方向感知 + KB 接地」的联合判定；6 条规则覆盖肝 / 血脂 / 血糖 / 肾 / 血常规面板,向后兼容 `directions=None`。
- ✅ CI 三绿（lint-test / changes / docker-build）,17 单测 + golden 守护；经两轮 /code-review 收口（轮1 修 `interpretations[-1]` 脆弱耦合 → 分支内 `it` 变量；轮2 docstring 记隐式契约 + 别名回归测试）。
- 🟡 **「接地但跨面板错引」+ Cross-Encoder 负增益复评仍延后**：medical_kb 仍 6 文档,规模化门槛未满足。本周 `panel` 字段已为修法#1（面板感知检索）备料,但不动检索。
- 🧹 顺清 W04 老账：宙吊的 docker-compose / vite 未提交改动全部 revert（说明见收获 #2）。

### 收获

1. **三连查再次省下返工**：延续 W07,动手前先盘 git / repo / plan,精准定位 `joint_analysis` 是真缺口（而非从零造规则引擎）,也确认 off-panel 门槛未到、不盲动检索。
2. **删代码前先看它是否被产品叙事消费**（本周最大教训）：宙吊的「删 ollama」diff 看着像死代码清理,`git grep` 一查才发现 Ollama 是 MediRead「健康数据零外传」核心卖点（README / DEPLOYMENT / architecture / config 默认值全建立其上,DEPLOYMENT 明确禁止配置第三方云 LLM URL）。那份 diff 实为本机无 GPU 改用云 DeepSeek 的本地 dev 作物,提交会掀翻文档化架构 → 全 revert。**「看着像死代码」不是删除理由,先确认没有消费者（代码 + 文档 + 商业叙事）。**
3. **方向感知与 W07「接地但跨面板错引」同源**：W07 暴露「真实但语义不相关引用」,本质是检索相关性 + 接地判据强度；方向错配（ALT 偏低也判肝损伤）是同一类「字面命中但语义错」。顺手把指标→面板映射（`panel` 字段）编码,为将来面板感知检索铺路。
4. **恒开方向校验引入隐式契约,要显式记**：react_chain 现在总传 `directions`,使「被标异常但无方向」的指标静默退出联合检测。验证当前 `extractor._mark_abnormal` 保证 abnormal ⟹ 有方向,并把契约写进 docstring + 单测锁住——第二轮 review 才挖出的,确定性逻辑也有「隐式依赖上游数据形态」的坑。
5. **review 缺口分级决定走不走 /debug**：两轮 review 都是健壮性 / 契约 / 测试缺口（静态可证）,非运行期 e2e 隐患,故改完回归即可,未触发 /debug——与 W08/W09「有 e2e 隐患才 debug」一致,不为流程而流程。

### 下周预告 · W11（08/03–08/09）· MemoMate servers 扩充

主项目切到 **MemoMate**：按 W08 范式起手先评估候选（`12306` 余票 / `wechat_mp` 深化等）的反爬与可验证性,再定做哪个、怎么做（「有官方 API 才最干净」优先）。副项目穿插：MediRead off-panel（视 KB 规模化）、NutriCore 轮值。

---
