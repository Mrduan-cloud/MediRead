<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { useMessage, NButton, NSpin, NProgress } from "naive-ui";
import client from "@/api/client";
import AppHeader from "@/components/AppHeader.vue";
import IndicatorTable, { type Indicator } from "@/components/IndicatorTable.vue";
import InterpretationResult from "@/components/InterpretationResult.vue";

const message = useMessage();

type Phase =
  | "idle"
  | "staged"
  | "uploading"
  | "parsing"
  | "parsed"
  | "interpreting"
  | "done";
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

// 待解析的文件:拖入/选中后先预览确认,再上传解析(而非拖入即跑 OCR+LLM)
const stagedFile = ref<File | null>(null);
const previewUrl = ref<string>("");
const previewKind = ref<"image" | "pdf" | "">("");
// 真实上传进度(0–100),由 axios onUploadProgress 驱动
const uploadPercent = ref(0);
// 本次 staged 文件已成功上传得到的 report_id;解析失败重试时复用,避免重传残留空报告行
const uploadedId = ref("");

// 「我的报告」分页
const page = ref(1);
const total = ref(0);
const PAGE_SIZE = 8;
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));

async function loadReports() {
  try {
    const { data } = await client.get("/api/history/reports", {
      params: { page: page.value, page_size: PAGE_SIZE },
    });
    reports.value = data.items || [];
    total.value = data.total || 0;
  } catch {
    /* 列表失败不阻塞主流程 */
  }
}
onMounted(loadReports);

// 离开页面时回收预览 ObjectURL,避免内存泄漏
onBeforeUnmount(clearStaged);

function pickFile() {
  fileInput.value?.click();
}
function onInputChange(e: Event) {
  const target = e.target as HTMLInputElement;
  const f = target.files?.[0];
  if (f) stageFile(f);
  // 清空 input,使「重选同一文件」也能再次触发 change
  target.value = "";
}
function onDrop(e: DragEvent) {
  dragging.value = false;
  const f = e.dataTransfer?.files?.[0];
  if (f) stageFile(f);
}

const ALLOWED = ["jpg", "jpeg", "png", "pdf"];
const MAX_BYTES = 20 * 1024 * 1024;

function clearStaged() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  stagedFile.value = null;
  previewUrl.value = "";
  previewKind.value = "";
  uploadPercent.value = 0;
  uploadedId.value = "";
}

// 校验 + 生成本地预览,进入 staged 态等用户确认
function stageFile(file: File) {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ALLOWED.includes(ext)) {
    message.error(`不支持的文件类型:${ext}（支持 ${ALLOWED.join(" / ")}）`);
    return;
  }
  if (file.size > MAX_BYTES) {
    message.error(`文件过大（${prettySize(file.size)}），上限 20MB`);
    return;
  }
  clearStaged();
  interp.value = null;
  indicators.value = [];
  stagedFile.value = file;
  previewUrl.value = URL.createObjectURL(file);
  previewKind.value = ext === "pdf" ? "pdf" : "image";
  phase.value = "staged";
}

async function startParse() {
  const file = stagedFile.value;
  if (!file) return;
  try {
    // 仅在尚未上传时上传;解析失败重试复用已上传的 report_id,不重传(避免残留空报告行)
    if (!uploadedId.value) {
      phase.value = "uploading";
      uploadPercent.value = 0;
      const fd = new FormData();
      fd.append("file", file);
      const up = await client.post("/api/upload", fd, {
        onUploadProgress: (e) => {
          // e.total 为请求体大小(浏览器已知),上传阶段可靠;|| 1 兜底防 0 字节除零
          uploadPercent.value = Math.round((e.loaded / (e.total || file.size || 1)) * 100);
        },
      });
      uploadedId.value = up.data.report_id;
    }
    currentId.value = uploadedId.value;

    // 上传完成 → OCR 解析是服务端工作、无进度事件,改用不定态指示
    phase.value = "parsing";
    const parsed = await client.post(`/api/parse/${currentId.value}`);
    indicators.value = parsed.data.indicators || [];
    phase.value = "parsed";
    clearStaged();
    message.success(`解析完成,识别 ${indicators.value.length} 项指标`);
    page.value = 1; // 新报告落在第一页
    void loadReports();
  } catch (e: any) {
    phase.value = "staged"; // 失败退回预览态,可重试或重选
    uploadPercent.value = 0;
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
    clearStaged();
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
  clearStaged();
  phase.value = "idle";
  currentId.value = "";
  indicators.value = [];
  interp.value = null;
}

async function goPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return;
  page.value = p;
  await loadReports();
}

