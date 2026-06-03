<script setup lang="ts">
import { computed } from "vue";
import { tierStyle, worstTier } from "@/lib/risk";

interface Finding {
  indicator: string;
  value?: number | string;
  ref_range?: string | null;
  risk_level?: string;
  triage?: string;
  is_critical?: boolean;
  citations?: string[];
  interpretation?: string;
  lifestyle?: string;
  triage_advice?: string;
  error?: string;
}
interface JointSignal {
  pattern?: string;
  description?: string;
  [k: string]: unknown;
}
interface Result {
  joint_signals?: JointSignal[];
  interpretations?: Finding[];
}

const props = defineProps<{ result: Result }>();

const findings = computed<Finding[]>(() => props.result?.interpretations ?? []);
const joints = computed<JointSignal[]>(() => props.result?.joint_signals ?? []);

const overall = computed(() => worstTier(findings.value.map((f) => f.risk_level || "正常")));
const overallStyle = computed(() => tierStyle(overall.value));

const JOINT_LABELS: Record<string, string> = {
  liver_injury: "肝细胞损伤组合",
  anemia: "贫血组合",
  dyslipidemia: "血脂异常组合",
  renal: "肾功能异常组合",
};
function jointLabel(s: JointSignal): string {
  return JOINT_LABELS[s.pattern || ""] || s.description || s.pattern || "联合信号";
}
</script>

<template>
  <div class="result">
    <!-- 整体结论 -->
    <div
      class="banner"
      :style="{
        background: overallStyle.bg,
        borderColor: overallStyle.border,
        color: overallStyle.color,
      }"
    >
      <span class="b-dot" :style="{ background: overallStyle.color }" />
      <span class="b-text">
        整体结论:<strong>{{ overall }}</strong>
        <span class="b-sub">· 共 {{ findings.length }} 项异常指标</span>
      </span>
    </div>

    <!-- 联合信号 -->
    <div v-if="joints.length" class="joints">
      <span class="j-label">多指标联合信号</span>
      <span v-for="(s, i) in joints" :key="i" class="j-chip">⚕ {{ jointLabel(s) }}</span>
    </div>

    <!-- 逐指标解读卡片 -->
    <div class="cards">
      <article
        v-for="(f, i) in findings"
        :key="i"
        class="card"
        :style="{ borderColor: tierStyle(f.risk_level || '正常').border }"
      >
        <header class="c-head">
          <div class="c-title">
            <span class="c-name">{{ f.indicator }}</span>
            <span v-if="f.value !== undefined" class="c-val">
              {{ f.value }}<span v-if="f.ref_range" class="c-ref"> (参考 {{ f.ref_range }})</span>
            </span>
          </div>
          <div class="c-tags">
            <span
              class="c-badge"
              :style="{
                color: tierStyle(f.risk_level || '正常').color,
                background: tierStyle(f.risk_level || '正常').bg,
                borderColor: tierStyle(f.risk_level || '正常').border,
              }"
            >
              {{ f.risk_level || "—" }}
            </span>
            <span v-if="f.triage && f.triage !== '无需'" class="c-triage">就医:{{ f.triage }}</span>
            <span v-if="f.is_critical" class="c-critical">⚠ 危急值</span>
          </div>
        </header>

        <div v-if="f.error" class="c-error">该指标解读失败:{{ f.error }}</div>
        <template v-else>
          <p v-if="f.interpretation" class="c-block">{{ f.interpretation }}</p>
          <p v-if="f.lifestyle" class="c-block">
            <span class="c-tag">生活方式</span>{{ f.lifestyle }}
          </p>
          <p v-if="f.triage_advice" class="c-block">
            <span class="c-tag">就医建议</span>{{ f.triage_advice }}
          </p>
          <div v-if="f.citations && f.citations.length" class="c-cites">
            <span v-for="(c, ci) in f.citations" :key="ci" class="cite">[{{ c }}]</span>
          </div>
        </template>
      </article>
    </div>

    <p class="disclaimer">
      本结果由 AI 基于检验数值 + 知识库证据生成,仅供健康科普参考,不构成诊断,请以医生面诊为准。
    </p>
  </div>
</template>

<style scoped>
.result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 18px;
  border: 1px solid;
  border-radius: 12px;
  font-size: 15px;
}
.b-dot {
  width: 10px;
  height: 10px;
  border-radius: 9999px;
  flex: none;
  box-shadow: 0 0 12px currentColor;
}
.b-sub {
  opacity: 0.8;
  font-size: 13px;
  margin-left: 4px;
}
.joints {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.j-label {
  font-size: 12px;
  color: #64748b;
}
.j-chip {
  font-size: 13px;
  color: #c4b5fd;
  background: rgba(167, 139, 250, 0.12);
  border: 1px solid rgba(167, 139, 250, 0.3);
  border-radius: 9999px;
  padding: 3px 11px;
}
.cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.card {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 16px 18px;
  background: rgba(255, 255, 255, 0.025);
}
.c-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}
.c-name {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}
.c-val {
  font-family: ui-monospace, monospace;
  font-size: 14px;
  color: #94a3b8;
  margin-left: 8px;
}
.c-ref {
  color: #64748b;
}
.c-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.c-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 9999px;
  border: 1px solid;
}
.c-triage {
  font-size: 12px;
  color: #94a3b8;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 9999px;
  padding: 2px 9px;
}
.c-critical {
  font-size: 12px;
  font-weight: 700;
  color: #fca5a5;
  background: rgba(248, 113, 113, 0.14);
  border-radius: 9999px;
  padding: 2px 9px;
}
.c-block {
  font-size: 14px;
  line-height: 1.7;
  color: #cbd5e1;
  margin-top: 6px;
}
.c-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: #7dd3fc;
  background: rgba(56, 189, 248, 0.1);
  border-radius: 6px;
  padding: 1px 7px;
  margin-right: 8px;
}
.c-error {
  font-size: 13px;
  color: #fca5a5;
}
.c-cites {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.cite {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: #64748b;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 1px 6px;
}
.disclaimer {
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 12px;
}
</style>
