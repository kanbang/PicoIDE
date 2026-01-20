<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { getFlowExecutions } from '@/api/execute';
import { showError, showSuccess } from '@/utils/toast';

export interface ExecutionRecord {
  execution_id: string;
  flow_id: string;
  status: string;
  start_time: string;
  end_time: string | null;
  execution_time: number;
  total_nodes: number;
  executed_nodes: number;
  failed_nodes: number;
  tag: string | null;
  scripts_path: string;
  scripts_hash: string;
}

interface Props {
  flowId?: string;
  limit?: number;
  offset?: number;
}

interface Emits {
  (e: 'select', execution: ExecutionRecord): void;
  (e: 'delete', executionId: string): void;
}

const props = withDefaults(defineProps<Props>(), {
  limit: 20,
  offset: 0
});

const emit = defineEmits<Emits>();

const executions = ref<ExecutionRecord[]>([]);
const loading = ref(false);
const total = ref(0);

async function loadExecutions() {
  if (!props.flowId) return;
  
  loading.value = true;
  try {
    const result = await getFlowExecutions(props.flowId, undefined, true, props.limit, props.offset);
    executions.value = result.executions;
    total.value = result.total;
  } catch (error) {
    console.error('加载执行记录失败:', error);
    showError('加载执行记录失败');
  } finally {
    loading.value = false;
  }
}

async function refresh() {
  await loadExecutions();
  showSuccess('历史记录已刷新');
}

function selectExecution(execution: ExecutionRecord) {
  emit('select', execution);
}

function deleteExecution(execution: ExecutionRecord, event: Event) {
  event.stopPropagation(); // 阻止点击事件冒泡
  emit('delete', execution.execution_id);
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  
  if (diffMs < 60000) return '刚刚';
  if (diffMs < 3600000) return Math.floor(diffMs / 60000) + '分钟前';
  if (diffMs < 86400000) return Math.floor(diffMs / 3600000) + '小时前';
  
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

function getStatusText(status: string): string {
  switch (status) {
    case 'running':
      return '运行中';
    case 'completed':
      return '完成';
    case 'failed':
      return '失败';
    default:
      return status;
  }
}

watch(() => props.flowId, () => {
  if (props.flowId) {
    loadExecutions();
  }
});

onMounted(() => {
  if (props.flowId) {
    loadExecutions();
  }
});

defineExpose({
  refresh,
  loadExecutions
});
</script>

<template>
  <div class="execution-list-container">
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>
    
    <div v-else-if="executions.length > 0" class="execution-list">
      <div 
        v-for="exec in executions" 
        :key="exec.execution_id"
        class="execution-item"
      >
        <div class="execution-icon" :class="exec.status">
          <svg v-if="exec.status === 'running'" class="spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <svg v-else-if="exec.status === 'completed'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        
        <div class="execution-content" @click="selectExecution(exec)">
          <div class="execution-time">{{ formatTime(exec.start_time) }}</div>
          <div class="execution-status">
            <span :class="`status-${exec.status}`">{{ getStatusText(exec.status) }}</span>
            <span class="execution-duration">{{ exec.execution_time.toFixed(2) }}s</span>
          </div>
          <div class="execution-meta">
            <span>{{ exec.executed_nodes }}/{{ exec.total_nodes }} 节点</span>
            <span v-if="exec.failed_nodes > 0" class="failed-count">{{ exec.failed_nodes }} 失败</span>
            <span v-if="exec.output_files_count !== undefined" class="file-count-badge">
              {{ exec.output_files_count }} 文件
            </span>
            <span v-if="exec.tag" class="tag">{{ exec.tag }}</span>
          </div>
        </div>
        
        <div class="execution-actions">
          <button @click="deleteExecution(exec, $event)" class="delete-btn" title="删除记录">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
          <div class="execution-arrow">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <div class="empty-illustration">
        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 1118 0"/><circle cx="12" cy="13" r="3"/><path d="M9 13h6"/>
        </svg>
      </div>
      <h4>{{ flowId ? '暂无执行记录' : '未提供 Flow ID' }}</h4>
      <p>{{ flowId ? '执行流程后，历史记录将汇总在此处。' : '历史记录功能需要 Flow ID。' }}</p>
    </div>
  </div>
</template>

<style scoped>
.execution-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #888;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 2px solid #333;
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.execution-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.execution-item {
  background: #252526;
  border: 1px solid #333;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 10px;
  gap: 12px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.execution-item:hover {
  background: #2d2d30;
  border-color: #444;
  transform: translateX(4px);
}

.execution-icon {
  width: 32px;
  height: 32px;
  background: #333;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  flex-shrink: 0;
}

.execution-icon.running { color: #007acc; }
.execution-icon.completed { color: #4caf50; }
.execution-icon.failed { color: #f44336; }

.execution-icon svg { width: 16px; height: 16px; stroke-width: 1.5; }

.execution-content {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.execution-time {
  font-size: 11px;
  color: #888;
  margin-bottom: 2px;
}

.execution-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.status-running { color: #007acc; }
.status-completed { color: #4caf50; }
.status-failed { color: #f44336; }

.execution-duration {
  font-size: 11px;
  color: #777;
}

.execution-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: #777;
}

.failed-count {
  color: #f44336;
  font-weight: 500;
}

.tag {
  background: #3c3c3c;
  padding: 1px 4px;
  border-radius: 3px;
  color: #aaa;
}

.file-count-badge {
  color: #4caf50;
  font-weight: 500;
}

.execution-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.delete-btn {
  background: #333;
  border: none;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  color: #888;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0;
}

.execution-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: #902722;
  color: #fff;
}

.execution-arrow {
  color: #666;
  flex-shrink: 0;
}

.spin { animation: spin 2s linear infinite; }

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 40px;
  color: #666;
}

.empty-illustration {
  margin-bottom: 20px;
  opacity: 0.2;
}

.empty-state h4 { 
  color: #888; 
  margin: 0 0 8px 0; 
  font-size: 16px; 
}

.empty-state p { 
  font-size: 12px; 
  line-height: 1.6; 
  max-width: 260px; 
}
</style>