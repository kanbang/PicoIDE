<!--
 * @Descripttion: 运行监控页面 - 查看正在运行的 flow、运行状态、实时输出、生成的文件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-02-04
-->
<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue';
import {
  getRunningFlows,
  getExecution,
  getExecutionOutputs,
  stopExecution,
  streamExecutionEvents,
  getFlow,
  getBlocks,
  type ExecutionRecord,
  type OutputFile,
  type FlowItem
} from '@/api';
import LogViewer from '@/components/common/LogViewer.vue';
import FileList from '@/components/common/FileList.vue';
import type { LogEvent } from '@/components/common/types';
import { toLogEvent, type BlockDefinition } from '@/components/common/types';
import { formatAbsoluteTime, getStatusText } from '@/utils/formatters';
import { BaklavaEditor, useBaklava, Commands } from '@baklavajs/renderer-vue';
import { BuildBlock } from '@/components/NodeFlow/BlockBuilder.js';
import RefreshIcon from '@/components/icons/Refresh.vue';
import '@baklavajs/themes/dist/syrup-dark.css';

// Baklava 编辑器
const baklava = useBaklava();
const editor = baklava.editor;

// 配置编辑器
baklava.settings.sidebar.enabled = false;
baklava.settings.enableMinimap = true;
baklava.settings.toolbar.enabled = false;

// 当前 tab
const currentTab = ref<'logs' | 'outputs' | 'graph'>('logs');

// Flow 编辑器相关
const flowData = ref<any>(null);
const blocks = ref<BlockDefinition[]>([]);
const selectedFlowId = ref<string | null>(null);
const loadingFlow = ref(false);
const flowError = ref<string | null>(null);

// 用于缩放命令的 hook token
const zoomToFitToken = Symbol('ZoomToFit');

