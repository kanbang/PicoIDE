<template>
  <div class="output-panel">
    <header class="panel-header">
      <div class="title-group">
        <svg class="header-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
        <h3>输出中心</h3>
        <span class="file-count" v-if="outputFiles.length">{{ outputFiles.length }}</span>
      </div>
      <div class="header-actions">
        <button v-if="outputFiles.length > 0" @click="refreshFiles" class="action-btn" title="同步文件">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <path d="M23 4v6h-6" /><path d="M1 20v-6h6" />
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
        </button>
        <button v-if="outputFiles.length > 0" @click="cleanupFiles" class="action-btn danger" title="全部清空">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </header>

    <div class="panel-body">
      <section v-if="executionStatus" class="status-banner" :class="executionStatus">
        <div class="banner-main">
          <div class="status-indicator">
            <svg v-if="executionStatus === 'running'" class="spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
            </svg>
            <svg v-else-if="executionStatus === 'completed'" width="18" height="18" viewBox="0 0 24 24" stroke="currentColor">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" stroke="currentColor">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div class="status-info">
            <span class="status-msg">{{ statusText }}</span>
            <span v-if="executionDuration" class="status-time">耗时 {{ executionDuration.toFixed(2) }}s</span>
          </div>
        </div>
      </section>

      <div class="notif-area" v-if="errors.length || warnings.length">
        <div v-for="(err, i) in errors" :key="'e'+i" class="notif-item error">
          <span class="dot"></span> {{ err }}
        </div>
        <div v-for="(wrn, i) in warnings" :key="'w'+i" class="notif-item warning">
          <span class="dot"></span> {{ wrn }}
        </div>
      </div>

      <div v-if="outputFiles.length > 0" class="file-grid">
        <div v-for="file in outputFiles" :key="file.file_id" class="file-card" :class="file.file_type">
          <div class="card-icon" :data-type="file.file_type">
            <template v-if="file.file_type === 'html'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /><polyline points="15 3 21 3 21 9" /><line x1="10" y1="14" x2="21" y2="3" /></svg>
            </template>
            <template v-else-if="file.file_type === 'csv'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><line x1="8" y1="13" x2="16" y2="13" /><line x1="8" y1="17" x2="16" y2="17" /></svg>
            </template>
            <template v-else>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" /></svg>
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
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
            </button>
            <button @click="downloadFile(file)" class="icon-btn" title="下载">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
            <button @click="deleteFile(file)" class="icon-btn danger" title="移除">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-illustration">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/>
          </svg>
        </div>
        <h4>暂无数据产生</h4>
        <p>执行流程后，生成的文件、报告及错误日志将汇总在此处。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { showSuccess, showError, showInfo } from '@/utils/toast';

interface OutputFile {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  created_at: string;
  block_name?: string;
  can_open: boolean;
  can_download: boolean;
}

const props = defineProps<{
  executionId?: string;
  isVisible?: boolean;
}>();

const emit = defineEmits<{
  'file-opened': [file: OutputFile];
  'file-downloaded': [file: OutputFile];
  'visibility-change': [visible: boolean];
}>();

// 状态
const executionStatus = ref<'running' | 'completed' | 'failed' | null>(null);
const executionDuration = ref<number>(0);
const outputFiles = ref<OutputFile[]>([]);
const errors = ref<string[]>([]);
const warnings = ref<string[]>([]);
const visible = ref(props.isVisible || false);

// 监听 props.isVisible 变化
watch(() => props.isVisible, (newValue) => {
  visible.value = newValue;
});

// 显示/隐藏功能
function toggle() {
  visible.value = !visible.value;
  emit('visibility-change', visible.value);
}

function show() {
  visible.value = true;
  emit('visibility-change', true);
}

function hide() {
  visible.value = false;
  emit('visibility-change', false);
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
      show();
    }
  },
  setOutputFiles: (files: OutputFile[]) => {
    outputFiles.value = files;
    // 有输出文件时自动显示面板
    if (files.length > 0) {
      show();
    }
  },
  setErrors: (errorList: string[]) => {
    errors.value = errorList;
    // 有错误时自动显示面板
    if (errorList.length > 0) {
      show();
    }
  },
  setWarnings: (warningList: string[]) => {
    warnings.value = warningList;
  },
  refreshFiles,
  toggle,
  show,
  hide,
  visible,
});
</script>

<style scoped>
/* 核心容器 */
.output-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #1e1e1e; /* 更深的深色背景 */
  color: #cccccc;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* 头部 */
.panel-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #252526;
  border-bottom: 1px solid #333333;
  flex-shrink: 0;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon { color: #888; }

.panel-header h3 {
  margin: 0;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #eee;
  font-weight: 600;
}

.file-count {
  background: #333;
  color: #aaa;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
}

.header-actions { display: flex; gap: 4px; }

.action-btn {
  background: transparent;
  border: none;
  color: #888;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.action-btn:hover { background: #37373d; color: #fff; }
.action-btn.danger:hover { background: #902722; color: #fff; }

/* 主体内容区 */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

/* 运行状态横幅 */
.status-banner {
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 16px;
  border-left: 4px solid transparent;
}

.status-banner.running {
  background: rgba(0, 122, 204, 0.15);
  border-color: #007acc;
}
.status-banner.completed {
  background: rgba(76, 175, 80, 0.1);
  border-color: #4caf50;
}
.status-banner.failed {
  background: rgba(244, 67, 54, 0.1);
  border-color: #f44336;
}

.banner-main { display: flex; align-items: center; gap: 12px; }

.status-info { display: flex; flex-direction: column; }
.status-msg { font-size: 13px; font-weight: 500; color: #fff; }
.status-time { font-size: 11px; opacity: 0.6; }

/* 动画 */
.spin { animation: spin 2s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* 错误警告通知 */
.notif-area { margin-bottom: 16px; }
.notif-item {
  font-size: 12px;
  padding: 6px 10px;
  margin-bottom: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.notif-item.error { background: rgba(244, 67, 54, 0.15); color: #f88070; }
.notif-item.warning { background: rgba(255, 193, 7, 0.1); color: #ffd54f; }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

/* 文件网格 */
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
  position: relative;
}

.file-card:hover {
  background: #2d2d30;
  border-color: #444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
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
}

.file-card.html .card-icon { color: #007acc; background: rgba(0,122,204,0.1); }
.file-card.csv .card-icon { color: #4caf50; background: rgba(76,175,80,0.1); }

.card-icon svg { width: 20px; height: 20px; stroke-width: 1.5; }

.card-content { flex: 1; min-width: 0; }

.name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 2px; }
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

/* 按钮组 */
.card-actions {
  display: flex;
  gap: 4px;
  opacity: 0.4; /* 默认低透明度，显得整洁 */
  transition: opacity 0.2s;
}

.file-card:hover .card-actions { opacity: 1; }

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

.icon-btn:hover { background: #444; color: #fff; }
.icon-btn.highlight { color: #007acc; }
.icon-btn.highlight:hover { background: #007acc; color: #fff; }
.icon-btn.danger:hover { background: #902722; color: #fff; }

/* 空状态 */
.empty-state {
  height: 100%;
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

.empty-state h4 { color: #888; margin: 0 0 8px 0; font-size: 16px; }
.empty-state p { font-size: 12px; line-height: 1.6; max-width: 260px; }

/* 滚动条美化 */
.panel-body::-webkit-scrollbar { width: 10px; }
.panel-body::-webkit-scrollbar-track { background: transparent; }
.panel-body::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; border: 3px solid #1e1e1e; }
.panel-body::-webkit-scrollbar-thumb:hover { background: #444; }
</style>