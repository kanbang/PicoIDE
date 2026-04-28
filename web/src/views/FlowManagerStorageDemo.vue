<script setup lang="ts">
import { ref, onMounted } from 'vue';
import FlowManager, { type FlowItem } from '@/components/FlowManager/index.vue'; // 确保路径正确，原代码是 @/components/...
import { getBlocks } from '@/api/index';

const STORAGE_KEY = 'flow_manager_example_data';

// Blocks 数据从后端获取
const blocks = ref<any[]>([]);

// Flow 列表
const flows = ref<FlowItem[]>([]);
// 当前选中的 Flow ID
const selectedFlowId = ref<string | null>(null);

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
      flows.value = data.flows || [];
      selectedFlowId.value = data.selectedFlowId || null;
    } catch (e) {
      console.error('Failed to parse saved data:', e);
    }
  }
}

// 保存到 localStorage
function saveToStorage(): void {
  const data = {
    flows: flows.value,
    selectedFlowId: selectedFlowId.value
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// 处理创建事件
function handleCreate(flow: FlowItem): void {
  console.log('handleCreate called with flow:', flow);
  // 生成 ID
  const newFlowWithId = {
    ...flow,
    id: crypto.randomUUID()
  };
  flows.value.push(newFlowWithId);
  // 自动选中新创建的 flow
  selectedFlowId.value = newFlowWithId.id;
  console.log('After push, flows:', flows.value);
  saveToStorage();
}

// 处理保存事件
function handleSave(id: string, data: any): void {
  const flow = flows.value.find((s: FlowItem) => s.id === id);
  if (flow) {
    flow.flow = data;
    saveToStorage();
  }
}

// 处理删除事件
function handleDelete(id: string): void {
  const index = flows.value.findIndex((s: FlowItem) => s.id === id);
  if (index > -1) {
    flows.value.splice(index, 1);
    saveToStorage();
  }
}

// 处理重命名事件
function handleRename(id: string, newName: string): void {
  const flow = flows.value.find((s: FlowItem) => s.id === id);
  if (flow) {
    flow.name = newName;
    saveToStorage();
  }
}

// 处理复制事件
function handleDuplicate(originalId: string, newFlow: FlowItem): void {
  // 生成 ID
  const newFlowWithId: FlowItem = {
    ...newFlow,
    id: crypto.randomUUID()
  };
  flows.value.push(newFlowWithId);
  // 自动选中新复制的 flow
  selectedFlowId.value = newFlowWithId.id;
  saveToStorage();
}

function handleRun(id: string, data: any) {
  alert('run: \n' + id + '\n' + JSON.stringify(data));
}

// 组件挂载时加载数据
onMounted(() => {
  loadBlocks();
  loadFromStorage();

  // 如果没有 flow，创建一个默认的
  // if (flows.value.length === 0) {
  //   const defaultFlow: FlowItem = {
  //     id: crypto.randomUUID(),
  //     name: 'Flow 1',
  //     flow: null,
  //     hasUnsavedChanges: false
  //   };
  //   flows.value.push(defaultFlow);
  //   selectedFlowId.value = defaultFlow.id;
  //   saveToStorage();
  // }
});
</script>

<template>
  <FlowManager v-model:flows="flows" v-model:selected-flow-id="selectedFlowId" :blocks="blocks"
    :show-run="true" @run="handleRun" @create="handleCreate" @save="handleSave" @delete="handleDelete"
    @rename="handleRename" @duplicate="handleDuplicate" />
</template>

<style scoped>
/* 示例页面不需要额外样式 */
</style>