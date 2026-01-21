<!--
 * @Descripttion: 主应用组件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { useBusinessStore } from '@/stores/business';
import SingleNodeFlow from '@/views/NodeFlowDemo.vue';
import SchemaManagerExample from '@/views/FlowManagerApiDemo.vue';
import TinyCode from '@/views/TinyCode.vue';

const TAB_STORAGE_KEY = 'picoide_active_tab';

// 当前激活的标签页
const activeTab = ref<'single' | 'manager' | 'tinycode'>('single');

// 使用 Pinia store
const businessStore = useBusinessStore();

// 从 localStorage 恢复 tab 状态
function restoreTabFromStorage() {
  const savedTab = localStorage.getItem(TAB_STORAGE_KEY);
  if (savedTab && ['single', 'manager', 'tinycode'].includes(savedTab)) {
    activeTab.value = savedTab as 'single' | 'manager' | 'tinycode';
  }
}

// 切换标签页
function switchTab(tab: 'single' | 'manager' | 'tinycode') {
  activeTab.value = tab;
  localStorage.setItem(TAB_STORAGE_KEY, tab);
}

// 监听 tab 变化，自动保存
watch(activeTab, (newTab) => {
  localStorage.setItem(TAB_STORAGE_KEY, newTab);
});

// 组件挂载时恢复 tab 状态
onMounted(() => {
  restoreTabFromStorage();
});
</script>

<template>
  <div class="app-container">
    <!-- 标签页导航 -->
    <div class="tab-nav">
      <div class="tab-buttons">
        <button :class="['tab-button', { active: activeTab === 'single' }]" @click="switchTab('single')">
          Flow Playground
        </button>
        <button :class="['tab-button', { active: activeTab === 'manager' }]" @click="switchTab('manager')">
          Flow Manager
        </button>
        <button :class="['tab-button', { active: activeTab === 'tinycode' }]" @click="switchTab('tinycode')">
          Block Builder
        </button>
      </div>
      
      <!-- Business 选择框 -->
      <div class="business-selector">
        <label for="business-select">业务:</label>
        <select id="business-select" v-model="businessStore.business">
          <option value="DEMO">DEMO</option>
          <option value="WAVE">WAVE</option>
        </select>
      </div>
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
  justify-content: space-between;
  align-items: center;
  background: #2d2d2d;
  border-bottom: 1px solid #444;
  padding: 0 16px;
}

.tab-buttons {
  display: flex;
  gap: 0;
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

.business-selector {
  display: flex;
  align-items: center;
  gap: 8px;
}

.business-selector label {
  color: #888;
  font-size: 12px;
}

.business-selector select {
  background: #2d2d2d;
  border: 1px solid #3c3c3c;
  color: #aaa;
  padding: 4px 8px;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.business-selector select:hover {
  border-color: #444;
  color: #ccc;
}

.business-selector select:focus {
  border-color: #3c3c3c;
}

.tab-content {
  flex: 1;
  overflow: hidden;
}
</style>