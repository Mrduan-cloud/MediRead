"""引用守卫 —— 校验 LLM 生成的解读是否「真的接地」在检索证据上。

医学解读里,「带了引用」和「引用是真的」是两回事:LLM 会编造 `[doc_id:chunk_id]`,
或干脆不带引用就下结论。本模块把生成文本里的引用标记抽出来,逐个对照**本轮实际检索到的
证据集合**:

  - 编造的引用(指向不存在的 doc/chunk)→ 记为 hallucinated;
  - 一条「必须接地」的字段若没有任何**有效**引用 → 该字段判为未接地。

整模块是纯函数(不碰网络/LLM),既能离线单测,又被 react_chain 的「接地驱动有界重试」
循环当作停止条件:接地不足就带着缺口重检索、重试,至多 3 步。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 引用形如 [doc_id:chunk_id];doc_id / chunk_id 不含方括号与冒号即可。
_CITATION_RE = re.compile(r"\[([^\[\]:]+):([^\[\]:]+)\]")


def extract_citations(text: str) -> list[str]:
    """从文本里抽出所有 `doc_id:chunk_id` 引用键(去重保序)。"""
    seen: dict[str, None] = {}
    for doc_id, chunk_id in _CITATION_RE.findall(text or ""):
        seen.setdefault(f"{doc_id.strip()}:{chunk_id.strip()}", None)
    return list(seen)


def allowed_keys(evidence: list[dict]) -> set[str]:
    """本轮检索证据允许的引用键集合。"""
    out: set[str] = set()
    for e in evidence or []:
        doc_id, chunk_id = e.get("doc_id"), e.get("chunk_id")
        if doc_id is not None and chunk_id is not None:
            out.add(f"{doc_id}:{chunk_id}")
    return out


@dataclass
class FieldGrounding:
    field_name: str
    cited: list[str] = field(default_factory=list)         # 文本里出现的全部引用
    valid: list[str] = field(default_factory=list)         # ∈ 证据集
    hallucinated: list[str] = field(default_factory=list)  # ∉ 证据集(编造)

    @property
    def has_citation(self) -> bool:
        return bool(self.cited)

    @property
    def grounded(self) -> bool:
        """有至少一条有效引用、且没有编造引用,才算接地。"""
        return bool(self.valid) and not self.hallucinated


def check_field(field_name: str, text: str, allowed: set[str]) -> FieldGrounding:
    cited = extract_citations(text)
    valid = [c for c in cited if c in allowed]
    hallucinated = [c for c in cited if c not in allowed]
    return FieldGrounding(field_name=field_name, cited=cited, valid=valid, hallucinated=hallucinated)


@dataclass
class GuardResult:
    fields: dict[str, FieldGrounding]
    required: tuple[str, ...]

    @property
    def grounded(self) -> bool:
        """所有「必须接地」字段都存在且接地,才整体通过。

        注意必须先判 `f in self.fields`:缺字段视为未接地(否则 `all([])` 会把
        「必填字段整个缺失」误判为通过)。
        """
        return all(f in self.fields and self.fields[f].grounded for f in self.required)

    @property
    def ungrounded_fields(self) -> list[str]:
        return [f for f in self.required if f in self.fields and not self.fields[f].grounded]

    @property
    def hallucinated(self) -> list[str]:
        out: list[str] = []
        for fg in self.fields.values():
            out.extend(fg.hallucinated)
        return out


# 默认「必须接地」的字段:解读是事实性主张,必须有据;生活方式/就医建议由 medical_advice
# 的确定性映射兜底,这里只校验、不强制(但仍会报告其接地情况)。
DEFAULT_REQUIRED = ("interpretation",)


def guard(
    generated: dict[str, str],
    evidence: list[dict],
    required: tuple[str, ...] = DEFAULT_REQUIRED,
) -> GuardResult:
    """对一组生成字段做引用守卫。

    Args:
        generated: 字段名 → 文本(如 {"interpretation": "...", "lifestyle": "..."})。
        evidence: 本轮检索到的证据(含 doc_id / chunk_id)。
        required: 必须接地的字段名;缺一不可则整体不通过。

    Returns:
        GuardResult:.grounded 供有界重试循环当停止条件;.hallucinated / .ungrounded_fields 供日志与重检索定位缺口。
    """
    allowed = allowed_keys(evidence)
    fields = {name: check_field(name, text, allowed) for name, text in (generated or {}).items()}
    return GuardResult(fields=fields, required=required)
