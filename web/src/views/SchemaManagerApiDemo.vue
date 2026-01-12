<script setup lang="ts">
import { ref, onMounted } from 'vue';
import SchemaManager, { SchemaItem } from '@/components/SchemaManager/index.vue';
import { getBlocks, getSchemas, createSchema, updateSchema, deleteSchema, duplicateSchema, executeBlocks, SchemaItem as ApiSchemaItem } from '@/api/index';

// Blocks 数据从后端获取
const blocks = ref<any[]>([]);

// Schema 列表
const schemas = ref<ApiSchemaItem[]>([]);
// 当前选中的 Schema ID (string 类型，因为后端使用 UUID)
const selectedSchemaId = ref<string | null>(null);

// 从后端加载 blocks
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    console.error('Error loading blocks:', error);
  }
}

// 从后端加载 schemas
async function loadSchemas() {
  try {
    schemas.value = await getSchemas();
    if (schemas.value.length > 0 && !selectedSchemaId.value) {
      selectedSchemaId.value = schemas.value[0].id;
    }
  } catch (error) {
    console.error('Error loading schemas:', error);
  }
}

// 处理创建事件
async function handleCreate(schema: SchemaItem) {
  try {
    const newSchema = await createSchema({ name: schema.name, schema: schema.schema });
    schemas.value.push(newSchema);
    selectedSchemaId.value = newSchema.id;
  } catch (error) {
    console.error('Error creating schema:', error);
  }
}

// 处理保存事件
async function handleSave(id: string, data: any) {
  try {
    const updated = await updateSchema(id, { schema: data });
    const index = schemas.value.findIndex(s => s.id === id);
    if (index !== -1) {
      schemas.value[index] = updated;
    }
  } catch (error) {
    console.error('Error saving schema:', error);
  }
}

// 处理删除事件
async function handleDelete(id: string) {
  try {
    await deleteSchema(id);
    const index = schemas.value.findIndex(s => s.id === id);
    if (index !== -1) {
      schemas.value.splice(index, 1);
    }
    if (selectedSchemaId.value === id) {
      selectedSchemaId.value = schemas.value.length > 0 ? schemas.value[0].id : null;
    }
  } catch (error) {
    console.error('Error deleting schema:', error);
  }
}

// 处理重命名事件
async function handleRename(id: string, newName: string) {
  try {
    const updated = await updateSchema(id, { name: newName });
    const index = schemas.value.findIndex(s => s.id === id);
    if (index !== -1) {
      schemas.value[index] = updated;
    }
  } catch (error) {
    console.error('Error renaming schema:', error);
  }
}

// 处理复制事件
async function handleDuplicate(originalId: string, newSchema: SchemaItem) {
  try {
    const duplicated = await duplicateSchema(originalId, newSchema.name);
    schemas.value.push(duplicated);
    selectedSchemaId.value = duplicated.id;
  } catch (error) {
    console.error('Error duplicating schema:', error);
  }
}

async function handleRun(id: string, data: any) {
  try {
    const result = await executeBlocks({ scripts: [], data });
    alert('执行结果:\n' + JSON.stringify(result, null, 2));
  } catch (error) {
    console.error('Error executing blocks:', error);
    alert('执行失败: ' + (error instanceof Error ? error.message : String(error)));
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadBlocks();
  loadSchemas();
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