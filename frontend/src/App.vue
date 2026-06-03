<script setup lang="ts">
import {
  NConfigProvider,
  NMessageProvider,
  NDialogProvider,
  darkTheme,
  zhCN,
  dateZhCN,
} from "naive-ui";
import { RouterView } from "vue-router";

// MediRead 主题:体检报告解读 → 深色高级风 + 医疗科技青蓝(sky)。
// 近黑底 + cyan 辉光,沿用已验证的视觉语言(web-demo 同源)。
const themeOverrides = {
  common: {
    primaryColor: "#38bdf8",
    primaryColorHover: "#7dd3fc",
    primaryColorPressed: "#0ea5e9",
    primaryColorSuppl: "#38bdf8",
    bodyColor: "#0a0a0a",
    cardColor: "rgba(255, 255, 255, 0.03)",
    modalColor: "#131316",
    popoverColor: "#16161a",
    borderRadius: "12px",
    fontSize: "14px",
  },
  Card: {
    color: "rgba(255, 255, 255, 0.03)",
    borderColor: "rgba(255, 255, 255, 0.08)",
  },
};
</script>

<template>
  <n-config-provider
    :theme="darkTheme"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-message-provider>
      <n-dialog-provider>
        <RouterView />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html,
body,
#app {
  height: 100%;
}
body {
  background-color: #0a0a0a;
  color: #ededed;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
  /* 极淡的顶部光晕,医疗科技感 */
  background-image: radial-gradient(
    60rem 40rem at 50% -12rem,
    rgba(56, 189, 248, 0.08),
    transparent 70%
  );
  background-repeat: no-repeat;
  background-attachment: fixed;
}
::selection {
  background: rgba(56, 189, 248, 0.24);
}
::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
::-webkit-scrollbar-thumb {
  background: #262626;
  border-radius: 9999px;
  border: 2px solid #0a0a0a;
}
::-webkit-scrollbar-thumb:hover {
  background: #404040;
}
</style>
