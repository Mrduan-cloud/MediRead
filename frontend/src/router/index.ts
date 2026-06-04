import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/report" },
    {
      path: "/login",
      name: "login",
      component: () => import("@/views/LoginView.vue"),
    },
    {
      // 主页面:上传 → OCR 解析 → AI 解读
      path: "/report",
      name: "report",
      component: () => import("@/views/ReportView.vue"),
      meta: { requiresAuth: true },
    },
    {
      // 历史趋势:多次报告同指标随时间变化
      path: "/history",
      name: "history",
      component: () => import("@/views/HistoryView.vue"),
      meta: { requiresAuth: true },
    },
  ],
});

// 路由守卫:未登录访问受保护页 → 跳登录;已登录访问登录页 → 回主页面
router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.requiresAuth && !auth.token) {
    return { name: "login" };
  }
  if (to.name === "login" && auth.token) {
    return { name: "report" };
  }
});

export default router;
