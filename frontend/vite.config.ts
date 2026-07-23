import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // 代码分割：按路由/组件拆分 chunk，减少首屏加载
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom"],
          charts: ["echarts", "echarts-for-react"],
          antd: ["antd", "@ant-design/icons"],
        },
      },
    },
    // 压缩 CSS
    cssMinify: true,
    // 生成 source map（生产环境关闭）
    sourcemap: false,
    // chunk 大小告警阈值
    chunkSizeWarningLimit: 600,
    // 依赖预打包优化
    modulePreload: { polyfill: true },
    // 目标浏览器：es2020 兼顾现代浏览器和较新特性
    target: "es2020",
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
