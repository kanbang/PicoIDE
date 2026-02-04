<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { getExecutionOutputs } from '@/api/execute';
import { showError } from '@/utils/toast';
import { formatAbsoluteTime, getStatusText } from '@/utils/formatters';
import FileList from '../common/FileList.vue';
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
    <button @click="emit('back')" class="back-btn" title="返回列表">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </svg>
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

    <!-- 使用公共 FileList 组件 -->
    <FileList
      :files="outputFiles"
      :show-header="true"
      :show-delete="false"
      header-title="输出文件"
      :compact="true"
    />
  </div>
</template>

<style scoped>
.execution-detail-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  padding: 0;
}

.back-btn {
  background: #333;
  border: none;
  color: #ccc;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
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

</style>
