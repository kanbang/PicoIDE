<!--
 * @Descripttion: 单个 NodeFlow 编辑器
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import NodeFlow from '@/components/NodeFlow/index.vue'
import { ref, onMounted } from 'vue';
import { getBlocks, executeBlocks } from '@/api/index';

// Props
// Blocks 数据从后端获取
const blocks = ref<any[]>([]);

const STORAGE_KEY = 'nodeflow_schema';

// 从后端加载 blocks
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    console.error('Error loading blocks:', error);
  }
}

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

async function handleRun(data: any) {
  try {
    console.log(data);
    const result = await executeBlocks({ scripts: [], data });
    alert('执行结果:\n' + JSON.stringify(result, null, 2));
  } catch (error) {
    console.error('Error executing blocks:', error);
    alert('执行失败: ' + (error instanceof Error ? error.message : String(error)));
  }
}

// 组件挂载后加载存储的数据
onMounted(() => {
  loadBlocks();
  loadFromStorage();
});

</script>

<template>
  <div class="single-node-flow">
    <NodeFlow ref="nodeFlowRef" :blocks="blocks" :show-run="true" @run="handleRun" @save="handleSave"
      @update="handleUpdate" @unsaved-changes="handleUnsavedChanges" />
  </div>
</template>

<style scoped>
.single-node-flow {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>