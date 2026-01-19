<script setup lang="ts">
import { ref, onMounted } from 'vue';
import SchemaManager, { SchemaItem } from '@/components/SchemaManager/index.vue';
import {
  getBlocks, getSchemas, createSchema, updateSchema,
  deleteSchema, duplicateSchema, executeBlocks,
  SchemaItem as ApiSchemaItem
} from '@/api/index';
import { showSuccess, showError, showInfo } from '@/utils/toast';

// --- 响应式状态 ---
const blocks = ref<any[]>([]);
const schemas = ref<ApiSchemaItem[]>([]);
const selectedSchemaId = ref<string | null>(null);

// 引用 SchemaManager 实例
const schemaManagerRef = ref<InstanceType<typeof SchemaManager> | null>(null);

// --- 数据加载 ---
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    showError('加载节点定义失败');
  }
}

async function loadSchemas() {
  try {
    schemas.value = await getSchemas();
    // 默认选中第一个
    if (schemas.value.length > 0 && !selectedSchemaId.value) {
      selectedSchemaId.value = schemas.value[0].id;
    }
  } catch (error) {
    showError('加载 Schema 列表失败');
  }
}

// --- Schema 操作逻辑 ---
async function handleCreate(schema: SchemaItem) {
  try {
    const newSchema = await createSchema({ name: schema.name, schema: schema.schema });
    schemas.value.push(newSchema);
    selectedSchemaId.value = newSchema.id;
    showSuccess('创建成功');
  } catch (error) {
    showError('创建失败');
  }
}

async function handleSave(id: string, data: any) {
  try {
    const updated = await updateSchema(id, { schema: data });
    const index = schemas.value.findIndex(s => s.id === id);
    if (index !== -1) schemas.value[index] = updated;
    showSuccess('保存成功');
  } catch (error) {
    showError('保存失败');
  }
}

async function handleDelete(id: string) {
  try {

    let newSelectedId: string | null = null;
    if (selectedSchemaId.value === id) {
      if (schemas.value.length > 1) {
        const currentIndex = schemas.value.findIndex(s => s.id === id);
        if (currentIndex == schemas.value.length - 1) {
          newSelectedId = schemas.value[currentIndex - 1].id;
        } else {
          newSelectedId = schemas.value[currentIndex + 1].id;
        }
      }
    }

    await deleteSchema(id);
    schemas.value = schemas.value.filter(s => s.id !== id);


    if (newSelectedId !== null) {
      selectedSchemaId.value = newSelectedId;
    }

    showSuccess('删除成功');
  } catch (error) {
    showError('删除失败');
  }
}

async function handleRename(id: string, newName: string) {
  try {
    const updated = await updateSchema(id, { name: newName });
    const index = schemas.value.findIndex(s => s.id === id);
    if (index !== -1) schemas.value[index] = updated;
  } catch (error) {
    showError('重命名失败');
  }
}

async function handleDuplicate(originalId: string, newSchema: SchemaItem) {
  try {
    const duplicated = await duplicateSchema(originalId, newSchema.name);
    schemas.value.push(duplicated);
    selectedSchemaId.value = duplicated.id;
    showSuccess('复制成功');
  } catch (error) {
    showError('复制失败');
  }
}

// --- 核心执行逻辑 (重构重点) ---
async function handleRun(id: string, schema: any) {
  // 1. 获取 NodeFlow 实例引用
  const nodeFlowInstance = schemaManagerRef.value?.nodeFlowRef;
  if (!nodeFlowInstance) return;

  // 2. 自动展开输出面板 (体验优化)
  nodeFlowInstance.showOutputPanel();

  const outputPanel = nodeFlowInstance.outputPanelRef;

  try {
    console.log('执行 Schema:', id);

    // 3. 更新 UI 为运行中
    outputPanel?.setExecutionStatus('running');

    // 4. 调用 API
    const result = await executeBlocks({ scripts: [], schema });

    // 5. 更新输出面板结果
    if (outputPanel) {
      outputPanel.setExecutionStatus('completed', result.execution_time);
      outputPanel.setOutputFiles(result.output_files || []);

      if (result.output_files?.length > 0) {
        showSuccess(`执行完成，生成 ${result.output_files.length} 个文件`);
      } else {
        showInfo('执行完成，无输出内容');
      }
    }

  } catch (error: any) {
    console.error('执行失败:', error);
    if (outputPanel) {
      outputPanel.setExecutionStatus('failed');
      outputPanel.setErrors([error?.message || String(error)]);
    }
    showError('执行失败: ' + (error?.message || '未知错误'));
  }
}

// --- 初始化 ---
onMounted(() => {
  loadBlocks();
  loadSchemas();
});
</script>

<template>
  <div class="manager-page-wrapper">
    <SchemaManager ref="schemaManagerRef" v-model:schemas="schemas" v-model:selected-schema-id="selectedSchemaId"
      :blocks="blocks" :show-run="true" @run="handleRun" @create="handleCreate" @save="handleSave"
      @delete="handleDelete" @rename="handleRename" @duplicate="handleDuplicate" />
  </div>
</template>

<style scoped>
.manager-page-wrapper {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}
</style>