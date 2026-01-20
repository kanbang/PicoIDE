<script setup lang="ts">
import { ref, watch, onMounted } from 'vue';
import { getExecutionOutputs } from '@/api/execute';
import { showError } from '@/utils/toast';
import type { ExecutionRecord } from './ExecutionList.vue';

export interface OutputFile {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  block_name?: string;
  can_open: boolean;
  can_download: boolean;
}

interface Props {
  executionId?: string;
  execution?: ExecutionRecord;
}

interface Emits {
  (e: 'back'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const outputFiles = ref<OutputFile[]>([]);
const loading = ref(false);

async function loadOutputs() {
  if (!props.executionId) return;

  // 如果 execution 对象中已经有 output_files，直接使用
  if (props.execution?.output_files) {
    console.log('ExecutionDetail - 使用 execution 中的 output_files:', props.execution.output_files.length);
    outputFiles.value = props.execution.output_files;
    return;
  }

  // 否则从 API 加载
  loading.value = true;
  try {
    console.log('ExecutionDetail - loadOutputs called, executionId:', props.executionId);
    const result = await getExecutionOutputs(props.executionId);
    console.log('ExecutionDetail - API返回结果:', result);
    outputFiles.value = result.output_files;
    console.log('ExecutionDetail - output_files:', outputFiles.value);
  } catch (error) {
    console.error('加载执行输出文件失败:', error);
    showError('加载输出文件失败');
  } finally {
    loading.value = false;
  }
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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

async function openFile(file: OutputFile) {
  try {
    const baseUrl = window.location.origin;
    const fileUrl = `${baseUrl}/api/engine/output-files/${file.file_id}`;
    window.open(fileUrl, '_blank', 'noopener,noreferrer');
  } catch (error) {
    console.error('打开文件失败:', error);
    showError('打开文件失败');
  }
}

async function downloadFile(file: OutputFile) {
  try {
    const { getOutputFile } = await import('@/api/execute');
    const blob = await getOutputFile(file.file_id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error('下载文件失败:', error);
    showError('下载文件失败');
  }
}

watch(() => props.executionId, (newId) => {
  console.log('ExecutionDetail - executionId changed:', newId);
  if (newId) {
    loadOutputs();
  }
});

onMounted(() => {
  if (props.executionId) {
    loadOutputs();
  }
});

defineExpose({
  loadOutputs
});
</script>

<template>
  <div class="execution-detail-container">
    <button @click="emit('back')" class="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </svg>
      返回列表
    </button>

    <div v-if="execution" class="execution-info">
      <h4>执行信息</h4>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">执行ID</span>
          <span class="value">{{ execution.execution_id }}</span>
        </div>
        <div class="info-item">
          <span class="label">执行时间</span>
          <span class="value">{{ formatTime(execution.start_time) }}</span>
        </div>
        <div class="info-item">
          <span class="label">执行时长</span>
          <span class="value">{{ execution.execution_time.toFixed(2) }}s</span>
        </div>
        <div class="info-item">
          <span class="label">状态</span>
          <span class="value" :class="`status-${execution.status}`">
            {{ getStatusText(execution.status) }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">节点执行</span>
          <span class="value">{{ execution.executed_nodes }}/{{ execution.total_nodes }}</span>
        </div>
        <div class="info-item" v-if="execution.failed_nodes > 0">
          <span class="label">失败节点</span>
          <span class="value failed">{{ execution.failed_nodes }}</span>
        </div>
        <div class="info-item" v-if="execution.tag">
          <span class="label">标签</span>
          <span class="value tag">{{ execution.tag }}</span>
        </div>
      </div>
    </div>

    <div class="files-header">
      <h4>输出文件 ({{ outputFiles.length }})</h4>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载输出文件...</p>
    </div>

    <div v-else-if="outputFiles.length > 0" class="file-grid">
      <div v-for="file in outputFiles" :key="file.file_id" class="file-card" :class="file.file_type">
        <div class="card-icon" :data-type="file.file_type">
          <template v-if="file.file_type === 'html'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </template>
          <template v-else-if="file.file_type === 'csv'">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <line x1="8" y1="13" x2="16" y2="13" />
              <line x1="8" y1="17" x2="16" y2="17" />
            </svg>
          </template>
          <template v-else>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
              <polyline points="13 2 13 9 20 9" />
            </svg>
          </template>
        </div>

        <div class="card-content">
          <div class="name-row">
            <span class="name" :title="file.filename">{{ file.filename }}</span>
            <span class="tag">{{ file.file_type.toUpperCase() }}</span>
          </div>
          <div class="meta-row">
            <span>{{ formatFileSize(file.file_size) }}</span>
            <span class="divider">·</span>
            <span class="source">{{ file.block_name || '系统输出' }}</span>
          </div>
        </div>

        <div class="card-actions">
          <button v-if="file.can_open" @click="openFile(file)" class="icon-btn highlight" title="预览">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </button>
          <button @click="downloadFile(file)" class="icon-btn" title="下载">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <h4>此执行无输出文件</h4>
    </div>
  </div>
</template>

<style scoped>
.execution-detail-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.back-btn {
  background: #333;
  border: none;
  color: #ccc;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  transition: all 0.2s;
  align-self: flex-start;
}

.back-btn:hover {
  background: #444;
  color: #fff;
}

.execution-info {
  background: #252526;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 16px;
}

.execution-info h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #eee;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item .label {
  font-size: 11px;
  color: #888;
}

.info-item .value {
  font-size: 13px;
  color: #e1e1e1;
}

.info-item .value.status-running {
  color: #007acc;
}

.info-item .value.status-completed {
  color: #4caf50;
}

.info-item .value.status-failed {
  color: #f44336;
}

.info-item .value.failed {
  color: #f44336;
}

.info-item .value.tag {
  background: #3c3c3c;
  padding: 2px 6px;
  border-radius: 3px;
  color: #aaa;
}

.files-header {
  margin-bottom: 8px;
}

.files-header h4 {
  margin: 0;
  font-size: 14px;
  color: #eee;
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
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

.file-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-card {
  background: #252526;
  border: 1px solid #333;
  border-radius: 6px;
  display: flex;
  align-items: center;
  padding: 10px;
  gap: 12px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.file-card:hover {
  background: #2d2d30;
  border-color: #444;
  transform: translateY(-1px);
}

.card-icon {
  width: 36px;
  height: 36px;
  background: #333;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #888;
  flex-shrink: 0;
}

.file-card.html .card-icon {
  color: #007acc;
  background: rgba(0, 122, 204, 0.1);
}

.file-card.csv .card-icon {
  color: #4caf50;
  background: rgba(76, 175, 80, 0.1);
}

.card-icon svg {
  width: 20px;
  height: 20px;
  stroke-width: 1.5;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.name {
  font-size: 13px;
  color: #e1e1e1;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag {
  font-size: 9px;
  background: #3c3c3c;
  padding: 1px 4px;
  border-radius: 3px;
  color: #aaa;
}

.meta-row {
  display: flex;
  font-size: 11px;
  color: #777;
  gap: 6px;
}

.card-actions {
  display: flex;
  gap: 4px;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.file-card:hover .card-actions {
  opacity: 1;
}

.icon-btn {
  background: #333;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 4px;
  color: #ccc;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: #444;
  color: #fff;
}

.icon-btn.highlight {
  color: #007acc;
}

.icon-btn.highlight:hover {
  background: #007acc;
  color: #fff;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  min-height: 200px;
}

.empty-state h4 {
  margin: 0;
  font-size: 14px;
  color: #888;
}
</style>