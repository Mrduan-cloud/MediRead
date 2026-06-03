// 演示模式数据 —— 全部为脱敏、虚构样例(无任何真实个人 / 医院信息),仅作 UX 展示。
// 真实链路(PaddleOCR 解析 + 版式识别 + 指标归一化 + RAG + 风险分级)见后端仓库。

export type IndicatorStatus = "normal" | "high" | "low";
export type RiskTier = "正常" | "轻度偏离" | "关注观察" | "建议复查" | "建议就医";

export interface Indicator {
  name: string;
  value: string;
  unit: string;
  refRange: string;
  status: IndicatorStatus;
}

export interface Finding {
  indicator: string;
  note: string;
  tier: RiskTier;
}

export interface SampleReport {
  id: string;
  title: string;
  category: string;
  meta: { hospital: string; sampledAt: string; patient: string };
  indicators: Indicator[];
  interpretation: {
    overallTier: RiskTier;
    summary: string;
    findings: Finding[];
    advice: string;
  };
}

export const SAMPLES: SampleReport[] = [
  {
    id: "cbc",
    title: "血常规检验报告",
    category: "血常规 · CBC",
    meta: { hospital: "示例市人民医院(样例)", sampledAt: "2026-05-20", patient: "张三 · 男 · 35" },
    indicators: [
      { name: "白细胞 WBC", value: "11.2", unit: "10⁹/L", refRange: "3.5–9.5", status: "high" },
      { name: "中性粒细胞% NEUT%", value: "78", unit: "%", refRange: "40–75", status: "high" },
      { name: "红细胞 RBC", value: "4.8", unit: "10¹²/L", refRange: "4.3–5.8", status: "normal" },
      { name: "血红蛋白 Hb", value: "152", unit: "g/L", refRange: "130–175", status: "normal" },
      { name: "血小板 PLT", value: "245", unit: "10⁹/L", refRange: "125–350", status: "normal" },
    ],
    interpretation: {
      overallTier: "关注观察",
      summary: "白细胞与中性粒细胞比例轻度升高,常见于近期细菌感染 / 炎症反应,其余血象正常。",
      findings: [
        { indicator: "白细胞 WBC", note: "11.2 高于上限 9.5,提示可能存在感染或炎症。", tier: "关注观察" },
        { indicator: "中性粒细胞% NEUT%", note: "78% 略高,与 WBC 升高方向一致。", tier: "轻度偏离" },
      ],
      advice:
        "多为一过性炎症反应。建议结合是否有发热、咳嗽等症状观察 3–5 天;若持续升高或伴明显不适,复查血常规并至全科 / 内科就诊。",
    },
  },
  {
    id: "lipid",
    title: "血脂四项检验报告",
    category: "血脂 · Lipid Panel",
    meta: { hospital: "示例市人民医院(样例)", sampledAt: "2026-05-20", patient: "李四 · 男 · 48" },
    indicators: [
      { name: "总胆固醇 TC", value: "6.8", unit: "mmol/L", refRange: "< 5.2", status: "high" },
      { name: "甘油三酯 TG", value: "2.4", unit: "mmol/L", refRange: "< 1.7", status: "high" },
      { name: "低密度脂蛋白 LDL-C", value: "4.6", unit: "mmol/L", refRange: "< 3.4", status: "high" },
      { name: "高密度脂蛋白 HDL-C", value: "0.9", unit: "mmol/L", refRange: "> 1.0", status: "low" },
    ],
    interpretation: {
      overallTier: "建议复查",
      summary: "多项血脂指标超出参考范围,LDL-C 偏高且 HDL-C 偏低,提示动脉粥样硬化 / 心血管风险升高。",
      findings: [
        { indicator: "低密度脂蛋白 LDL-C", note: "4.6 明显高于 3.4,是心血管风险的核心指标。", tier: "建议复查" },
        { indicator: "总胆固醇 TC", note: "6.8 高于 5.2。", tier: "关注观察" },
        { indicator: "高密度脂蛋白 HDL-C", note: "0.9 低于下限,保护性胆固醇不足。", tier: "关注观察" },
      ],
      advice:
        "建议 1–2 周后空腹复查血脂以确认,同步控制饮食(减少饱和脂肪 / 精制糖)、规律有氧运动;如复查仍偏高,建议心内科评估是否需要药物干预。",
    },
  },
  {
    id: "liver",
    title: "肝功能检验报告",
    category: "肝功能 · LFT",
    meta: { hospital: "示例市人民医院(样例)", sampledAt: "2026-05-20", patient: "王五 · 男 · 41" },
    indicators: [
      { name: "谷丙转氨酶 ALT", value: "156", unit: "U/L", refRange: "9–50", status: "high" },
      { name: "谷草转氨酶 AST", value: "98", unit: "U/L", refRange: "15–40", status: "high" },
      { name: "γ-谷氨酰转移酶 GGT", value: "210", unit: "U/L", refRange: "10–60", status: "high" },
      { name: "总胆红素 TBIL", value: "28", unit: "μmol/L", refRange: "3.4–20.5", status: "high" },
    ],
    interpretation: {
      overallTier: "建议就医",
      summary: "转氨酶(ALT/AST)与 GGT 显著升高,总胆红素轻度升高,提示存在肝细胞损伤,需进一步排查病因。",
      findings: [
        { indicator: "谷丙转氨酶 ALT", note: "156 约为上限 3 倍,肝细胞损伤较明确。", tier: "建议就医" },
        { indicator: "γ-谷氨酰转移酶 GGT", note: "210 显著升高,常与胆汁淤积 / 饮酒相关。", tier: "建议就医" },
        { indicator: "总胆红素 TBIL", note: "28 轻度升高,需结合直接 / 间接胆红素判断。", tier: "关注观察" },
      ],
      advice:
        "肝酶显著升高,建议尽快至肝病科 / 消化内科就诊,完善肝炎病毒、肝胆影像学等检查;近期避免饮酒及肝毒性药物。本提示不构成诊断。",
    },
  },
];
