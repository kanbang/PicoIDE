<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { getExecutionOutputs } from '@/api/execute';
import { showError } from '@/utils/toast';
import { formatFileSize, formatAbsoluteTime, getStatusText } from '@/utils/formatters';
import type { ExecutionRecord } from './ExecutionList.vue';
import type { OutputFile } from '@/api/execute';

interface Props {
  executionId?: string;
  execution?: ExecutionRecord;
}

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const props = defineProps<Props>();
const outputFiles = ref<OutputFile[]>([]);
const loading = ref(false);

async function loadOutputs() {
  if (!props.executionId) return;

  // 使用 execution 中的 output_files 或从 API 加载
  if (props.execution?.output_files) {
    outputFiles.value = [...props.execution.output_files];
    return;
  }

  loading.value = true;
  try {
    const result = await getExecutionOutputs(props.executionId);
    outputFiles.value = result.output_files || [];
  } catch (error) {
    console.error('加载执行输出文件失败:', error);
    showError('加载输出文件失败');
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (props.executionId) {
    loadOutputs();
  }
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
          <span class="value">{{ formatAbsoluteTime(execution.start_time) }}</span>
        </div>
        <div class="info-item">
          <span class="label">执行时长</span>
          <span class="value">{{ execution.execution_time.toFixed(2) }}s</span>
        </div>
        <div class="info-item">
          <span class="label">状态</span>
          <span class="value" :class="`status-${execution.status}`">
            {{ getStatusText(execution.status).text }}
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
      <a
        v-for="file in outputFiles"
        :key="file.file_id"
        class="file-card"
        :href="`/api/engine/output-files/${file.file_id}`"
        target="_blank"
      >
        <div class="card-icon" :data-type="file.file_type">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
          </svg>
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
      </a>
    </div>

    <div v-else class="empty-state">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>
      <p>此执行无输出文件</p>
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
  text-decoration: none;
  color: inherit;
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

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #666;
  min-height: 200px;
}

.empty-state svg {
  color: #444;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
  color: #888;
}
</style>
