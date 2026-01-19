<script setup lang="ts">
import { ref, onMounted } from 'vue';
import NodeFlow from '@/components/NodeFlow/index.vue';
import { getBlocks, executeBlocks } from '@/api/index';
import { showSuccess, showError, showInfo } from '@/utils/toast';

const STORAGE_KEY = 'nodeflow_schema';

// --- 响应式状态 ---
const blocks = ref<any[]>([]);
const hasUnsavedChanges = ref(false);
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// --- 数据加载逻辑 ---

// 加载节点定义 (Blocks)
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    console.error('加载节点失败:', error);
    showError('无法获取节点定义，请检查网络');
  }
}

// 从本地存储还原画布
function loadFromStorage(): void {
  const savedSchema = localStorage.getItem(STORAGE_KEY);
  if (savedSchema) {
    try {
      const schema = JSON.parse(savedSchema);
      // 调用 NodeFlow 暴露的 loadSchema 方法
      nodeFlowRef.value?.loadSchema(schema);
    } catch (e) {
      console.error('解析本地存储失败:', e);
    }
  }
}

// --- 事件处理 ---

// 处理保存：持久化到本地
function handleSave(data: any): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  hasUnsavedChanges.value = false;
  showSuccess('保存成功');
}

// 处理未保存状态：用于 UI 提示或路由守卫
function handleUnsavedChanges(changes: boolean): void {
  hasUnsavedChanges.value = changes;
}

// 处理运行逻辑
async function handleRun(schema: any) {
  if (!nodeFlowRef.value) return;

  // 1. 自动展开输出面板 (利用 NodeFlow 暴露的 API)
  nodeFlowRef.value.showOutputPanel();

  const outputPanel = nodeFlowRef.value.outputPanelRef;

  try {
    console.log('开始执行流程...', schema);
    
    // 2. 更新 UI 状态为运行中
    if (outputPanel) {
      outputPanel.setExecutionStatus('running');
    }
    
    // 3. 调用后端执行 API
    const result = await executeBlocks({ scripts: [], schema });
    
    // 4. 处理执行结果
    if (outputPanel) {
      outputPanel.setExecutionStatus('completed', result.execution_time);
      outputPanel.setOutputFiles(result.output_files || []);
      
      if (result.output_files?.length > 0) {
        showSuccess(`执行成功，生成 ${result.output_files.length} 个文件`);
      } else {
        showInfo('执行完成，无输出文件');
      }
    }
    
  } catch (error: any) {
    console.error('运行出错:', error);
    
    // 5. 更新 UI 状态为失败
    if (outputPanel) {
      outputPanel.setExecutionStatus('failed');
      outputPanel.setErrors([error?.message || String(error)]);
    }
    
    showError('运行失败: ' + (error?.message || '未知错误'));
  }
}

// --- 生命周期 ---
onMounted(async () => {
  // 先加载 Blocks 定义，确保画布渲染节点时能找到对应的 Block 类型
  await loadBlocks();
  loadFromStorage();
});
</script>

<template>
  <div class="single-node-flow-container">
    <NodeFlow 
      ref="nodeFlowRef" 
      :blocks="blocks" 
      :show-run="true" 
      @run="handleRun" 
      @save="handleSave"
      @unsaved-changes="handleUnsavedChanges" 
    />
    
    <!-- <div v-if="hasUnsavedChanges" class="unsaved-badge">
      未保存的更改
    </div> -->
  </div>
</template>

<style scoped>
.single-node-flow-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background-color: #1a1a1a;
}

.unsaved-badge {
  position: absolute;
  top: 10px;
  right: 80px; /* 避开 Toolbar */
  padding: 4px 12px;
  background: rgba(255, 152, 0, 0.2);
  border: 1px solid #ff9800;
  color: #ff9800;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
}
</style>