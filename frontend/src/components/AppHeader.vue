<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
import { NButton } from "naive-ui";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

function go(name: string) {
  router.push({ name });
}
function logout() {
  auth.logout();
  router.push("/login");
}
</script>

<template>
  <header class="hdr">
    <div class="left">
      <span class="logo">🩺</span>
      <span class="brand">MediRead</span>
      <nav class="nav">
        <button :class="{ active: route.name === 'report' }" @click="go('report')">报告解读</button>
        <button :class="{ active: route.name === 'history' }" @click="go('history')">历史趋势</button>
      </nav>
    </div>
    <div class="right">
      <span class="user">{{ auth.userId }}</span>
      <n-button size="small" quaternary @click="logout">退出</n-button>
    </div>
  </header>
</template>

<style scoped>
.hdr {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 58px;
  padding: 0 22px;
  background: rgba(10, 10, 10, 0.72);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(12px);
}
.left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.logo {
  font-size: 20px;
}
.brand {
  font-weight: 800;
  font-size: 17px;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #e2e8f0, #7dd3fc);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.nav {
  display: flex;
  gap: 4px;
  margin-left: 10px;
}
.nav button {
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.12s;
}
.nav button:hover {
  color: #e2e8f0;
  background: rgba(255, 255, 255, 0.05);
}
.nav button.active {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.12);
}
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user {
  font-family: ui-monospace, monospace;
  font-size: 13px;
  color: #94a3b8;
}
</style>
