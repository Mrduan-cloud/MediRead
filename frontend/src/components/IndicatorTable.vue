<script setup lang="ts">
import { computed } from "vue";

export interface Indicator {
  name: string;
  value: number | string;
  unit?: string | null;
  ref_range?: string | null;
  abnormal?: boolean;
  abnormal_direction?: string | null;
}

const props = defineProps<{ indicators: Indicator[] }>();

const rows = computed(() => props.indicators ?? []);

function statusOf(ind: Indicator): { label: string; cls: string } {
  if (!ind.abnormal) return { label: "正常", cls: "ok" };
  const d = ind.abnormal_direction;
  if (d === "high") return { label: "偏高 ↑", cls: "high" };
  if (d === "low") return { label: "偏低 ↓", cls: "low" };
  return { label: "异常", cls: "high" };
}
</script>

<template>
  <div class="tbl-wrap">
    <table class="tbl">
      <thead>
        <tr>
          <th>指标</th>
          <th>结果</th>
          <th>参考范围</th>
          <th>状态</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(ind, i) in rows" :key="i" :class="{ abn: ind.abnormal }">
          <td class="name">{{ ind.name }}</td>
          <td class="val">
            {{ ind.value }}<span v-if="ind.unit" class="unit"> {{ ind.unit }}</span>
          </td>
          <td class="ref">{{ ind.ref_range || "—" }}</td>
          <td>
            <span class="badge" :class="statusOf(ind).cls">{{ statusOf(ind).label }}</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td colspan="4" class="empty">暂无指标</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tbl-wrap {
  overflow-x: auto;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.tbl th {
  text-align: left;
  font-weight: 500;
  color: #64748b;
  font-size: 12px;
  padding: 8px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}
.tbl td {
  padding: 11px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  color: #cbd5e1;
}
.tbl tr.abn td {
  background: rgba(248, 113, 113, 0.04);
}
.name {
  font-weight: 500;
  color: #e2e8f0;
}
.val {
  font-family: ui-monospace, monospace;
  color: #f1f5f9;
}
.unit {
  color: #64748b;
  font-size: 12px;
}
.ref {
  font-family: ui-monospace, monospace;
  color: #94a3b8;
  font-size: 13px;
}
.badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 9999px;
  border: 1px solid transparent;
}
.badge.ok {
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
  border-color: rgba(52, 211, 153, 0.28);
}
.badge.high {
  color: #fb923c;
  background: rgba(251, 146, 60, 0.12);
  border-color: rgba(251, 146, 60, 0.3);
}
.badge.low {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.12);
  border-color: rgba(251, 191, 36, 0.3);
}
.empty {
  text-align: center;
  color: #64748b;
  padding: 28px;
}
</style>
