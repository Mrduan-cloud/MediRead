"""多指标联合分析（方向感知）。

避免「单指标偏离一律打高风险」误判，按已知医学规则做联合判定。

每条规则都标注：
  - **预期异常方向**（high / low）：方向感知可避免「ALT 偏低也判肝损伤」「血红蛋白
    偏高也判贫血」这类方向错配的误命中；
  - **接地面板**（panel，即 KB doc_id）：每条联合结论都能在对应面板文档里找到依据，
    同时为将来「面板感知检索」留素材（指标 → 面板映射）。

`detect_joint_signals` 对旧调用（只传指标名、不带方向）保持向后兼容：不传 directions
时不做方向校验，行为同历史版本。
"""
from __future__ import annotations

from dataclasses import dataclass

# 异常方向归一化：报告 / 抽取 / 测试里方向写法不一（high/low、偏高/偏低、↑/↓），
# 统一成 'high' / 'low'。生产 extractor 写入的是 'high' / 'low'（见 parser/extractor.py）。
_HIGH_TOKENS = ("偏高", "升高", "增高", "高")
_LOW_TOKENS = ("偏低", "降低", "减低", "低")


def normalize_direction(direction: str | None) -> str | None:
    """把异常方向的多种写法归一为 'high' / 'low'；无法判定返回 None。"""
    if not direction:
        return None
    dl = direction.strip().casefold()
    if dl in ("high", "h", "↑"):
        return "high"
    if dl in ("low", "l", "↓"):
        return "low"
    # 中文写法按子串判定（'偏高' 含 '高'，不会误命中拉丁文 'high'）
    if any(t in direction for t in _HIGH_TOKENS):
        return "high"
    if any(t in direction for t in _LOW_TOKENS):
        return "low"
    return None


@dataclass
class JointSignal:
    pattern: str                       # 例如 "liver_injury"
    matched_indicators: list[str]
    hint: str                          # 联合判定结论
    direction: str | None = None       # 该联合模式预期的异常方向（high / low）
    panel: str | None = None           # 接地面板（doc_id），面板感知检索 / 展示的素材


# 联合规则（生产可外置 YAML / 规则引擎）。指标名须为 normalizer 归一化后的标准名
# （见 app/data/synonyms.json），否则永远不命中。每条均有 KB 面板文档接地。
JOINT_RULES: list[dict] = [
    {
        "pattern": "liver_injury",
        "require_all": ["丙氨酸氨基转移酶", "天门冬氨酸氨基转移酶", "γ-谷氨酰转移酶"],
        "direction": "high",
        "panel": "liver_function_panel",
        "hint": "ALT + AST + GGT 三项同步偏高，提示肝细胞 / 胆道系统受损可能，建议肝胆超声 + 消化内科评估。",
    },
    {
        "pattern": "hypercholesterolemia",
        "require_all": ["总胆固醇", "低密度脂蛋白胆固醇"],
        "direction": "high",
        "panel": "lipid_glucose_panel",
        "hint": "总胆固醇与低密度脂蛋白胆固醇同步升高，提示高胆固醇血症倾向，心血管风险升高。",
    },
    {
        "pattern": "dyslipidemia",
        "require_any": ["总胆固醇", "甘油三酯", "低密度脂蛋白胆固醇"],
        "direction": "high",
        "panel": "lipid_glucose_panel",
        "hint": "血脂相关指标偏高，提示血脂代谢紊乱倾向。",
    },
    {
        "pattern": "renal_impairment",
        "require_all": ["肌酐", "尿素氮"],
        "direction": "high",
        "panel": "kidney_function_panel",
        "hint": "血肌酐与尿素氮同步升高，提示肾小球滤过功能下降可能，建议结合 eGFR 评估、肾内科复查。",
    },
    {
        "pattern": "dysglycemia",
        "require_any": ["空腹血糖", "糖化血红蛋白"],
        "direction": "high",
        "panel": "lipid_glucose_panel",
        "hint": "空腹血糖 / 糖化血红蛋白偏高，提示糖代谢异常倾向，建议复查并评估糖尿病风险。",
    },
    {
        "pattern": "anemia",
        "require_all": ["血红蛋白", "红细胞计数"],
        "direction": "low",
        "panel": "blood_routine",
        "hint": "血红蛋白与红细胞计数同步偏低，提示贫血倾向，建议结合 MCV / MCH 判断类型。",
    },
]


def detect_joint_signals(
    abnormal_names: list[str],
    directions: dict[str, str | None] | None = None,
) -> list[JointSignal]:
    """检测命中的多指标联合模式。

    Args:
        abnormal_names: 异常指标的标准名列表。
        directions: 可选 ``{指标名 -> 异常方向}``。提供时启用**方向校验**——参与某规则
            的指标方向须与规则预期方向一致才算命中（避免「ALT 偏低也判肝损伤」）。为
            ``None``（历史调用）则不校验方向，保持向后兼容。

    Note:
        启用方向校验时，方向**未知**（``None`` 或无法归一）的指标按「不匹配」处理 →
        会从其本可命中的联合规则中被剔除（保守不误报）。因此调用方应保证每个异常指标
        都带 high / low 方向：当前 OCR 抽取路径 ``parser/extractor._mark_abnormal`` 在
        置 ``abnormal=True`` 的同时必写 ``abnormal_direction``，满足此契约；若日后引入
        「设异常但不带方向」的指标来源，需在该处补方向，否则联合检测会静默 under-fire。
    """
    name_set = set(abnormal_names)
    norm_dir = (
        {n: normalize_direction(d) for n, d in directions.items()}
        if directions is not None
        else None
    )

    def _dir_ok(name: str, want: str | None) -> bool:
        # 不校验方向（未提供 directions，或规则无方向要求）→ 放行；
        # 校验时方向须确切匹配，未知方向（None）视为不匹配，保守不误报。
        if norm_dir is None or want is None:
            return True
        return norm_dir.get(name) == want

    signals: list[JointSignal] = []
    for rule in JOINT_RULES:
        want = rule.get("direction")
        if "require_all" in rule:
            req = rule["require_all"]
            if set(req).issubset(name_set) and all(_dir_ok(n, want) for n in req):
                signals.append(
                    JointSignal(rule["pattern"], list(req), rule["hint"], want, rule.get("panel"))
                )
        elif "require_any" in rule:
            matched = sorted(n for n in (name_set & set(rule["require_any"])) if _dir_ok(n, want))
            if matched:
                signals.append(
                    JointSignal(rule["pattern"], matched, rule["hint"], want, rule.get("panel"))
                )
    return signals