// 运行中的执行列表
const runningExecutions = ref<ExecutionRecord[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

// 当前选中的执行
const selectedExecutionId = ref<string | null>(null);
const selectedExecution = ref<ExecutionRecord | null>(null);
const executionLogs = ref<LogEvent[]>([]);
const executionOutputs = ref<OutputFile[]>([]);

// SSE 连接管理
const sseConnections = new Map<string, EventSource>();

// 计算属性
const hasRunningFlows = computed(() => runningExecutions.value.length > 0);

// 加载正在运行的 flows
async function loadRunningFlows() {
  loading.value = true;
  error.value = null;
  try {
    const result = await getRunningFlows();
    if (result.ok) {
      // 获取每个执行的详细信息
      const executions: ExecutionRecord[] = [];
      for (const execId of result.running_executions) {
        try {
          const details = await getExecution(execId);
          executions.push(details);
        } catch (e) {
          console.error(`Failed to get execution details for ${execId}:`, e);
        }
      }
      runningExecutions.value = executions;
    }
  } catch (e: any) {
    error.value = e.message || '加载失败';
    console.error('Failed to load running flows:', e);
  } finally {
    loading.value = false;
  }
}

// 选择执行
async function selectExecution(executionId: string) {
  selectedExecutionId.value = executionId;
  try {
    selectedExecution.value = await getExecution(executionId);
    // 加载输出文件
    await loadExecutionOutputs(executionId);
    // 订阅 SSE 流
    subscribeToExecution(executionId);
    // 加载 Flow 图（如果有 flow_id）
    if (selectedExecution.value?.flow_id) {
      await loadFlowGraph(selectedExecution.value.flow_id);
    } else {
      flowData.value = null;
      blocks.value = [];
      selectedFlowId.value = null;
    }
  } catch (e: any) {
    error.value = e.message || '加载执行详情失败';
    console.error('Failed to load execution:', e);
  }
}

// 加载 Flow 图
async function loadFlowGraph(flowId: string) {
  loadingFlow.value = true;
  flowError.value = null;
  try {
    // 并行加载 flow 和 blocks
    const [flowResult, blocksData] = await Promise.all([
      getFlow(flowId),
      getBlocks()
    ]);

    selectedFlowId.value = flowId;
    flowData.value = flowResult.flow;
    blocks.value = blocksData || [];

    // 注册 blocks 并加载 flow
    registerBlocks(blocks.value);
    if (flowData.value) {
      editor.load(flowData.value);
      // 使用 renderNode hook 来监听节点渲染完成
      baklava.hooks.renderNode.subscribe(zoomToFitToken, ({ node, el }) => {
        // 第一个节点渲染完成后执行缩放命令
        nextTick(() => {
          baklava.commandHandler.executeCommand<Commands.ZoomToFitGraphCommand>(
            Commands.ZOOM_TO_FIT_GRAPH_COMMAND,
            true
          );
        });
        // 只需要监听第一个节点，之后移除监听器
        baklava.hooks.renderNode.unsubscribe(zoomToFitToken);
      });
    }


  } catch (e: any) {
    flowError.value = e.message || '加载 Flow 失败';
    console.error('Failed to load flow:', e);
  } finally {
    loadingFlow.value = false;
  }
}

// 注册 Blocks
function registerBlocks(blockDefs: BlockDefinition[]) {
  // 清空现有节点
  const graph = editor.graph;
  [...graph.nodes].forEach(node => graph.removeNode(node));
  [...graph.connections].forEach(conn => graph.removeConnection(conn));

  // 注册新的 block 类型
  blockDefs.forEach((blockDef) => {
    try {
      const Block = BuildBlock({
        name: blockDef.name,
        inputs: blockDef.inputs,
        outputs: blockDef.outputs,
        options: blockDef.options
      });
      const category = 'category' in blockDef ? blockDef.category : undefined;
      editor.registerNodeType(Block, { category });
    } catch (error) {
      console.error(`注册节点 ${blockDef.name} 失败:`, error);
    }
  });
}

// 加载执行输出文件
async function loadExecutionOutputs(executionId: string) {
  try {
    const result = await getExecutionOutputs(executionId);
    executionOutputs.value = result.outputs || [];
  } catch (e: any) {
    console.error('Failed to load execution outputs:', e);
  }
}

// 订阅执行事件
function subscribeToExecution(executionId: string) {
  // 关闭所有之前的 SSE 连接（防止切换执行时连接堆积）
  sseConnections.forEach((es, id) => {
    if (id !== executionId) {
      es.close();
      sseConnections.delete(id);
    }
  });

  // 如果已经有当前执行的连接，先关闭
  if (sseConnections.has(executionId)) {
    sseConnections.get(executionId)?.close();
  }

  executionLogs.value = []; // 清空日志

  const eventSource = streamExecutionEvents(
    executionId,
    (event: any) => {
      executionLogs.value.push(toLogEvent(event));
    },
    (errorMsg: string) => {
      console.error('SSE error:', errorMsg);
    },
    () => {
      // SSE 结束，刷新执行列表
      loadRunningFlows();
      // 刷新选中的执行状态
      if (selectedExecutionId.value === executionId) {
        getExecution(executionId).then(details => {
          selectedExecution.value = details;
        });
      }
    }
  );

  sseConnections.set(executionId, eventSource);
}

// 取消订阅执行事件
function unsubscribeFromExecution(executionId: string) {
  const eventSource = sseConnections.get(executionId);
  if (eventSource) {
    eventSource.close();
    sseConnections.delete(executionId);
  }
}

// 停止执行
async function handleStop(executionId: string) {
  try {
    await stopExecution(executionId);
    // 关闭 SSE 连接
    unsubscribeFromExecution(executionId);
    // 刷新列表
    await loadRunningFlows();
    // 如果是当前选中的，刷新详情
    if (selectedExecutionId.value === executionId) {
      selectedExecution.value = await getExecution(executionId);
    }
  } catch (e: any) {
    error.value = e.message || '停止执行失败';
    console.error('Failed to stop execution:', e);
  }
}

// 格式化执行时间
function formatExecutionTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(2)}s`;
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
  }
}

// 清空日志
function clearLogs() {
  executionLogs.value = [];
}

// 删除文件
function deleteFile() {
  // FlowMonitor 中文件只读，不支持删除
  console.warn('FlowMonitor only supports viewing files, deletion is not supported');
}

// 组件挂载
onMounted(() => {
  loadRunningFlows();
});

// 组件卸载
onUnmounted(() => {
  // 关闭所有 SSE 连接
  sseConnections.forEach((es) => es.close());
  sseConnections.clear();
});
</script>

<template>
  <div class="flow-monitor">
    <div class="monitor-layout">
      <!-- 左侧：运行中的 Flow 列表 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>运行中的 Flow</h3>
          <button class="refresh-btn" @click="loadRunningFlows" :disabled="loading">
            <RefreshIcon :class="{ spinning: loading }" />
            <span>{{ loading ? '刷新中...' : '刷新' }}</span>
          </button>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div v-else-if="!hasRunningFlows && !loading" class="empty-state">
          <div class="empty-icon">📭</div>
          <p>暂无正在运行的 Flow</p>
        </div>

        <div v-else class="execution-list">
          <div v-for="exec in runningExecutions" :key="exec.execution_id"
            :class="['execution-item', { active: selectedExecutionId === exec.execution_id }]"
            @click="selectExecution(exec.execution_id)">
            <div class="execution-header">
              <span class="execution-id">{{ exec.execution_id }}</span>
              <span class="execution-status" :style="{ color: getStatusText(exec.status).color }">
                {{ getStatusText(exec.status).text }}
              </span>
            </div>
            <div class="execution-meta">
              <span>节点: {{ exec.executed_nodes }}/{{ exec.total_nodes }}</span>
              <span>{{ formatAbsoluteTime(exec.start_time) }}</span>
            </div>
            <div v-if="exec.tag" class="execution-tag">
              标签: {{ exec.tag }}
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：执行详情 -->
      <div class="detail-panel">
        <template v-if="selectedExecution">
          <!-- 执行信息头部 -->
          <div class="detail-header">
            <div class="execution-info">
              <h2>{{ selectedExecution.execution_id }}</h2>
              <span :class="['status-badge', selectedExecution.status]"
                :style="{ background: getStatusText(selectedExecution.status).color }">
                {{ getStatusText(selectedExecution.status).text }}
              </span>
            </div>
            <div class="execution-actions">
              <button v-if="selectedExecution.status === 'running'" class="stop-btn"
                @click="handleStop(selectedExecution.execution_id)">
                停止执行
              </button>
            </div>
          </div>

          <!-- 执行详情 -->
          <div class="execution-details">
            <div class="detail-row">
              <span class="label">开始时间:</span>
              <span class="value">{{ formatAbsoluteTime(selectedExecution.start_time) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">结束时间:</span>
              <span class="value">{{ selectedExecution.end_time ? formatAbsoluteTime(selectedExecution.end_time) : '-'
              }}</span>
            </div>
            <div class="detail-row">
              <span class="label">执行时长:</span>
              <span class="value">{{ selectedExecution.execution_time ?
                formatExecutionTime(selectedExecution.execution_time) : '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="label">总节点数:</span>
              <span class="value">{{ selectedExecution.total_nodes }}</span>
            </div>
            <div class="detail-row">
              <span class="label">已执行:</span>
              <span class="value">{{ selectedExecution.executed_nodes }}</span>
            </div>
            <div class="detail-row">
              <span class="label">失败节点:</span>
              <span class="value">{{ selectedExecution.failed_nodes || 0 }}</span>
            </div>
            <div v-if="selectedExecution.tag" class="detail-row">
              <span class="label">标签:</span>
              <span class="value">{{ selectedExecution.tag }}</span>
            </div>
            <div v-if="selectedExecution.source" class="detail-row">
              <span class="label">来源:</span>
              <span class="value">{{ selectedExecution.source }}</span>
            </div>
          </div>

          <!-- Tab 切换 -->
          <div class="detail-tabs">
            <button :class="['tab-btn', { active: currentTab === 'logs' }]" @click="currentTab = 'logs'">
              实时日志 ({{ executionLogs.length }})
            </button>
            <button :class="['tab-btn', { active: currentTab === 'outputs' }]" @click="currentTab = 'outputs'">
              输出文件 ({{ executionOutputs.length }})
            </button>
            <button v-if="selectedExecution?.flow_id" :class="['tab-btn', { active: currentTab === 'graph' }]"
              @click="currentTab = 'graph'">
              Flow 图
            </button>
          </div>

          <!-- 实时日志 -->
          <div v-if="currentTab === 'logs'" class="logs-panel">
            <LogViewer :events="executionLogs" :is-loading="loading" :show-filter="true" :show-header="true"
              @clear="clearLogs" />
          </div>

          <!-- 输出文件 -->
          <div v-else-if="currentTab === 'outputs'" class="outputs-panel">
            <FileList :files="executionOutputs" :show-header="false" :show-delete="false" @open="() => { }"
              @download="() => { }" @delete="deleteFile" />
          </div>

          <!-- Flow 图 -->
          <div v-else-if="currentTab === 'graph'" class="graph-panel">
            <div v-if="loadingFlow" class="loading-overlay">
              <div class="loading-spinner"></div>
              <div class="loading-text">加载 Flow 图...</div>
            </div>
            <div v-else-if="flowError" class="error-message">
              {{ flowError }}
            </div>
            <div v-else-if="!flowData" class="empty-graph">
              <div class="empty-icon">📊</div>
              <p>暂无 Flow 图数据</p>
            </div>
            <BaklavaEditor v-else :view-model="baklava" :blocks="blocks" />
          </div>
        </template>

        <!-- 未选择执行时的提示 -->
        <div v-else class="empty-selection">
          <div class="empty-icon">📋</div>
          <p>请从左侧选择一个正在运行的 Flow 查看详情</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.flow-monitor {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1e1e1e;
  color: #e0e0e0;
}

.monitor-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧边栏 */
.sidebar {
  width: 320px;
  background: #252526;
  border-right: 1px solid #3c3c3c;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  height: 48px;
  padding: 0 16px;
  border-bottom: 1px solid #3c3c3c;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #eee;
  font-weight: 600;
}

.refresh-btn {
  background: transparent;
  border: none;
  color: #888;
  width: auto;
  min-width: 70px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  transition: all 0.2s;
  padding: 0 6px;
}

.refresh-btn:hover:not(:disabled) {
  background: #37373d;
  color: #fff;
}

.refresh-btn svg {
  width: 20px;
  height: 20px;
}

.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}

.refresh-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.error-message {
  padding: 16px;
  color: #f44336;
  text-align: center;
  font-size: 13px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 20px;
  opacity: 0.2;
}

.empty-state p {
  font-size: 12px;
  line-height: 1.6;
}

.execution-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.execution-item {
  background: #252526;
  border: 1px solid #333;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  gap: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  margin-bottom: 8px;
}

.execution-item:hover {
  background: #2d2d30;
  border-color: #444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.execution-item.active {
  background: #2d2d30;
  border-left: 4px solid #4caf50;
  border-right: none;
  border-top: none;
  border-bottom: none;
}

.execution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.execution-id {
  font-family: 'Consolas', monospace;
  font-size: 13px;
  color: #9cdcfe;
  font-weight: 500;
}

.execution-status {
  font-size: 11px;
  font-weight: 500;
}

.execution-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #888;
}

.execution-meta>span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.execution-tag {
  margin-top: 2px;
  font-size: 11px;
  color: #4caf50;
  font-weight: 500;
}

/* 滚动条美化 */
.execution-list::-webkit-scrollbar {
  width: 10px;
}

.execution-list::-webkit-scrollbar-track {
  background: transparent;
}

.execution-list::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 10px;
  border: 3px solid #252526;
}

.execution-list::-webkit-scrollbar-thumb:hover {
  background: #444;
}

/* 右侧详情面板 */
.detail-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  padding: 12px 20px;
  background: #2d2d30;
  border-bottom: 1px solid #3c3c3c;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.execution-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.execution-info h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  font-family: 'Consolas', monospace;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  color: white;
}

.execution-actions {
  display: flex;
  gap: 8px;
}

.stop-btn {
  padding: 6px 16px;
  background: #f44336;
  border: none;
  color: white;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.stop-btn:hover {
  background: #d32f2f;
}

.execution-details {
  padding: 16px 20px;
  border-bottom: 1px solid #3c3c3c;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.detail-row {
  display: flex;
  gap: 12px;
}

.detail-row .label {
  color: #888;
  font-size: 12px;
  min-width: 80px;
}

.detail-row .value {
  color: #e0e0e0;
  font-size: 12px;
}

/* Tab 切换 */
.detail-tabs {
  display: flex;
  border-bottom: 1px solid #3c3c3c;
  background: #2d2d30;
}

.tab-btn {
  padding: 10px 20px;
  background: transparent;
  border: none;
  color: #888;
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: #e0e0e0;
  background: rgba(255, 255, 255, 0.05);
}

.tab-btn.active {
  color: #4caf50;
  border-bottom-color: #4caf50;
}

/* 日志面板 */
.logs-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1e1e1e;
}

/* 输出文件面板 */
.outputs-panel {
  flex: 1;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 8px;
}

/* Flow 图面板 */
.graph-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1e1e1e;
  position: relative;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(30, 30, 30, 0.8);
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #3c3c3c;
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-text {
  margin-top: 16px;
  color: #888;
  font-size: 14px;
}

.empty-graph {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #666;
}

.empty-graph .empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.2;
}

.empty-graph p {
  font-size: 14px;
}

/* Baklava 样式覆盖 */
.graph-panel :deep(.baklava-editor) {
  height: 100%;
  width: 100%;
}

.graph-panel :deep(.baklava-node-palette) {
  display: none !important;
}

/* 未选择时的提示 */
.empty-selection {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #666;
}

.empty-selection .empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-selection p {
  font-size: 14px;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #1e1e1e;
}

::-webkit-scrollbar-thumb {
  background: #3c3c3c;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #4a4a4a;
}
</style>
