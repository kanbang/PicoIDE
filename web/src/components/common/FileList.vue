<!--
 * @Descripttion: 通用文件列表组件
 * @version: 1.0
 * @Author: zhai
 * @Date: 2026-02-04
-->
<script setup lang="ts">
import { formatFileSize, formatAbsoluteTime } from '@/utils/formatters';
import type { OutputFile } from '@/api/execute';

interface Props {
  files: OutputFile[];
  showHeader?: boolean;
  headerTitle?: string;
  showDelete?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showHeader: true,
  headerTitle: '输出文件',
  showDelete: true
});

const emit = defineEmits<{
  open: [file: OutputFile];
  download: [file: OutputFile];
  delete: [file: OutputFile];
}>();

// 打开文件
function openFile(file: OutputFile) {
  const baseUrl = window.location.origin;
  const fileUrl = `${baseUrl}/api/engine/output-files/${file.file_id}`;
  window.open(fileUrl, '_blank', 'noopener,noreferrer');
  emit('open', file);
}

// 下载文件
function downloadFile(file: OutputFile) {
  const link = document.createElement('a');
  link.href = `/api/engine/output-files/${file.file_id}`;
  link.download = file.filename;
  link.click();
  emit('download', file);
}

// 删除文件
function deleteFile(file: OutputFile) {
  emit('delete', file);
}
</script>

<template>
  <div class="file-list">
    <!-- 头部 -->
    <div v-if="showHeader" class="file-header">
      <span class="header-title">{{ headerTitle }}</span>
      <span v-if="files.length > 0" class="file-count">{{ files.length }}</span>
    </div>

    <!-- 内容区域 -->
    <div class="file-body">
      <!-- 空状态 -->
      <div v-if="files.length === 0" class="empty-state">
        <div class="empty-illustration">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
            <line x1="7" y1="2" x2="7" y2="22" />
            <line x1="17" y1="2" x2="17" y2="22" />
            <line x1="2" y1="12" x2="22" y2="12" />
            <line x1="2" y1="7" x2="7" y2="7" />
            <line x1="2" y1="17" x2="7" y2="17" />
            <line x1="17" y1="17" x2="22" y2="17" />
            <line x1="17" y1="7" x2="22" y2="7" />
          </svg>
        </div>
        <h4>暂无文件</h4>
        <p>执行流程后，生成的文件将显示在此处</p>
      </div>

      <!-- 文件列表 -->
      <div v-else class="file-items">
        <div
          v-for="file in files"
          :key="file.file_id"
          class="file-card"
          :class="file.file_type"
        >
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
              <span class="divider">·</span>
              <span>{{ formatAbsoluteTime(file.created_at) }}</span>
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
            <button v-if="showDelete" @click="deleteFile(file)" class="icon-btn danger" title="移除">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #1e1e1e;
}

.file-header {
  height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-bottom: 1px solid #333;
  flex-shrink: 0;
}

.header-title {
  font-size: 13px;
  font-weight: 500;
  color: #e0e0e0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.file-count {
  background: #374151;
  color: #fff;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.file-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

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

.file-items {
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
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
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
  align-items: center;
  flex-wrap: wrap;
}

.divider {
  color: #555;
}

.source {
  color: #4caf50;
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

.icon-btn.danger:hover {
  background: #902722;
  color: #fff;
}

/* 滚动条美化 */
.file-body::-webkit-scrollbar {
  width: 10px;
}

.file-body::-webkit-scrollbar-track {
  background: transparent;
}

.file-body::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 10px;
  border: 3px solid #1e1e1e;
}

.file-body::-webkit-scrollbar-thumb:hover {
  background: #444;
}
</style>
