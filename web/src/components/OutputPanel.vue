<template>
  <div v-if="isPanelVisible" class="output-panel-wrapper" :style="{ width: panelWidth + 'px' }">
    <div class="output-panel">
      <div class="panel-header">
        <h3>输出文件</h3>
        <div class="header-actions">
          <button v-if="outputFiles.length > 0" @click="refreshFiles" class="btn btn-secondary btn-sm" title="刷新">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6" />
              <path d="M1 20v-6h6" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
          </button>
          <button v-if="outputFiles.length > 0" @click="cleanupFiles" class="btn btn-danger btn-sm" title="清理旧文件">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              <line x1="10" y1="11" x2="10" y2="17" />
              <line x1="14" y1="11" x2="14" y2="17" />
            </svg>
          </button>
        </div>
      </div>

      <div class="panel-content">
        <!-- 执行状态 -->
        <div v-if="executionStatus" class="execution-status" :class="executionStatus">
          <div class="status-icon">
            <svg v-if="executionStatus === 'running'" width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
            <svg v-else-if="executionStatus === 'completed'" width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <svg v-else-if="executionStatus === 'failed'" width="20" height="20" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <div class="status-text">
            <span class="status-label">{{ statusText }}</span>
            <span v-if="executionDuration" class="status-duration">{{ executionDuration.toFixed(2) }}s</span>
          </div>
        </div>

        <!-- 错误信息 -->
        <div v-if="errors.length > 0" class="error-list">
          <div v-for="(error, index) in errors" :key="index" class="error-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{{ error }}</span>
          </div>
        </div>

        <!-- 警告信息 -->
        <div v-if="warnings.length > 0" class="warning-list">
          <div v-for="(warning, index) in warnings" :key="index" class="warning-item">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span>{{ warning }}</span>
          </div>
        </div>

        <!-- 输出文件列表 -->
        <div v-if="outputFiles.length > 0" class="file-list">
          <div v-for="file in outputFiles" :key="file.file_id" class="file-item">
            <div class="file-icon">
              <svg v-if="file.file_type === 'html'" width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
              <svg v-else-if="file.file_type === 'csv'" width="24" height="24" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="8" y1="13" x2="16" y2="13" />
                <line x1="8" y1="17" x2="16" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
              <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
                <polyline points="13 2 13 9 20 9" />
              </svg>
            </div>

            <div class="file-info">
              <div class="file-name">{{ file.filename }}</div>
              <div class="file-meta">
                <span class="file-type">{{ file.file_type.toUpperCase() }}</span>
                <span class="file-size">{{ formatFileSize(file.file_size) }}</span>
                <span v-if="file.block_name" class="file-source">{{ file.block_name }}</span>
              </div>
            </div>

            <div class="file-actions">
              <button v-if="file.can_open" @click="openFile(file)" class="btn btn-primary btn-sm" title="打开">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
                打开
              </button>
              <button @click="downloadFile(file)" class="btn btn-secondary btn-sm" title="下载">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                下载
              </button>
              <button @click="deleteFile(file)" class="btn btn-danger btn-sm" title="删除">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
          </svg>
          <p>暂无输出文件</p>
          <p class="hint">运行流程后将在此显示输出文件</p>
        </div>
      </div>
      <Splitter
      direction="horizontal"
      :min-size="250"
      :max-size="800"
      @drag="handleSplitterDrag"
    />
    </div>
  </div>

  <!-- 显示/隐藏按钮 -->
  <button
    @click="togglePanel"
    class="btn-toggle-overlay"
    :style="{ right: isPanelVisible ? panelWidth + 'px' : '0' }"
    :title="isPanelVisible ? '隐藏输出面板' : '显示输出面板'"
  >
    <svg v-if="isPanelVisible" width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M4 1L8 5L4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
        stroke-linejoin="round" />
    </svg>
    <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M6 1L2 5L6 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
        stroke-linejoin="round" />
    </svg>
  </button>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { showSuccess, showError, showInfo } from '@/utils/toast';
import Splitter from '@/components/common/Splitter.vue';

interface OutputFile {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  block_name?: string;
  output_port?: string;
  can_open: boolean;
  can_download: boolean;
}

const props = defineProps<{
  executionId?: string;
}>();

const emit = defineEmits<{
  'file-opened': [file: OutputFile];
  'file-downloaded': [file: OutputFile];
}>();

// 状态
const executionStatus = ref<'running' | 'completed' | 'failed' | null>(null);
const executionDuration = ref<number>(0);
const outputFiles = ref<OutputFile[]>([]);
const errors = ref<string[]>([]);
const warnings = ref<string[]>([]);

// 面板控制
const panelWidth = ref(350);
const isPanelVisible = ref(false);

// 拖动功能
function handleSplitterDrag(delta: number) {
  const newWidth = panelWidth.value + delta;
  if (newWidth >= 250 && newWidth <= 800) {
    panelWidth.value = newWidth;
  }
}

// 显示/隐藏功能
function togglePanel() {
  isPanelVisible.value = !isPanelVisible.value;
}

function showPanel() {
  isPanelVisible.value = true;
}

// 计算属性
const statusText = computed(() => {
  switch (executionStatus.value) {
    case 'running':
      return '执行中...';
    case 'completed':
      return '执行完成';
    case 'failed':
      return '执行失败';
    default:
      return '';
  }
});

// 方法
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

async function refreshFiles() {
  try {
    const { getOutputFiles } = await import('@/api/flow');
    const files = await getOutputFiles();
    outputFiles.value = files;
    showSuccess('文件列表已刷新');
  } catch (error) {
    console.error('刷新文件失败:', error);
    showError('刷新文件失败');
  }
}

