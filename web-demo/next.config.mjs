/** @type {import('next').NextConfig} */
const nextConfig = {
  // 纯静态导出：无服务端、无 API 路由 → 可部署到 Vercel / Cloudflare Pages / 任意静态托管。
  output: "export",
  images: { unoptimized: true },
  // GitHub Pages 等子路径部署时可设 basePath；Vercel 根部署留空。
};

export default nextConfig;
