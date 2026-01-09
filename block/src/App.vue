<!--
 * @Descripttion: 主应用组件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import { ref } from 'vue';
import SingleNodeFlow from './components/SingleNodeFlow/index.vue';
import SchemaManager from './components/SchemaManager/index.vue';

// 当前激活的标签页
const activeTab = ref<'single' | 'manager'>('single');

// Blocks 数据
const blocks = [
  { "inputs": [], "name": "Sensor", "options": [{ "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"], "name": "采样率", "properties": { "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"] }, "type": "SelectOption", "value": "128000" }, { "items": ["Bipolar[-10V,10V]"], "name": "量程", "properties": { "items": ["Bipolar[-10V,10V]"] }, "type": "SelectOption", "value": "Bipolar[-10V,10V]" }], "outputs": [{ "name": "O-Sensor" }] },
  { "inputs": [{ "name": "I-Sensor" }], "name": "Channel", "options": [{ "name": "启用", "type": "CheckboxOption", "value": true }, { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"], "name": "通道", "properties": { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"] }, "type": "SelectOption", "value": null }, { "max": 10, "min": 0, "name": "灵敏度", "properties": { "max": 10, "min": 0 }, "type": "NumberOption", "value": null }, { "items": ["m", "m/s", "m/s²", "g"], "name": "单位", "properties": { "items": ["m", "m/s", "m/s²", "g"] }, "type": "SelectOption", "value": null }, { "name": "IEPE/ICP/CCLD", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-XY" }], "name": "ToList1D", "options": [{ "items": ["X", "Y"], "name": "输出", "properties": { "items": ["X", "Y"] }, "type": "SelectOption", "value": "Y" }], "outputs": [{ "name": "O-List-V" }] },
  { "inputs": [{ "name": "I-List-X" }, { "name": "I-List-Y" }], "name": "ToList2D", "options": [], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-V" }], "name": "FourierTransform", "options": [{ "name": "绝对值", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "List-XY" }], "name": "Result", "options": [{ "items": ["时域", "频域", "FREE"], "name": "类型", "properties": { "items": ["时域", "频域", "FREE"] }, "type": "SelectOption", "value": null }, { "name": "名称", "type": "InputOption", "value": "" }], "outputs": [] }
];

// 切换标签页
function switchTab(tab: 'single' | 'manager') {
  activeTab.value = tab;
}
</script>

<template>
  <div class="app-container">
    <!-- 标签页导航 -->
    <div class="tab-nav">
      <button
        :class="['tab-button', { active: activeTab === 'single' }]"
        @click="switchTab('single')"
      >
        单个编辑器
      </button>
      <button
        :class="['tab-button', { active: activeTab === 'manager' }]"
        @click="switchTab('manager')"
      >
        Schema 管理
      </button>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <SingleNodeFlow v-if="activeTab === 'single'" :blocks="blocks" />
      <SchemaManager v-else :blocks="blocks" />
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