async function openFile(file: OutputFile) {
  try {
    // 直接使用后端文件访问 URL
    const baseUrl = window.location.origin;
    const fileUrl = `${baseUrl}/api/flow/output-files/${file.file_id}`;

    // 使用 window.open 直接打开文件
    window.open(fileUrl, '_blank', 'noopener,noreferrer');

    emit('file-opened', file);
  } catch (error) {
    console.error('打开文件失败:', error);
    showError('打开文件失败');
  }
}

async function downloadFile(file: OutputFile) {
  try {
    const { getOutputFile } = await import('@/api/flow');
    const blob = await getOutputFile(file.file_id);
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    emit('file-downloaded', file);
    showSuccess('文件下载已开始');
  } catch (error) {
    console.error('下载文件失败:', error);
    showError('下载文件失败');
  }
}

async function deleteFile(file: OutputFile) {
  try {
    const confirmed = await showConfirm(
      `确定要删除文件 "${file.filename}" 吗？`,
      '确认删除'
    );

    if (!confirmed) return;

    const { deleteOutputFile } = await import('@/api/flow');
    await deleteOutputFile(file.file_id);

    outputFiles.value = outputFiles.value.filter(f => f.file_id !== file.file_id);
    showSuccess('文件已删除');
  } catch (error) {
    console.error('删除文件失败:', error);
    showError('删除文件失败');
  }
}

async function cleanupFiles() {
  try {
    const confirmed = await showConfirm(
      '确定要清理所有旧文件吗？',
      '确认清理'
    );

    if (!confirmed) return;

    const { cleanupOutputFiles } = await import('@/api/flow');
    await cleanupOutputFiles();

    await refreshFiles();
    showSuccess('旧文件已清理');
  } catch (error) {
    console.error('清理文件失败:', error);
    showError('清理文件失败');
  }
}

// 原生 confirm 对话框
function showConfirm(message: string, title: string = '确认'): Promise<boolean> {
  return new Promise((resolve) => {
    const result = window.confirm(`${title}\n\n${message}`);
    resolve(result);
  });
}

// 暴露方法供父组件调用
defineExpose({
  setExecutionStatus: (status: 'running' | 'completed' | 'failed', duration?: number) => {
    executionStatus.value = status;
    if (duration !== undefined) {
      executionDuration.value = duration;
    }
    // 运行时自动显示面板
    if (status === 'running') {
      showPanel();
    }
  },
  setOutputFiles: (files: OutputFile[]) => {
    outputFiles.value = files;
    // 有输出文件时自动显示面板
    if (files.length > 0) {
      showPanel();
    }
  },
  setErrors: (errorList: string[]) => {
    errors.value = errorList;
    // 有错误时自动显示面板
    if (errorList.length > 0) {
      showPanel();
    }
  },
  setWarnings: (warningList: string[]) => {
    warnings.value = warningList;
  },
  refreshFiles,
  showPanel,
  isPanelVisible,
});
</script>

<style scoped>
.output-panel-wrapper {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  display: flex;
  background: #2d2d2d;
  border-left: 1px solid #444;
  z-index: 1000;
}

.output-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  flex: 1;
  overflow: hidden;
}

.btn-toggle-overlay {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 60px;
  background: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: 6px 0 0 6px;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
  transition: all 0.25s ease;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.3);
  padding: 0;
}

.btn-toggle-overlay:hover {
  width: 20px;
  background: rgba(50, 50, 50, 0.9);
  color: #fff;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
}

.btn-toggle-overlay svg {
  width: 12px;
  height: 12px;
  stroke-width: 2;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #444;
  background: #2d2d2d;
  flex-shrink: 0;
}

.panel-header h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.execution-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 12px;
  border-radius: 4px;
  background: #3d3d3d;
}

.execution-status.running {
  background: rgba(0, 122, 204, 0.1);
  border: 1px solid rgba(0, 122, 204, 0.3);
}

.execution-status.completed {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.execution-status.failed {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.status-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}

.execution-status.running .status-icon {
  color: #007acc;
}

.execution-status.completed .status-icon {
  color: #10b981;
}

.execution-status.failed .status-icon {
  color: #ef4444;
}

.status-text {
  display: flex;
  flex-direction: column;
}

.status-label {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.status-duration {
  font-size: 11px;
  color: #888;
}

.error-list,
.warning-list {
  margin-bottom: 12px;
}

.error-item,
.warning-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 12px;
  margin-bottom: 4px;
  border-radius: 4px;
  font-size: 12px;
}

.error-item {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.warning-item {
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
}

.error-item svg,
.warning-item svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 4px;
  background: #3d3d3d;
  transition: background 0.2s;
}

.file-item:hover {
  background: #4d4d4d;
}

.file-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  color: #888;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 4px;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: #888;
}

.file-type {
  padding: 2px 6px;
  border-radius: 3px;
  background: #4e4e52;
  font-weight: 500;
}

.file-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #888;
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 4px 0;
  font-size: 14px;
}

.empty-state .hint {
  font-size: 11px;
  color: #666;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 12px;
}

.btn-primary {
  background: #4caf50;
  border-color: #4caf50;
}

.btn-primary:hover {
  background: #45a049;
}

.btn-secondary {
  background: #3d3d3d;
  border-color: #555;
  color: #ccc;
}

.btn-secondary:hover {
  background: #4d4d4d;
}

.btn-danger {
  background: #f44336;
  border-color: #f44336;
  color: #fff;
}

.btn-danger:hover {
  background: #d32f2f;
}

.btn svg {
  flex-shrink: 0;
}
</style>