<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import NodeFlow from '@/components/NodeFlow/index.vue';
import {
  createFlow,
  executeSavedFlow,
  getBlocks,
  stopExecution,
  updateFlow,
} from '@/api/index';
import { useBusinessStore } from '@/stores/business';
import { buildTempFlowName, buildTempFlowPayload } from '@/utils/tempFlow';
import { showError, showInfo, showSuccess } from '@/utils/toast';

const businessStore = useBusinessStore();

const STORAGE_KEY = computed(() => `nodeflow_flow_${businessStore.business}`);
const TEMP_FLOW_ID_KEY = computed(() => `nodeflow_temp_flow_id_${businessStore.business}`);
const TEMP_FLOW_NAME = computed(() => buildTempFlowName(businessStore.business));

const blocks = ref<any[]>([]);
const hasUnsavedChanges = ref(false);
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);
const currentExecutionId = ref<string | null>(null);

async function loadBlocks() {
  try {
    blocks.value = await getBlocks();
  } catch (error) {
    console.error('Failed to load blocks:', error);
    showError('无法获取节点定义，请检查网络');
  }
}

function loadFromStorage(): void {
  const savedSchema = localStorage.getItem(STORAGE_KEY.value);
  if (!savedSchema) {
    return;
  }

  try {
    const flow = JSON.parse(savedSchema);
    nodeFlowRef.value?.loadFlow(flow);
  } catch (error) {
    console.error('Failed to parse local flow:', error);
  }
}

function handleSave(data: any): void {
  localStorage.setItem(STORAGE_KEY.value, JSON.stringify(data));
  hasUnsavedChanges.value = false;
  showSuccess('保存成功');
}

function handleUnsavedChanges(changes: boolean): void {
  hasUnsavedChanges.value = changes;
}

async function ensureRemoteTempFlow(flow: any): Promise<string> {
  const flowId = localStorage.getItem(TEMP_FLOW_ID_KEY.value);
  const remoteFlow = buildTempFlowPayload(flow);

  if (flowId) {
    try {
      await updateFlow(flowId, {
        name: TEMP_FLOW_NAME.value,
        flow: remoteFlow,
      });
      return flowId;
    } catch (error) {
      console.warn('Failed to update temp flow, recreating it:', error);
      localStorage.removeItem(TEMP_FLOW_ID_KEY.value);
    }
  }

  const createdFlow = await createFlow({
    name: TEMP_FLOW_NAME.value,
    flow: remoteFlow,
  });

  localStorage.setItem(TEMP_FLOW_ID_KEY.value, createdFlow.id);
  return createdFlow.id;
}

async function handleRun(flow: any) {
  if (!nodeFlowRef.value) {
    return;
  }

  nodeFlowRef.value.showOutputPanel();
  const outputPanel = nodeFlowRef.value.outputPanelRef;

  try {
    if (outputPanel) {
      outputPanel.resetExecutionOutput();
      outputPanel.setExecutionStatus('running');
    }

    const flowId = await ensureRemoteTempFlow(flow);
    const result = await executeSavedFlow(flowId);

    currentExecutionId.value = result.execution_id;
    nodeFlowRef.value.setCurrentExecutionId(result.execution_id);

    showSuccess(`开始执行，执行 ID: ${result.execution_id}`);
  } catch (error: any) {
    console.error('Execution failed:', error);

    if (outputPanel) {
      outputPanel.setExecutionStatus('failed');
      outputPanel.setErrors([error?.message || String(error)]);
    }

    showError('执行失败: ' + (error?.message || '未知错误'));
  }
}

async function handleStop(executionId?: string) {
  const idToStop = executionId || currentExecutionId.value;
  if (!idToStop) {
    showError('没有正在执行的流程可停止');
    return;
  }

  try {
    const outputPanel = nodeFlowRef.value?.outputPanelRef;
    if (outputPanel) {
      outputPanel.setExecutionStatus('stopping');
    }

    const result = await stopExecution(idToStop);
    if (result.ok) {
      showInfo('已发送停止请求');
    } else {
      showError('停止执行失败');
    }
  } catch (error: any) {
    console.error('Stop execution failed:', error);
    showError('停止执行失败: ' + (error?.message || '未知错误'));
  }
}

function handleExecutionEnded(executionId: string) {
  if (currentExecutionId.value === executionId) {
    currentExecutionId.value = null;
    nodeFlowRef.value?.setCurrentExecutionId(null);
  }
}

onMounted(async () => {
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
      @stop="handleStop"
      @executionEnded="handleExecutionEnded"
      @save="handleSave"
      @unsaved-changes="handleUnsavedChanges"
    />
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
</style>
