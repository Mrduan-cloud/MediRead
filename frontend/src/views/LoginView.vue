<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useMessage, NForm, NFormItem, NInput, NButton, NModal } from "naive-ui";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const message = useMessage();
const auth = useAuthStore();

const username = ref("demo-001");
const password = ref("mediread2024");
const loading = ref(false);

// 演示账号(仅 is_demo,经 /demo-accounts 暴露,不泄露真实用户名)
const demoUsers = ref<string[]>(["demo-001"]);
const DEMO_PASSWORD = "mediread2024";

const PERSONA_HINTS: Record<string, string> = {
  "demo-001": "已灌入体检报告 · 可直接解读",
};
function personaHint(u: string): string {
  return PERSONA_HINTS[u] || "演示账号";
}

// 注册
const showReg = ref(false);
const regUser = ref("");
const regPwd = ref("");
const regPwd2 = ref("");
const registering = ref(false);

async function fetchDemoUsers() {
  try {
    const { data } = await axios.get("/api/auth/demo-accounts");
    if (Array.isArray(data.users) && data.users.length) demoUsers.value = data.users;
  } catch {
    /* 用默认演示账号兜底 */
  }
}
onMounted(fetchDemoUsers);

function pickDemo(u: string) {
  username.value = u;
  password.value = DEMO_PASSWORD;
}

async function onLogin() {
  if (!username.value || !password.value) {
    message.warning("请输入用户名和口令");
    return;
  }
  loading.value = true;
  try {
    await auth.login(username.value, password.value);
    message.success("登录成功");
    router.push("/report");
  } catch (e: any) {
    message.error(e?.response?.data?.detail || "登录失败,请重试");
  } finally {
    loading.value = false;
  }
}

async function onRegister() {
  const u = regUser.value.trim();
  if (!u) return message.warning("请输入用户名");
  if (regPwd.value.length < 6) return message.warning("口令至少 6 位");
  if (regPwd.value !== regPwd2.value) return message.warning("两次口令不一致");
  registering.value = true;
  try {
    await auth.register(u, regPwd.value);
    message.success(`欢迎,${u}！`);
    showReg.value = false;
    router.push("/report");
  } catch (e: any) {
    message.error(e?.response?.data?.detail || "注册失败,请重试");
  } finally {
    registering.value = false;
  }
}
</script>

<template>
  <div class="login-wrap">
    <div class="brand">
      <div class="logo">🩺</div>
      <h1>MediRead</h1>
      <p>AI 体检报告智能解读平台</p>
    </div>

    <div class="login-card">
      <h2 class="title">登录</h2>
      <n-form @submit.prevent="onLogin">
        <n-form-item label="用户名">
          <n-input v-model:value="username" placeholder="你的用户名" @keyup.enter="onLogin" />
        </n-form-item>
        <n-form-item label="口令">
          <n-input
            v-model:value="password"
            type="password"
            show-password-on="click"
            placeholder="你的口令"
            @keyup.enter="onLogin"
          />
        </n-form-item>

        <div class="personas">
          <span class="p-label">演示账号 · 一键填充体验</span>
          <button
            v-for="u in demoUsers"
            :key="u"
            type="button"
            class="persona"
            :class="{ active: u === username }"
            @click="pickDemo(u)"
          >
            <span class="p-name">{{ u }}</span>
            <span class="p-tag">{{ personaHint(u) }}</span>
          </button>
        </div>

        <n-button type="primary" block size="large" :loading="loading" @click="onLogin">
          登 录
        </n-button>
        <div class="reg-row">
          还没有账号?<a class="reg-link" @click="showReg = true">注册新用户</a>
        </div>
      </n-form>
      <p class="hint">演示账号:demo-001 · 口令 mediread2024</p>
    </div>

    <!-- 注册 -->
    <n-modal v-model:show="showReg" preset="card" title="注册新用户" style="width: 380px">
      <n-form @submit.prevent="onRegister">
        <n-form-item label="用户名">
          <n-input v-model:value="regUser" placeholder="字母 / 数字 / 下划线 / 连字符,1-64 位" />
        </n-form-item>
        <n-form-item label="设置口令">
          <n-input v-model:value="regPwd" type="password" show-password-on="click" placeholder="至少 6 位" />
        </n-form-item>
        <n-form-item label="确认口令">
          <n-input
            v-model:value="regPwd2"
            type="password"
            show-password-on="click"
            placeholder="再输入一次"
            @keyup.enter="onRegister"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="reg-actions">
          <n-button :disabled="registering" @click="showReg = false">取消</n-button>
          <n-button type="primary" :loading="registering" @click="onRegister">注册并登录</n-button>
        </div>
      </template>
    </n-modal>

    <p class="footer">Powered by PaddleOCR · 版式识别 · RAG · 风险分级 · DeepSeek</p>
  </div>
