<!--
 * @Descripttion:
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-10 21:08:00
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-21 09:18:35
-->
<template>
  <iframe
    :src="iframeSrc"
    frameborder="0"
    allowfullscreen
    class="tiny-code-iframe"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useBusinessStore } from '@/stores/business';

const businessStore = useBusinessStore();

// 动态生成 iframe URL，通过配置参数传递 business
const iframeSrc = computed(() => {
  const business = businessStore.business;
  return `/tinycode.html?business=${encodeURIComponent(business)}`;
});
</script>

<style scoped>
.tiny-code-iframe {
  width: 100%;
  height: 100vh;
  border: none;
  display: block;
}
</style>