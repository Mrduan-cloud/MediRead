<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useMessage, NButton, NSpin } from "naive-ui";
import client from "@/api/client";
import AppHeader from "@/components/AppHeader.vue";
import IndicatorTable, { type Indicator } from "@/components/IndicatorTable.vue";
import InterpretationResult from "@/components/InterpretationResult.vue";

const message = useMessage();

type Phase = "idle" | "uploading" | "parsing" | "parsed" | "interpreting" | "done";
const phase = ref<Phase>("idle");

interface ReportRow {
  report_id: string;
  created_at: string | null;
  n_indicators: number;
  n_abnormal: number;
}
const reports = ref<ReportRow[]>([]);
const currentId = ref<string>("");
const indicators = ref<Indicator[]>([]);
const interp = ref<any>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const dragging = ref(false);

const busy = () => ["uploading", "parsing", "interpreting"].includes(phase.value);

async function loadReports() {
  try {
    const { data } = await client.get("/api/history/reports");
    reports.value = data;
  } catch {
    /* 列表失败不阻塞主流程 */
  }
}
onMounted(loadReports);

function pickFile() {
  fileInput.value?.click();
}
function onInputChange(e: Event) {
  const f = (e.target as HTMLInputElement).files?.[0];
  if (f) void uploadAndParse(f);
}
function onDrop(e: DragEvent) {
  dragging.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (f) void uploadAndParse(f);
}

const ALLOWED = ["jpg", "jpeg", "png", "pdf"];

async function uploadAndParse(file: File) {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED.includes(ext)) {
    message.error(`不支持的文件类型:${ext}（支持 ${ALLOWED.join(" / ")}）`);
    return;
  }
  interp.value = null;
  indicators.value = [];
  try {
    phase.value = "uploading";
    const fd = new FormData();
    fd.append("file", file);
    const up = await client.post("/api/upload", fd);
    currentId.value = up.data.report_id;

    phase.value = "parsing";
    const parsed = await client.post(`/api/parse/${currentId.value}`);
    indicators.value = parsed.data.indicators || [];
    phase.value = "parsed";
    message.success(`解析完成,识别 ${indicators.value.length} 项指标`);
    void loadReports();
  } catch (e: any) {
    phase.value = "idle";
    message.error(e?.response?.data?.detail || "上传 / 解析失败,请确认后端服务已启动");
  }
}

async function runInterpret() {
  if (!currentId.value) return;
  try {
    phase.value = "interpreting";
    const { data } = await client.post(`/api/interpret/${currentId.value}`);
    interp.value = data;
    phase.value = "done";
    void loadReports();
  } catch (e: any) {
    phase.value = "parsed";
    message.error(e?.response?.data?.detail || "AI 解读失败,请稍后重试");
  }
}

async function openReport(id: string) {
  try {
    interp.value = null;
    indicators.value = [];
    const { data } = await client.get(`/api/history/report/${id}`);
    currentId.value = id;
    indicators.value = data.indicators || [];
    if (data.interpretation) {
      interp.value = data.interpretation;
      phase.value = "done";
    } else {
      phase.value = "parsed";
    }
  } catch (e: any) {
    message.error(e?.response?.data?.detail || "加载报告失败");
  }
}

function reset() {
  phase.value = "idle";
  currentId.value = "";
  indicators.value = [];
  interp.value = null;
}

function shortId(id: string) {
  return id.length > 10 ? id.slice(0, 8) : id;
}
</script>

