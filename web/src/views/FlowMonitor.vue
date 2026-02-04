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
  type ExecutionRecord,
  type OutputFile
} from '@/api';

// 全局类型定义
export interface RuntimeEvent {
  type: string;
  execution_id: string;
  timestamp: string;
  data?: any;
  node_id?: string;
  node_name?: string;
  message?: string;
  error?: string;
}

// 当前 tab
const currentTab = ref<'logs' | 'outputs'>('logs');

// 运行中的执行列表
const runningExecutions = ref<ExecutionRecord[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

// 当前选中的执行
const selectedExecutionId = ref<string | null>(null);
const selectedExecution = ref<ExecutionRecord | null>(null);
const executionLogs = ref<RuntimeEvent[]>([]);
const executionOutputs = ref<OutputFile[]>([]);

// SSE 连接管理
const sseConnections = new Map<string, EventSource>();
const refreshInterval = ref<number | null>(null);

// 计算属性
const hasRunningFlows = computed(() => runningExecutions.value.length > 0);

// 获取状态显示文本
function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    'running': '运行中',
    'completed': '已完成',
    'failed': '失败',
    'stopped': '已停止'
  };
  return statusMap[status] || status;
}

// 获取状态颜色
function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    'running': '#4caf50',
    'completed': '#2196f3',
    'failed': '#f44336',
    'stopped': '#ff9800'
  };
  return colorMap[status] || '#999';
}

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
  } catch (e: any) {
    error.value = e.message || '加载执行详情失败';
    console.error('Failed to load execution:', e);
  }
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
  // 关闭之前的连接
  if (sseConnections.has(executionId)) {
    sseConnections.get(executionId)?.close();
  }

  executionLogs.value = []; // 清空日志

  const eventSource = streamExecutionEvents(
    executionId,
    (event: RuntimeEvent) => {
      executionLogs.value.push(event);
      // 滚动到底部
      nextTick(() => {
        const container = document.querySelector('.logs-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
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

// 打开输出文件
function openOutputFile(file: OutputFile) {
  window.open(`/api/engine/output-files/${file.file_id}`, '_blank');
}

// 下载输出文件
function downloadOutputFile(file: OutputFile) {
  const link = document.createElement('a');
  link.href = `/api/engine/output-files/${file.file_id}`;
  link.download = file.filename;
  link.click();
}

// 格式化文件大小
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// 格式化时间
function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString('zh-CN');
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

// 组件挂载
onMounted(() => {
  loadRunningFlows();
  // 定时刷新运行列表
  // refreshInterval.value = window.setInterval(() => {
  //   if (!loading.value) {
  //     loadRunningFlows();
  //   }
  // }, 3000); // 每3秒刷新一次
});

// 组件卸载
onUnmounted(() => {
  // 清除定时器
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
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
            {{ loading ? '刷新中...' : '刷新' }}
          </button>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <div v-else-if="!hasRunningFlows && !loading" class="empty-state">
          <div class="empty-icon">🚫</div>
          <p>暂无正在运行的 Flow</p>
        </div>

        <div v-else class="execution-list">
          <div
            v-for="exec in runningExecutions"
            :key="exec.execution_id"
            :class="['execution-item', { active: selectedExecutionId === exec.execution_id }]"
            @click="selectExecution(exec.execution_id)"
          >
            <div class="execution-header">
              <span class="execution-id">{{ exec.execution_id }}</span>
              <span class="execution-status" :style="{ color: getStatusColor(exec.status) }">
                {{ getStatusText(exec.status) }}
              </span>
            </div>
            <div class="execution-meta">
              <span>节点: {{ exec.executed_nodes }}/{{ exec.total_nodes }}</span>
              <span>{{ formatTime(exec.start_time) }}</span>
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
              <span :class="['status-badge', selectedExecution.status]" :style="{ background: getStatusColor(selectedExecution.status) }">
                {{ getStatusText(selectedExecution.status) }}
              </span>
            </div>
            <div class="execution-actions">
              <button
                v-if="selectedExecution.status === 'running'"
                class="stop-btn"
                @click="handleStop(selectedExecution.execution_id)"
              >
                停止执行
              </button>
            </div>
          </div>

          <!-- 执行详情 -->
          <div class="execution-details">
            <div class="detail-row">
              <span class="label">开始时间:</span>
              <span class="value">{{ formatTime(selectedExecution.start_time) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">结束时间:</span>
              <span class="value">{{ selectedExecution.end_time ? formatTime(selectedExecution.end_time) : '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="label">执行时长:</span>
              <span class="value">{{ selectedExecution.execution_time ? formatExecutionTime(selectedExecution.execution_time) : '-' }}</span>
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
            <button
              :class="['tab-btn', { active: currentTab === 'logs' }]"
              @click="currentTab = 'logs'"
            >
              实时日志
            </button>
            <button
              :class="['tab-btn', { active: currentTab === 'outputs' }]"
              @click="currentTab = 'outputs'"
            >
              输出文件 ({{ executionOutputs.length }})
            </button>
          </div>

          <!-- 实时日志 -->
          <div v-if="currentTab === 'logs'" class="logs-panel">
            <div class="logs-header">
              <span>实时输出</span>
              <button class="clear-btn" @click="clearLogs">清空</button>
            </div>
            <div class="logs-container">
              <div v-if="executionLogs.length === 0" class="logs-empty">
                等待日志输出...
              </div>
              <div v-else class="log-list">
                <div
                  v-for="(log, index) in executionLogs"
                  :key="index"
                  :class="['log-entry', `log-${log.type}`]"
                >
                  <span class="log-time">{{ formatTime(log.timestamp) }}</span>
                  <span v-if="log.node_name" class="log-node">{{ log.node_name }}</span>
                  <span v-if="log.message" class="log-message">{{ log.message }}</span>
                  <span v-if="log.error" class="log-error">{{ log.error }}</span>
                  <pre v-if="log.data" class="log-data">{{ JSON.stringify(log.data, null, 2) }}</pre>
                </div>
              </div>
            </div>
          </div>

          <!-- 输出文件 -->
          <div v-else class="outputs-panel">
            <div v-if="executionOutputs.length === 0" class="outputs-empty">
              暂无输出文件
            </div>
            <div v-else class="outputs-list">
              <div
                v-for="file in executionOutputs"
                :key="file.file_id"
                class="output-item"
              >
                <div class="output-info">
                  <div class="output-filename">{{ file.filename }}</div>
                  <div class="output-meta">
                    <span>{{ formatFileSize(file.file_size) }}</span>
                    <span>{{ formatTime(file.created_at) }}</span>
                  </div>
                </div>
                <div class="output-actions">
                  <button
                    v-if="file.can_open"
                    class="open-btn"
                    @click="openOutputFile(file)"
                  >
                    打开
                  </button>
                  <button
                    class="download-btn"
                    @click="downloadOutputFile(file)"
                  >
                    下载
                  </button>
                </div>
              </div>
            </div>
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
  padding: 12px 16px;
  border-bottom: 1px solid #3c3c3c;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
}

.refresh-btn {
  padding: 4px 12px;
  background: #3c3c3c;
  border: 1px solid #4a4a4a;
  color: #e0e0e0;
  border-radius: 3px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #4a4a4a;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  padding: 16px;
  color: #f44336;
  text-align: center;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #666;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.execution-list {
  flex: 1;
  overflow-y: auto;
}

.execution-item {
  padding: 12px 16px;
  border-bottom: 1px solid #3c3c3c;
  cursor: pointer;
  transition: background 0.2s;
}

.execution-item:hover {
  background: #2d2d30;
}

.execution-item.active {
  background: #37373d;
  border-left: 3px solid #4caf50;
}

.execution-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.execution-id {
  font-family: 'Consolas', monospace;
  font-size: 12px;
  color: #9cdcfe;
}

.execution-status {
  font-size: 11px;
  font-weight: 500;
}

.execution-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #888;
}

.execution-tag {
  margin-top: 4px;
  font-size: 11px;
  color: #4caf50;
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
}

.logs-header {
  padding: 8px 20px;
  background: #252526;
  border-bottom: 1px solid #3c3c3c;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logs-header span {
  font-size: 12px;
  color: #888;
}

.clear-btn {
  padding: 4px 12px;
  background: #3c3c3c;
  border: 1px solid #4a4a4a;
  color: #e0e0e0;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #4a4a4a;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px 20px;
  font-family: 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.logs-empty {
  color: #666;
  text-align: center;
  padding: 40px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-entry {
  padding: 8px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.03);
}

.log-time {
  color: #666;
  margin-right: 8px;
}

.log-node {
  color: #4ec9b0;
  margin-right: 8px;
}

.log-message {
  color: #d4d4d4;
}

.log-error {
  color: #f44336;
}

.log-data {
  margin: 8px 0 0 0;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 3px;
  color: #9cdcfe;
  font-size: 11px;
  overflow-x: auto;
}

/* 输出文件面板 */
.outputs-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.outputs-empty {
  color: #666;
  text-align: center;
  padding: 40px;
}

.outputs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.output-item {
  padding: 12px;
  background: #2d2d30;
  border: 1px solid #3c3c3c;
  border-radius: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.output-info {
  flex: 1;
}

.output-filename {
  font-size: 13px;
  color: #e0e0e0;
  margin-bottom: 4px;
}

.output-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #888;
}

.output-actions {
  display: flex;
  gap: 8px;
}

.open-btn,
.download-btn {
  padding: 6px 12px;
  background: #3c3c3c;
  border: 1px solid #4a4a4a;
  color: #e0e0e0;
  border-radius: 3px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}

.open-btn:hover,
.download-btn:hover {
  background: #4a4a4a;
}

.open-btn {
  border-color: #4caf50;
  color: #4caf50;
}

.open-btn:hover {
  background: rgba(76, 175, 80, 0.1);
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
