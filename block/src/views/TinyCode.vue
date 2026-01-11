<!--
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-10 21:08:00
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-11 14:47:50
-->
<template>
  <iframe
    src="/tinycode.html"
    frameborder="0"
    allowfullscreen
    class="tiny-code-iframe"
  />
</template>

<script setup lang="ts">
// 无需任何脚本逻辑
// 所有 VS Code Web 的加载、配置、UI 隐藏、菜单清理等完全由 /tinycode.html 处理
// 这避免了 Vite dev 的 CSP 限制、HMR 重复加载、inline script 被挡等问题
// 效果与你提供的独立 HTML 页面 100% 一致
</script>

<style scoped>
.tiny-code-iframe {
  width: 100%;
  height: 100vh;
  border: none;
  display: block;
}
</style>