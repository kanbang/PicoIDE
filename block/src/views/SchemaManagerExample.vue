<script setup lang="ts">
import { ref, onMounted } from 'vue';
import SchemaManager, { SchemaItem } from '@/components/SchemaManager/index.vue'; // 确保路径正确，原代码是 @/components/...

const STORAGE_KEY = 'schema_manager_example_data';

// Blocks 数据 (保持不变)
const blocks = [
  { "inputs": [], "name": "Sensor", "options": [{ "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"], "name": "采样率", "properties": { "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"] }, "type": "SelectOption", "value": "128000" }, { "items": ["Bipolar[-10V,10V]"], "name": "量程", "properties": { "items": ["Bipolar[-10V,10V]"] }, "type": "SelectOption", "value": "Bipolar[-10V,10V]" }], "outputs": [{ "name": "O-Sensor" }] },
  { "inputs": [{ "name": "I-Sensor" }], "name": "Channel", "options": [{ "name": "启用", "type": "CheckboxOption", "value": true }, { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"], "name": "通道", "properties": { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"] }, "type": "SelectOption", "value": null }, { "max": 10, "min": 0, "name": "灵敏度", "properties": { "max": 10, "min": 0 }, "type": "NumberOption", "value": null }, { "items": ["m", "m/s", "m/s²", "g"], "name": "单位", "properties": { "items": ["m", "m/s", "m/s²", "g"] }, "type": "SelectOption", "value": null }, { "name": "IEPE/ICP/CCLD", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-XY" }], "name": "ToList1D", "options": [{ "items": ["X", "Y"], "name": "输出", "properties": { "items": ["X", "Y"] }, "type": "SelectOption", "value": "Y" }], "outputs": [{ "name": "O-List-V" }] },
  { "inputs": [{ "name": "I-List-X" }, { "name": "I-List-Y" }], "name": "ToList2D", "options": [], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "I-List-V" }], "name": "FourierTransform", "options": [{ "name": "绝对值", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] },
  { "inputs": [{ "name": "List-XY" }], "name": "Result", "options": [{ "items": ["时域", "频域", "FREE"], "name": "类型", "properties": { "items": ["时域", "频域", "FREE"] }, "type": "SelectOption", "value": null }, { "name": "名称", "type": "InputOption", "value": "" }], "outputs": [] }
];

// Schema 列表
const schemas = ref<SchemaItem[]>([]);
// 当前选中的 Schema ID
const selectedSchemaId = ref<string | null>(null);

// 从 localStorage 加载数据
function loadFromStorage(): void {
  const savedData = localStorage.getItem(STORAGE_KEY);
  if (savedData) {
    try {
      const data = JSON.parse(savedData);
      schemas.value = data.schemas || [];
      selectedSchemaId.value = data.selectedSchemaId || null;
    } catch (e) {
      console.error('Failed to parse saved data:', e);
    }
  }
}

// 保存到 localStorage
function saveToStorage(): void {
  const data = {
    schemas: schemas.value,
    selectedSchemaId: selectedSchemaId.value
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// 处理创建事件
function handleCreate(schema: SchemaItem): void {
  schemas.value.push(schema);
  saveToStorage();
}

// 处理保存事件
function handleSave(id: string, data: any): void {
  const schema = schemas.value.find(s => s.id === id);
  if (schema) {
    schema.schema = data;
    saveToStorage();
  }
}

// 处理删除事件
function handleDelete(id: string): void {
  const index = schemas.value.findIndex(s => s.id === id);
  if (index > -1) {
    schemas.value.splice(index, 1);
    saveToStorage();
  }
}

// 处理重命名事件
function handleRename(id: string, newName: string): void {
  const schema = schemas.value.find(s => s.id === id);
  if (schema) {
    schema.name = newName;
    saveToStorage();
  }
}

// 处理复制事件
function handleDuplicate(originalId: string, newSchema: SchemaItem): void {
  schemas.value.push(newSchema);
  saveToStorage();
}

// 组件挂载时加载数据
onMounted(() => {
  loadFromStorage();

  // 如果没有 schema，创建一个默认的
  if (schemas.value.length === 0) {
    const defaultSchema: SchemaItem = {
      id: crypto.randomUUID(),
      name: 'Schema 1',
      schema: null,
      hasUnsavedChanges: false
    };
    schemas.value.push(defaultSchema);
    selectedSchemaId.value = defaultSchema.id;
    saveToStorage();
  }
});
</script>

<template>
  <SchemaManager
    v-model:schemas="schemas"
    v-model:selected-schema-id="selectedSchemaId"
    :blocks="blocks"
    @create="handleCreate"
    @save="handleSave"
    @delete="handleDelete"
    @rename="handleRename"
    @duplicate="handleDuplicate"
  />
</template>

<style scoped>
/* 示例页面不需要额外样式 */
</style>