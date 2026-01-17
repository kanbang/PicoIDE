<!--
 * @Descripttion: 主应用组件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import { ref } from 'vue';
import SingleNodeFlow from '@/views/NodeFlowDemo.vue';
import SchemaManagerExample from '@/views/SchemaManagerApiDemo.vue';
import TinyCode from '@/views/TinyCode.vue';

// 当前激活的标签页
const activeTab = ref<'single' | 'manager' | 'tinycode'>('single');


// 切换标签页
function switchTab(tab: 'single' | 'manager' | 'tinycode') {
  activeTab.value = tab;
}
</script>

<template>
  <div class="app-container">
    <!-- 标签页导航 -->
    <div class="tab-nav">
      <button :class="['tab-button', { active: activeTab === 'single' }]" @click="switchTab('single')">
        Schema Playground
      </button>
      <button :class="['tab-button', { active: activeTab === 'manager' }]" @click="switchTab('manager')">
        Schema Manager
      </button>
      <button :class="['tab-button', { active: activeTab === 'tinycode' }]" @click="switchTab('tinycode')">
        Block Builder
      </button>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <SingleNodeFlow v-if="activeTab === 'single'" />
      <SchemaManagerExample v-else-if="activeTab === 'manager'" />
      <TinyCode v-else-if="activeTab === 'tinycode'" />
    </div>
  </div>
</template>

<style scoped>
.app-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-nav {
  display: flex;
  background: #2d2d2d;
  border-bottom: 1px solid #444;
}

.tab-button {
  padding: 12px 24px;
  background: transparent;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  border-bottom: 2px solid transparent;
}

.tab-button:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  color: #4caf50;
  border-bottom-color: #4caf50;
}

.tab-content {
  flex: 1;
  overflow: hidden;
}
</style>