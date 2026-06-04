<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useMessage, NSelect, NEmpty } from "naive-ui";
import client from "@/api/client";
import AppHeader from "@/components/AppHeader.vue";
import TrendChart from "@/components/TrendChart.vue";

const message = useMessage();

interface Point {
  report_id: string;
  created_at: string | null;
  value: number;
  ref_range?: string | null;
  abnormal?: boolean;
}
const series = ref<Record<string, Point[]>>({});
const selected = ref<string>("");
const loading = ref(true);

const names = computed(() => Object.keys(series.value));
const options = computed(() => names.value.map((n) => ({ label: n, value: n })));

onMounted(async () => {
  try {
    const { data } = await client.get("/api/history/series");
    series.value = data.series || {};
    // 默认选数据点最多的指标
    const sorted = Object.entries(series.value).sort((a, b) => b[1].length - a[1].length);
    if (sorted.length) selected.value = sorted[0][0];
  } catch (e: any) {
    message.error(e?.response?.data?.detail || "加载趋势失败,请确认后端已启动");
  } finally {
    loading.value = false;
  }
});

const option = computed(() => {
  const pts = series.value[selected.value] || [];
  return {
    color: ["#38bdf8"],
    grid: { left: 52, right: 24, top: 30, bottom: 40 },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: pts.map((p) => (p.created_at || "").slice(0, 10)),
      axisLabel: { color: "#94a3b8" },
      axisLine: { lineStyle: { color: "#334155" } },
    },
    yAxis: {
      type: "value",
      scale: true,
      axisLabel: { color: "#94a3b8" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbolSize: 8,
        data: pts.map((p) => p.value),
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.12 },
      },
    ],
  };
});

const pointCount = computed(() => (series.value[selected.value] || []).length);
</script>

<template>
  <div class="page">
    <AppHeader />
    <main class="wrap">
      <div class="card">
        <div class="card-head">
          <h3>历史趋势 <span class="muted">· 同指标随时间变化</span></h3>
          <n-select
            v-if="names.length"
            v-model:value="selected"
            :options="options"
            size="small"
            style="width: 200px"
          />
        </div>

        <div v-if="loading" class="state">加载中…</div>
        <template v-else-if="names.length">
          <p class="hint">
            指标「{{ selected }}」共 {{ pointCount }} 个时间点{{
              pointCount < 2 ? "（多次上传报告后即可看到趋势曲线）" : ""
            }}
          </p>
          <TrendChart :option="option" />
        </template>
        <n-empty v-else description="暂无历史数据,先到「报告解读」上传几份报告" class="state" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}
.wrap {
  max-width: 900px;
  margin: 0 auto;
  padding: 26px 22px 60px;
}
.card {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.025);
  padding: 18px 20px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 12px;
}
.card-head h3 {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}
.muted {
  color: #64748b;
  font-size: 13px;
  font-weight: 400;
}
.hint {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 4px;
}
.state {
  padding: 48px 0;
  text-align: center;
  color: #64748b;
}
</style>
