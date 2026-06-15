"""就医分级 + 生活方式建议 —— 确定性、可单测的临床红线层。

react_chain 的 LLM 负责「解读异常指标的可能含义」,但**建议**这一步刻意不全交给 LLM:
医学场景里「给出用药/诊断」是红线。本模块只产出三类**安全**内容:

  1. 就医分级措辞(由 TriageLevel 确定性映射);
  2. 饮食/运动/作息建议(按联合信号或指标类别选预置安全文案,绝不含药物/剂量);
  3. 固定免责声明。

并强制两条红线:
  - **危急值 / 建议就医档 / 未接地** → 强制升级到至少「专科」并冠以「建议就医」;
  - LLM 自由文本若命中**用药/诊断**结构特征(剂量、处方、确诊…)→ 丢弃该自由文本,
    回退到确定性安全建议(`violates_red_line`)。
"""
from __future__ import annotations

import re

from app.agents.interpreter.risk_grading import IndicatorRisk, RiskLevel, TriageLevel

DISCLAIMER = "本解读基于体检指标的统计偏离,仅供参考,不构成诊断或用药建议,具体请遵医嘱。"

# 就医分级 → 患者向措辞(确定性)
_TRIAGE_PHRASE = {
    TriageLevel.NONE: "暂无需专门就医,保持健康生活方式,按常规体检随访即可。",
    TriageLevel.GENERAL: "建议至全科/内科门诊就诊,结合临床进一步评估。",
    TriageLevel.SPECIALIST: "建议尽快至相关专科门诊就诊评估。",
    TriageLevel.EMERGENCY: "该指标已达危急范围,建议立即就医/急诊。",
}

# 联合信号 / 指标类别 → 预置安全生活方式建议(只含饮食运动作息,绝不含药物)
_LIFESTYLE_BY_PATTERN = {
    "liver_injury": "限酒戒酒、规律作息、避免自行服用可能伤肝的药物,饮食清淡均衡。",
    "dyslipidemia": "低脂低糖饮食、增加有氧运动、控制体重,减少油炸与动物内脏摄入。",
    "anemia": "均衡膳食、适量增加富铁食物(瘦肉、动物肝、深色蔬菜),保证休息。",
}
_LIFESTYLE_BY_KEYWORD = [
    (("血糖", "葡萄糖", "糖化"), "控制精制糖与主食总量、规律有氧运动、监测体重与血糖。"),
    (("肌酐", "尿素", "eGFR", "尿酸", "肾小球"), "适度控盐控蛋白、避免肾毒性药物、多饮水,规律复查肾功能。"),
    (("胆固醇", "甘油三酯", "脂蛋白"), "低脂低糖饮食、增加有氧运动、控制体重。"),
    (("转氨酶", "谷氨酰", "胆红素"), "限酒、规律作息、避免自行用药,饮食清淡。"),
]
_LIFESTYLE_DEFAULT = "保持均衡饮食、规律运动与作息,避免烟酒,按医嘱定期复查。"

# 用药/诊断红线:剂量单位、处方/服药动作、确诊式断言。命中即视为越界。
# 剂量只认**药物专属**单位(mg/µg/IU/片/粒/剂/丸…),刻意不收 g / ml —— 它们更常出现在
# 饮食/饮水建议里(「每天 2000ml 水」「50g 蛋白质」),收了会把安全建议误判为越界;
# 真·用药多半带专属单位或下方的用药动作词,不会漏。
_RED_LINE_RE = re.compile(
    r"\d+\s*(?:mg|mcg|µg|ug|IU|片|粒|剂|丸)"                       # 药物专属剂量
    r"|服用|口服|静滴|肌注|输液|处方|开药|停药|换药|加量|减量|遵医嘱服"  # 用药动作
    r"|确诊|诊断为|患有|罹患",                                       # 诊断式断言
    re.IGNORECASE,
)


def violates_red_line(text: str) -> bool:
    """文本是否命中用药/诊断红线(用于决定是否丢弃 LLM 自由文本)。"""
    return bool(_RED_LINE_RE.search(text or ""))


def triage_phrase(triage: TriageLevel) -> str:
    return _TRIAGE_PHRASE.get(triage, _TRIAGE_PHRASE[TriageLevel.GENERAL])


def lifestyle_advice(indicator: str, joint_patterns: list[str] | None = None) -> str:
    """按联合信号优先、否则按指标关键词、再否则默认,给确定性安全建议。"""
    for pat in joint_patterns or []:
        if pat in _LIFESTYLE_BY_PATTERN:
            return _LIFESTYLE_BY_PATTERN[pat]
    for keywords, advice in _LIFESTYLE_BY_KEYWORD:
        if any(k in indicator for k in keywords):
            return advice
    return _LIFESTYLE_DEFAULT


def _escalate(triage: TriageLevel) -> TriageLevel:
    """红线升级:至少升到专科。"""
    order = [TriageLevel.NONE, TriageLevel.GENERAL, TriageLevel.SPECIALIST, TriageLevel.EMERGENCY]
    return triage if order.index(triage) >= order.index(TriageLevel.SPECIALIST) else TriageLevel.SPECIALIST


def build_advice(
    risk: IndicatorRisk,
    joint_patterns: list[str] | None = None,
    grounded: bool = True,
    llm_lifestyle: str | None = None,
) -> dict:
    """汇总安全建议。

    Args:
        risk: 该指标的风险分级结果。
        joint_patterns: 命中的联合信号 pattern(如 ["liver_injury"])。
        grounded: 该条解读是否通过引用守卫;未接地则强制就医兜底。
        llm_lifestyle: LLM 生成的生活方式文本;仅在接地且不越红线时采用,否则用确定性文案。

    Returns:
        {triage, triage_advice, lifestyle, disclaimer, escalated}。
    """
    triage = risk.triage
    escalated = False

    # 红线①:危急值 / 建议就医档 / 未接地 → 强制升级 + 冠以「建议就医」
    if risk.is_critical or risk.risk_level == RiskLevel.SEEK_CARE or not grounded:
        triage = _escalate(triage)
        escalated = True

    phrase = triage_phrase(triage)
    if escalated and not grounded and not risk.is_critical and risk.risk_level != RiskLevel.SEEK_CARE:
        # 仅因「未接地」升级:措辞说明原因,避免夸大风险
        phrase = "该指标未能在知识库中找到充分依据,建议就医由医生进一步确认。"

    # 红线②:LLM 自由文本越界(用药/诊断)或未接地 → 弃用,改确定性安全建议
    if llm_lifestyle and grounded and not violates_red_line(llm_lifestyle):
        lifestyle = llm_lifestyle
    else:
        lifestyle = lifestyle_advice(risk.indicator, joint_patterns)

    return {
        "triage": triage.value,
        "triage_advice": phrase,
        "lifestyle": lifestyle,
        "disclaimer": DISCLAIMER,
        "escalated": escalated,
    }