</template>

<style scoped>
.login-wrap {
  position: relative;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
  background:
    radial-gradient(820px 520px at 16% 10%, rgba(56, 189, 248, 0.16) 0%, transparent 55%),
    radial-gradient(760px 580px at 86% 90%, rgba(20, 60, 90, 0.45) 0%, transparent 60%),
    linear-gradient(160deg, #0b1016 0%, #0a0a0a 60%, #08090c 100%);
}
.brand {
  position: relative;
  text-align: center;
  color: #f5f7fa;
  margin-bottom: 26px;
  animation: rise 0.5s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.brand .logo {
  font-size: 38px;
  width: 76px;
  height: 76px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(150deg, rgba(56, 189, 248, 0.22), rgba(255, 255, 255, 0.04));
  border: 1px solid rgba(56, 189, 248, 0.3);
  border-radius: 22px;
  box-shadow: 0 12px 36px rgba(56, 189, 248, 0.18);
}
.brand h1 {
  font-size: 36px;
  font-weight: 800;
  letter-spacing: 1px;
  margin: 14px 0 6px;
  background: linear-gradient(90deg, #e2e8f0, #7dd3fc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.brand p {
  opacity: 0.7;
  font-size: 15px;
}
.login-card {
  position: relative;
  width: 396px;
  max-width: 92vw;
  padding: 26px 26px 20px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(8px);
  animation: rise 0.55s cubic-bezier(0.22, 1, 0.36, 1) 0.06s both;
}
@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.title {
  text-align: center;
  margin-bottom: 18px;
  color: #e5e7eb;
  font-weight: 600;
}
.personas {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 2px 0 18px;
}
.p-label {
  width: 100%;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 2px;
}
.persona {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  background: rgba(56, 189, 248, 0.06);
  border: 1px solid rgba(56, 189, 248, 0.18);
  border-radius: 10px;
  padding: 7px 12px;
  cursor: pointer;
  transition: all 0.12s;
  min-width: 120px;
}
.persona:hover {
  border-color: rgba(56, 189, 248, 0.5);
}
.persona.active {
  background: rgba(56, 189, 248, 0.16);
  border-color: #38bdf8;
}
.p-name {
  font-size: 14px;
  font-weight: 600;
  color: #e2e8f0;
  font-family: ui-monospace, monospace;
}
.p-tag {
  font-size: 11px;
  color: #94a3b8;
}
.reg-row {
  text-align: center;
  margin-top: 14px;
  font-size: 13px;
  color: #94a3b8;
}
.reg-link {
  color: #38bdf8;
  font-weight: 600;
  cursor: pointer;
}
.reg-link:hover {
  text-decoration: underline;
}
.reg-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.hint {
  text-align: center;
  color: #64748b;
  font-size: 13px;
  margin-top: 12px;
}
.footer {
  position: relative;
  margin-top: 24px;
  color: rgba(148, 163, 184, 0.6);
  font-size: 12px;
  font-family: ui-monospace, monospace;
}
</style>
