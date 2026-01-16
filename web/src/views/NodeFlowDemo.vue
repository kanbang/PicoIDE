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
    console.log('执行Block图:', data);
    
    // 设置执行状态为运行中
    if (nodeFlowRef.value?.outputPanelRef) {
      nodeFlowRef.value.outputPanelRef.setExecutionStatus('running');
    }
    
    // 调用执行API
    const result = await executeBlocks({ scripts: [], data });
    
    console.log('执行结果:', result);
    
    // 更新输出面板
    if (nodeFlowRef.value?.outputPanelRef && result.output_files) {
      nodeFlowRef.value.outputPanelRef.setExecutionStatus('completed', result.execution_time);
      nodeFlowRef.value.outputPanelRef.setOutputFiles(result.output_files);
      
      if (result.output_files.length > 0) {
        showToast(`执行完成，生成了 ${result.output_files.length} 个输出文件`, 'success');
      } else {
        showToast('执行完成，但未生成输出文件', 'info');
      }
    }
    
  } catch (error) {
    console.error('执行失败:', error);
    
    // 更新输出面板状态为失败
    if (nodeFlowRef.value?.outputPanelRef) {
      nodeFlowRef.value.outputPanelRef.setExecutionStatus('failed');
      nodeFlowRef.value.outputPanelRef.setErrors([error instanceof Error ? error.message : String(error)]);
    }
    
    showToast('执行失败: ' + (error instanceof Error ? error.message : String(error)), 'error');
  }
}

// 原生 toast 提示
function showToast(message: string, type: 'success' | 'error' | 'info' = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  
  document.body.appendChild(toast);
  
  // 触发动画
  requestAnimationFrame(() => {
    toast.classList.add('toast-show');
  });
  
  // 3秒后移除
  setTimeout(() => {
    toast.classList.remove('toast-show');
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 300);
  }, 3000);
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

<style>
/* Toast 提示样式 */
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  padding: 12px 20px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  opacity: 0;
  transform: translateY(-20px);
  transition: all 0.3s ease;
  z-index: 9999;
}

.toast-show {
  opacity: 1;
  transform: translateY(0);
}

.toast-success {
  background: #10b981;
}

.toast-error {
  background: #ef4444;
}

.toast-info {
  background: #3b82f6;
}
</style>

<style scoped>
.single-node-flow {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>