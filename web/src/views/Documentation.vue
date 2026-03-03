<!--
 * @Descripttion: NodeFlow 文档页面
 * @version: 0.x
 * @Date: 2026-02-24
-->
<script setup lang="ts">
import { ref } from 'vue';
import Introduction from './docs/Introduction.vue';
import FlowUsage from './docs/FlowUsage.vue';
import FlowManager from './docs/FlowManager.vue';
import BlockBuilder from './docs/BlockBuilder.vue';
import CustomBlock from './docs/CustomBlock.vue';
import ApiReference from './docs/ApiReference.vue';

const activeSection = ref<string>('intro');

const sections = [
  { id: 'intro', title: '快速入门', component: Introduction },
  { id: 'flow', title: 'Flow Playground', component: FlowUsage },
  { id: 'manager', title: 'Flow Manager', component: FlowManager },
  { id: 'builder', title: 'Block Builder', component: BlockBuilder },
  { id: 'custom', title: '自定义 Block', component: CustomBlock },
  { id: 'api', title: 'API 参考', component: ApiReference },
];
</script>

<template>
  <div class="documentation">
    <!-- 侧边导航 -->
    <div class="sidebar">
      <h2 class="sidebar-title">NodeFlow 文档</h2>
      <nav class="nav-menu">
        <button
          v-for="section in sections"
          :key="section.id"
          :class="['nav-item', { active: activeSection === section.id }]"
          @click="activeSection = section.id"
        >
          {{ section.title }}
        </button>
      </nav>
    </div>

    <!-- 主内容区 -->
    <div class="content">
      <component
        :is="sections.find(s => s.id === activeSection)?.component"
        v-if="activeSection"
      />
    </div>
  </div>
</template>

<style scoped>
.documentation {
  display: flex;
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  color: #e0e0e0;
}

.sidebar {
  width: 240px;
  background: #252526;
  border-right: 1px solid #3c3c3c;
  display: flex;
  flex-direction: column;
  padding: 16px;
  flex-shrink: 0;
}

.sidebar-title {
  margin: 0 0 16px;
  font-size: 16px;
  color: #4caf50;
  padding-bottom: 12px;
  border-bottom: 1px solid #3c3c3c;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  padding: 10px 12px;
  background: transparent;
  border: none;
  color: #888;
  text-align: left;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
  transition: all 0.2s;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
}

.nav-item.active {
  background: rgba(76, 175, 80, 0.15);
  color: #4caf50;
}

.content {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #3c3c3c;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #4a4a4a;
}
</style>