<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from "vue";
import * as echarts from "echarts";

const props = defineProps<{ option: Record<string, any> | null | undefined }>();

const el = ref<HTMLDivElement | null>(null);
let chart: echarts.ECharts | null = null;
let ro: ResizeObserver | null = null;

function render() {
  if (!el.value || !props.option) return;
  if (!chart) chart = echarts.init(el.value, "dark");
  chart.setOption({ backgroundColor: "transparent", ...props.option }, true);
  chart.resize();
}

onMounted(async () => {
  await nextTick();
  render();
  if (el.value && "ResizeObserver" in window) {
    ro = new ResizeObserver(() => chart?.resize());
    ro.observe(el.value);
  }
  window.addEventListener("resize", () => chart?.resize());
});

onBeforeUnmount(() => {
  ro?.disconnect();
  ro = null;
  chart?.dispose();
  chart = null;
});

watch(() => props.option, render, { deep: true });
</script>

<template>
  <div ref="el" class="echart" />
</template>

<style scoped>
.echart {
  width: 100%;
  height: 300px;
}
</style>
