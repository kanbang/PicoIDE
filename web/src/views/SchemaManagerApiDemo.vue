<script setup lang="ts">
import { ref, onMounted } from 'vue';
import SchemaManager, { SchemaItem } from '@/components/SchemaManager/index.vue'; // 确保路径正确，原代码是 @/components/...
import { getBlocks } from '@/api/index';

const STORAGE_KEY = 'schema_manager_example_data';

// Blocks 数据从后端获取
const blocks = ref<any[]>([]);

// Schema 列表
const schemas = ref<SchemaItem[]>([]);
// 当前选中的 Schema ID
const selectedSchemaId = ref<string | null>(null);

// 从后端加载 blocks
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    console.error('Error loading blocks:', error);
  }
}

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
  console.log('handleCreate called with schema:', schema);
  // 生成 ID
  const newSchemaWithId = {
    ...schema,
    id: crypto.randomUUID()
  };
  schemas.value.push(newSchemaWithId);
  // 自动选中新创建的 schema
  selectedSchemaId.value = newSchemaWithId.id;
  console.log('After push, schemas:', schemas.value);
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
  // 生成 ID
  const newSchemaWithId = {
    ...newSchema,
    id: crypto.randomUUID()
  };
  schemas.value.push(newSchemaWithId);
  // 自动选中新复制的 schema
  selectedSchemaId.value = newSchemaWithId.id;
  saveToStorage();
}

function handleRun(id: string, data: any) {
  alert('run: \n' + id + '\n' + JSON.stringify(data));
}

// 组件挂载时加载数据
onMounted(() => {
  loadBlocks();
  loadFromStorage();

  // 如果没有 schema，创建一个默认的
  // if (schemas.value.length === 0) {
  //   const defaultSchema: SchemaItem = {
  //     id: crypto.randomUUID(),
  //     name: 'Schema 1',
  //     schema: null,
  //     hasUnsavedChanges: false
  //   };
  //   schemas.value.push(defaultSchema);
  //   selectedSchemaId.value = defaultSchema.id;
  //   saveToStorage();
  // }
});
</script>

<template>
  <SchemaManager v-model:schemas="schemas" v-model:selected-schema-id="selectedSchemaId" :blocks="blocks"
    :show-run="true" @run="handleRun" @create="handleCreate" @save="handleSave" @delete="handleDelete"
    @rename="handleRename" @duplicate="handleDuplicate" />
</template>

<style scoped>
/* 示例页面不需要额外样式 */
</style>