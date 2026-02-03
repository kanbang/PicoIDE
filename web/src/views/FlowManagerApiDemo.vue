<script setup lang="ts">
import { ref, onMounted } from 'vue';
import FlowManager, { FlowItem } from '@/components/FlowManager/index.vue';
import {
  getBlocks, getFlows, createFlow, updateFlow,
  deleteFlow, duplicateFlow, executeBlocks, executeSavedFlow, stopExecution,
  FlowItem as ApiFlowItem
} from '@/api/index';
import { showSuccess, showError, showInfo } from '@/utils/toast';

// --- 响应式状态 ---
const blocks = ref<any[]>([]);
const flows = ref<ApiFlowItem[]>([]);
const selectedFlowId = ref<string | null>(null);
const currentExecutionId = ref<string | null>(null);

// 引用 FlowManager 实例
const flowManagerRef = ref<InstanceType<typeof FlowManager> | null>(null);

// --- 数据加载 ---
async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    showError('加载节点定义失败');
  }
}

async function loadFlows() {
  try {
    flows.value = await getFlows();
    // 默认选中第一个
    if (flows.value.length > 0 && !selectedFlowId.value) {
      selectedFlowId.value = flows.value[0].id;
    }
  } catch (error) {
    showError('加载 Flow 列表失败');
  }
}

// --- Flow 操作逻辑 ---
async function handleCreate(flow: FlowItem) {
  try {
    const newFlow = await createFlow({ name: flow.name, flow: flow.flow });
    flows.value.push(newFlow);
    selectedFlowId.value = newFlow.id;
    showSuccess('创建成功');
  } catch (error) {
    showError('创建失败');
  }
}

async function handleSave(id: string, data: any) {
  try {
    const updated = await updateFlow(id, { flow: data });
    const index = flows.value.findIndex(s => s.id === id);
    if (index !== -1) flows.value[index] = updated;
    showSuccess('保存成功');
  } catch (error) {
    showError('保存失败');
  }
}

async function handleDelete(id: string) {
  try {

    let newSelectedId: string | null = null;
    if (selectedFlowId.value === id) {
      if (flows.value.length > 1) {
        const currentIndex = flows.value.findIndex(s => s.id === id);
        if (currentIndex == flows.value.length - 1) {
          newSelectedId = flows.value[currentIndex - 1].id;
        } else {
          newSelectedId = flows.value[currentIndex + 1].id;
        }
      }
    }

    await deleteFlow(id);
    flows.value = flows.value.filter(s => s.id !== id);


    if (newSelectedId !== null) {
      selectedFlowId.value = newSelectedId;
    }

    showSuccess('删除成功');
  } catch (error) {
    showError('删除失败');
  }
}

async function handleRename(id: string, newName: string) {
  try {
    const updated = await updateFlow(id, { name: newName });
    const index = flows.value.findIndex(s => s.id === id);
    if (index !== -1) flows.value[index] = updated;
  } catch (error) {
    showError('重命名失败');
  }
}

async function handleDuplicate(originalId: string, newFlow: FlowItem) {
  try {
    const duplicated = await duplicateFlow(originalId, newFlow.name);
    flows.value.push(duplicated);
    selectedFlowId.value = duplicated.id;
    showSuccess('复制成功');
  } catch (error) {
    showError('复制失败');
  }
}

// --- 核心执行逻辑 (重构重点) ---
async function handleRun(id: string, flow: any) {
  // 1. 获取 NodeFlow 实例引用
  const nodeFlowInstance = flowManagerRef.value?.nodeFlowRef;
  if (!nodeFlowInstance) return;

  // 2. 检查并保存未保存的更改
  const currentFlow = flows.value.find(f => f.id === id);
  if (currentFlow && currentFlow.hasUnsavedChanges) {
    try {
      // 保存当前 Flow
      await handleSave(id, flow);
      currentFlow.hasUnsavedChanges = false;
      showInfo('已自动保存未保存的更改');
    } catch (error) {
      showError('保存失败，无法执行');
      return;
    }
  }

  // 3. 自动展开输出面板 (体验优化)
  nodeFlowInstance.showOutputPanel();

  const outputPanel = nodeFlowInstance.outputPanelRef;

  try {
    console.log('执行 Flow:', id);


    // 5. 调用 API (使用 execute-saved 接口)
    const result = await executeSavedFlow(id);

    // 6. 设置 SSE 面板的 execution_id（开始接收流式日志）
    if (result.execution_id) {
      nodeFlowInstance.setCurrentExecutionId(result.execution_id);
      currentExecutionId.value = result.execution_id;
    }

    // 7. 更新输出面板结果
    if (outputPanel) {
      outputPanel.setOutputFiles(result.output_files || []);
      if (result.ok) {
        // 更新 UI 为运行中状态
        outputPanel.setExecutionStatus('running');
        showSuccess(`开始执行，执行 ID: ${result.execution_id}`);
      } else {
        showInfo('执行请求已发送，但返回失败状态');
      }
    }

  } catch (error: any) {
    console.error('执行失败:', error);
    if (outputPanel) {
      outputPanel.setExecutionStatus('failed');
      outputPanel.setErrors([error?.message || String(error)]);
    }
    showError('执行失败: ' + (error?.message || '未知错误'));

    // 清空当前执行 ID
    currentExecutionId.value = null;
  }
}

// --- 停止执行逻辑 ---
async function handleStop(executionId?: string) {
  try {
    const idToStop = executionId || currentExecutionId.value;
    if (!idToStop) {
      showError('没有正在执行的流程可停止');
      return;
    }

    console.log('停止执行:', idToStop);

    // 先设置 stopping 状态（在 API 调用前，避免被 SSE 事件覆盖）
    const nodeFlowInstance = flowManagerRef.value?.nodeFlowRef;
    const outputPanel = nodeFlowInstance?.outputPanelRef;
    if (outputPanel) {
      outputPanel.setExecutionStatus('stopping');
    }

    // 调用 API 停止执行
    const result = await stopExecution(idToStop);

    if (result.ok) {
      showInfo('已发送停止请求');
    } else {
      showError('停止执行失败');
    }
  } catch (error: any) {
    console.error('停止执行失败:', error);
    showError('停止执行失败: ' + (error?.message || '未知错误'));
  }
}

// --- 执行结束事件处理 ---
function handleExecutionEnded(executionId: string) {
  console.log('执行结束:', executionId);
  // 只有当结束的执行是当前正在执行的时才清空 currentExecutionId
  if (currentExecutionId.value === executionId) {
    currentExecutionId.value = null;
  }
}

// --- 初始化 ---
onMounted(() => {
  loadBlocks();
  loadFlows();
});
</script>

<template>
  <div class="manager-page-wrapper">
    <FlowManager ref="flowManagerRef" v-model:flows="flows" v-model:selected-flow-id="selectedFlowId" :blocks="blocks"
      :show-run="true" @run="handleRun" @stop="handleStop" @executionEnded="handleExecutionEnded" @create="handleCreate"
      @save="handleSave" @delete="handleDelete" @rename="handleRename" @duplicate="handleDuplicate" />
  </div>
</template>

<style scoped>
.manager-page-wrapper {
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>