<template>
  <div class="page">
    <AppHeader />
    <main class="wrap">
      <section class="main-col">
        <!-- 上传区:仅在无指标时展示 -->
        <div
          v-if="!indicators.length"
          class="drop"
          :class="{ active: dragging, busy: busy() }"
          @click="!busy() && pickFile()"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".jpg,.jpeg,.png,.pdf"
            hidden
            @change="onInputChange"
          />
          <template v-if="phase === 'uploading'">
            <n-spin size="small" /><span class="d-title">上传中…</span>
          </template>
          <template v-else-if="phase === 'parsing'">
            <n-spin size="small" /><span class="d-title">PaddleOCR 解析中…</span>
            <span class="d-sub">版式识别 + 指标抽取 + 数值归一化</span>
          </template>
          <template v-else>
            <div class="d-icon">📄</div>
            <span class="d-title">上传体检报告</span>
            <span class="d-sub">点击或拖拽图片 / PDF（jpg · png · pdf，≤ 20MB）</span>
          </template>
        </div>

        <!-- 结构化指标 -->
        <div v-if="indicators.length" class="card">
          <div class="card-head">
            <h3>结构化指标 <span class="muted">· {{ indicators.length }} 项</span></h3>
            <n-button size="small" quaternary @click="reset">↺ 换一份</n-button>
          </div>
          <IndicatorTable :indicators="indicators" />
          <div v-if="phase !== 'done'" class="interpret-row">
            <n-button
              type="primary"
              size="large"
              :loading="phase === 'interpreting'"
              @click="runInterpret"
            >
              {{ phase === "interpreting" ? "AI 解读中…" : "🩺 AI 智能解读" }}
            </n-button>
            <span class="muted">RAG 检索知识库 + 风险分级 + 联合分析</span>
          </div>
        </div>

        <!-- 解读结果 -->
        <div v-if="interp" class="card">
          <div class="card-head"><h3>AI 解读结果</h3></div>
          <InterpretationResult :result="interp" />
        </div>
      </section>

      <!-- 我的报告 -->
      <aside class="side">
        <div class="side-head">
          <h4>我的报告</h4>
          <n-button v-if="indicators.length" size="tiny" quaternary @click="reset">+ 新建</n-button>
        </div>
        <p v-if="!reports.length" class="side-empty">暂无报告,上传一份开始体验</p>
        <button
          v-for="r in reports"
          :key="r.report_id"
          class="r-item"
          :class="{ active: r.report_id === currentId }"
          @click="openReport(r.report_id)"
        >
          <div class="r-top">
            <span class="r-id">{{ shortId(r.report_id) }}</span>
            <span v-if="r.n_abnormal" class="r-abn">{{ r.n_abnormal }} 异常</span>
            <span v-else class="r-ok">正常</span>
          </div>
          <div class="r-meta">{{ r.created_at?.slice(0, 10) || "—" }} · {{ r.n_indicators }} 项指标</div>
        </button>
      </aside>
    </main>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
}
.wrap {
  max-width: 1080px;
  margin: 0 auto;
  padding: 26px 22px 60px;
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 22px;
  align-items: start;
}
.main-col {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-width: 0;
}
.drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 260px;
  border: 1.5px dashed rgba(56, 189, 248, 0.3);
  border-radius: 16px;
  background: rgba(56, 189, 248, 0.03);
  cursor: pointer;
  transition: all 0.15s;
  text-align: center;
  padding: 24px;
}
.drop:hover,
.drop.active {
  border-color: #38bdf8;
  background: rgba(56, 189, 248, 0.07);
}
.drop.busy {
  cursor: default;
}
.d-icon {
  font-size: 38px;
  opacity: 0.85;
}
.d-title {
  font-size: 17px;
  font-weight: 600;
  color: #e2e8f0;
}
.d-sub {
  font-size: 13px;
  color: #64748b;
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
.interpret-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.side {
  position: sticky;
  top: 80px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.025);
  padding: 14px;
}
.side-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.side-head h4 {
  font-size: 14px;
  color: #cbd5e1;
}
.side-empty {
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
  padding: 8px 2px;
}
.r-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 9px 11px;
  cursor: pointer;
  transition: all 0.12s;
  margin-bottom: 4px;
}
.r-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.r-item.active {
  background: rgba(56, 189, 248, 0.1);
  border-color: rgba(56, 189, 248, 0.3);
}
.r-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.r-id {
  font-family: ui-monospace, monospace;
  font-size: 13px;
  color: #e2e8f0;
}
.r-abn {
  font-size: 11px;
  color: #fb923c;
  background: rgba(251, 146, 60, 0.12);
  border-radius: 9999px;
  padding: 1px 7px;
}
.r-ok {
  font-size: 11px;
  color: #34d399;
  background: rgba(52, 211, 153, 0.1);
  border-radius: 9999px;
  padding: 1px 7px;
}
.r-meta {
  font-size: 12px;
  color: #64748b;
  margin-top: 3px;
}
@media (max-width: 820px) {
  .wrap {
    grid-template-columns: 1fr;
  }
  .side {
    position: static;
  }
}
</style>