function prettySize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
        <!-- 上传区:无文件、无指标时展示 -->
        <div
          v-if="phase === 'idle' && !indicators.length"
          class="drop"
          :class="{ active: dragging }"
          @click="pickFile"
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
          <div class="d-icon">📄</div>
          <span class="d-title">上传体检报告</span>
          <span class="d-sub">点击或拖拽图片 / PDF（jpg · png · pdf，≤ 20MB）</span>
        </div>

        <!-- 预览 + 上传进度:staged / uploading / parsing -->
        <div
          v-if="stagedFile && ['staged', 'uploading', 'parsing'].includes(phase)"
          class="card"
        >
          <div class="card-head">
            <h3>
              预览
              <span class="muted">· {{ stagedFile.name }} · {{ prettySize(stagedFile.size) }}</span>
            </h3>
            <n-button v-if="phase === 'staged'" size="small" quaternary @click="reset">
              ↺ 重选
            </n-button>
          </div>

          <div class="preview">
            <img v-if="previewKind === 'image'" :src="previewUrl" alt="报告预览" class="pv-img" />
            <embed v-else :src="previewUrl" type="application/pdf" class="pv-pdf" />
          </div>

          <!-- 上传中:真实百分比进度条 -->
          <div v-if="phase === 'uploading'" class="prog">
            <n-progress
              type="line"
              :percentage="uploadPercent"
              :height="8"
              :border-radius="6"
              color="#38bdf8"
              rail-color="rgba(255,255,255,0.08)"
            />
            <span class="prog-label">上传中 {{ uploadPercent }}%</span>
          </div>
          <!-- 解析中:服务端 OCR,无进度,不定态 -->
          <div v-else-if="phase === 'parsing'" class="prog parsing">
            <n-spin size="small" />
            <span class="prog-label"
              >PaddleOCR 解析中…<span class="muted"> 版式识别 + 指标抽取 + 数值归一化</span></span
            >
          </div>
          <!-- 已就绪:确认开始 -->
          <div v-else class="confirm-row">
            <n-button type="primary" size="large" @click="startParse">🔍 开始解析</n-button>
            <span class="muted">确认无误后上传并 OCR 解析</span>
          </div>
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
          <h4>我的报告 <span v-if="total" class="muted">· {{ total }}</span></h4>
          <n-button v-if="indicators.length || stagedFile" size="tiny" quaternary @click="reset">
            + 新建
          </n-button>
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

        <!-- 分页:仅多于一页时出现 -->
        <div v-if="totalPages > 1" class="pager">
          <button class="pg-btn" :disabled="page <= 1" @click="goPage(page - 1)">‹</button>
          <span class="pg-info">第 {{ page }} / {{ totalPages }} 页</span>
          <button class="pg-btn" :disabled="page >= totalPages" @click="goPage(page + 1)">›</button>
        </div>
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
  gap: 12px;
}
.card-head h3 {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 6px;
  overflow: hidden;
}
.card-head h3 .muted {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.muted {
  color: #64748b;
  font-size: 13px;
  font-weight: 400;
}
/* 预览 */
.preview {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 10px;
  max-height: 460px;
  overflow: hidden;
}
.pv-img {
  max-width: 100%;
  max-height: 440px;
  border-radius: 8px;
  object-fit: contain;
}
.pv-pdf {
  width: 100%;
  height: 440px;
  border: none;
  border-radius: 8px;
  background: #fff;
}
.prog {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.prog.parsing {
  gap: 10px;
}
.prog-label {
  font-size: 14px;
  color: #cbd5e1;
  white-space: nowrap;
}
.prog :deep(.n-progress) {
  flex: 1;
}
.confirm-row,
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
/* 分页 */
.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.pg-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: transparent;
  color: #cbd5e1;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.12s;
}
.pg-btn:hover:not(:disabled) {
  border-color: #38bdf8;
  color: #38bdf8;
}
.pg-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.pg-info {
  font-size: 12px;
  color: #94a3b8;
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
