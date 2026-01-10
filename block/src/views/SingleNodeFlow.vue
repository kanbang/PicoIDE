<!--
 * @Descripttion: 单个 NodeFlow 编辑器
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import NodeFlow from '@/components/NodeFlow/index.vue'
import { ref, onMounted } from 'vue';

// Props
// Blocks 数据
const blocks = [
  { "inputs": [], "name": "Sensor", "options": [{ "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"], "name": "采样率", "properties": { "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"] }, "type": "SelectOption", "value": "128000" }, { "items": ["Bipolar[-10V,10V]"], "name": "量程", "properties": { "items": ["Bipolar[-10V,10V]"] }, "type": "SelectOption", "value": "Bipolar[-10V,10V]" }], "outputs": [{ "name": "O-Sensor" }] },
  { "inputs": [{ "name": "I-Sensor" }], "name": "Channel", "options": [{ "name": "启用", "type": "CheckboxOption", "value": true }, { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"], "name": "通道", "properties": { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"] }, "type": "SelectOption", "value": null }, { "max": 10, "min": 0, "name": "灵敏度", "properties": { "max": 10, "min": 0 }, "type": "NumberOption", "value": null }, { "items": ["m", "m/s", "m/s²", "g"], "name": "单位", "properties": { "items": ["m", "m/s", "m/s²", "g"] }, "type": "SelectOption", "value": null }, { "name": "IEPE/ICP/CCLD", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-XY" }], "name": "ToList1D", "options": [{ "items": ["X", "Y"], "name": "输出", "properties": { "items": ["X", "Y"] }, "type": "SelectOption", "value": "Y" }], "outputs": [{ "name": "O-List-V" }] },
  { "inputs": [{ "name": "I-List-X" }, { "name": "I-List-Y" }], "name": "ToList2D", "options": [], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-V" }], "name": "FourierTransform", "options": [{ "name": "绝对值", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "List-XY" }], "name": "Result", "options": [{ "items": ["时域", "频域", "FREE"], "name": "类型", "properties": { "items": ["时域", "频域", "FREE"] }, "type": "SelectOption", "value": null }, { "name": "名称", "type": "InputOption", "value": "" }], "outputs": [] }
];

const STORAGE_KEY = 'nodeflow_schema';

// 使用 ref 引用 NodeFlow 组件实例
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// 保存状态
const hasUnsavedChanges = ref(false);

// 从本地存储加载 schema
function loadFromStorage(): void {
  const savedSchema = localStorage.getItem(STORAGE_KEY);
  if (savedSchema) {
    try {
      const schema = JSON.parse(savedSchema);
      // 通过 ref 调用 NodeFlow 的加载方法
      nodeFlowRef.value?.loadSchema(schema);
    } catch (e) {
      console.error('Failed to parse saved schema:', e);
    }
  }
}

// 保存 schema 到本地存储
function saveToStorage(data: any): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  hasUnsavedChanges.value = false;
}

// 处理 NodeFlow 的保存事件
function handleSave(data: any): void {
  saveToStorage(data);
}

// 处理 schema 更新事件
function handleUpdate(schema: any): void {
  // schema 已更新，但不自动保存，等待用户点击保存按钮
  console.log('Schema updated:', schema);
}

// 处理未保存更改状态变化
function handleUnsavedChanges(changes: boolean): void {
  hasUnsavedChanges.value = changes;
  // 可以在这里更新 UI，比如显示"有未保存的更改"提示
  console.log('Unsaved changes:', changes);
}

// 组件挂载后加载存储的数据
onMounted(() => {
  loadFromStorage();
});

</script>

<template>
  <div class="single-node-flow">
    <NodeFlow ref="nodeFlowRef" :blocks="blocks" @save="handleSave" @update="handleUpdate"
      @unsaved-changes="handleUnsavedChanges" />
  </div>
</template>

<style scoped>
.single-node-flow {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>