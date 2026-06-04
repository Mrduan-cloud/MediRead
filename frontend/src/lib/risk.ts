// 风险分级色板 —— 与后端 app/agents/interpreter/risk_grading.py 的 RiskLevel 对齐。
// 四级风险 + 正常,深色底上的高对比配色(医疗语义:绿→黄→橙→红 递进)。

export interface TierStyle {
  color: string;
  bg: string;
  border: string;
}

// 严重度从低到高排序,用于计算「整体最高风险」
export const TIER_ORDER = ["正常", "轻度偏离", "关注观察", "建议复查", "建议就医"] as const;

export const TIER_STYLES: Record<string, TierStyle> = {
  正常: { color: "#34d399", bg: "rgba(52, 211, 153, 0.10)", border: "rgba(52, 211, 153, 0.30)" },
  轻度偏离: { color: "#a3e635", bg: "rgba(163, 230, 53, 0.10)", border: "rgba(163, 230, 53, 0.28)" },
  关注观察: { color: "#fbbf24", bg: "rgba(251, 191, 36, 0.12)", border: "rgba(251, 191, 36, 0.30)" },
  建议复查: { color: "#fb923c", bg: "rgba(251, 146, 60, 0.12)", border: "rgba(251, 146, 60, 0.30)" },
  建议就医: { color: "#f87171", bg: "rgba(248, 113, 113, 0.13)", border: "rgba(248, 113, 113, 0.34)" },
};

const FALLBACK: TierStyle = TIER_STYLES["关注观察"];

export function tierStyle(tier: string): TierStyle {
  return TIER_STYLES[tier] ?? FALLBACK;
}

// 一组分级中取最严重的一档,用于结果页顶部的整体结论
export function worstTier(tiers: string[]): string {
  let idx = 0;
  for (const t of tiers) {
    const i = TIER_ORDER.indexOf(t as (typeof TIER_ORDER)[number]);
    if (i > idx) idx = i;
  }
  return TIER_ORDER[idx];
}
