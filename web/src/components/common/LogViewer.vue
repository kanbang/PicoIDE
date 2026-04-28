<!--
 * @Descripttion: 通用日志查看器组件
 * @version: 1.0
 * @Author: zhai
 * @Date: 2026-02-04
-->
<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import type { LogEvent, LogTypeFilter } from './types';

interface Props {
  events: LogEvent[];
  isLoading?: boolean;
  showFilter?: boolean;
  showHeader?: boolean;
  containerClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  isLoading: false,
  showFilter: true,
  showHeader: true,
  containerClass: 'logs-container'
});

const emit = defineEmits<{
  clear: [];
}>();

const containerRef = ref<HTMLElement | null>(null);
const selectedType = ref<LogTypeFilter>('all');

// 排除通用日志类型的唯一类型列表
const uniqueTypes = computed(() => {
  const types = new Set<string>();
  props.events.forEach(e => {
    if (e.type && !['log', 'info'].includes(e.type)) {
      types.add(e.type);
    }
  });
  return ['all', ...Array.from(types).sort()];
});

// 过滤后的事件
const filteredEvents = computed(() => {
  if (selectedType.value === 'all') {
    return props.events;
  }
  return props.events.filter(e => e.type === selectedType.value);
});

// 监听 events 变化，自动滚动到底部
watch(() => props.events.length, () => {
  nextTick(() => scrollToBottom());
});

// 自动滚动到底部
function scrollToBottom() {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight;
  }
}

// 切换数据展开/折叠
function toggleDataExpand(event: LogEvent) {
  event.expanded = !event.expanded;
}

// 格式化时间
function formatTime(isoString: string): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  if (diffMs < 1000) {
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  }

  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
}

// 格式化数据
function formatData(data: any): string {
  if (data === null || data === undefined) return '';
  if (typeof data === 'string') return data;
  if (typeof data === 'number') return data.toString();
  if (typeof data === 'boolean') return data ? 'true' : 'false';
  return JSON.stringify(data, null, 2);
}

// 获取事件图标
function getEventIcon(event: LogEvent): { svg: string; color: string } {
  const type = event.type?.toLowerCase() || 'info';

  const icons: Record<string, { svg: string; color: string }> = {
    // 基础日志类型
    log: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 6h16M4 12h16M4 18h16"/>
      </svg>`,
      color: '#4caf50'
    },
    debug: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="0.5" fill="currentColor"/>
      </svg>`,
      color: '#9e9e9e'
    },
    info: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="7" x2="12" y2="12" stroke-linecap="round"/>
        <circle cx="12" cy="16" r="0.5" fill="currentColor"/>
      </svg>`,
      color: '#2196f3'
    },
    error: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="14" stroke-linecap="round"/>
        <circle cx="12" cy="17" r="0.5" fill="currentColor"/>
      </svg>`,
      color: '#f44336'
    },
    // 数据类型
    data: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="4" width="18" height="16" rx="2" fill="currentColor" fill-opacity="0.1"/>
        <line x1="8" y1="12" x2="16" y2="12" stroke-linecap="round"/>
        <line x1="8" y1="8" x2="12" y2="8" stroke-linecap="round"/>
        <line x1="8" y1="16" x2="14" y2="16" stroke-linecap="round"/>
      </svg>`,
      color: '#2196f3'
    },
    file: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
        <polyline points="13 2 13 9 20 9"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
      </svg>`,
      color: '#ff9800'
    },
    // 引擎状态类型
    status: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="6" x2="12" y2="12" stroke-linecap="round"/>
      </svg>`,
      color: '#4caf50'
    },
    execution_completed: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M9 12l2 2 4-4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`,
      color: '#4caf50'
    },
    execution_failed: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15" stroke-linecap="round"/>
        <line x1="9" y1="9" x2="15" y2="15" stroke-linecap="round"/>
      </svg>`,
      color: '#f44336'
    },
    execution_stopped: {
      svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <rect x="9" y="9" width="6" height="6" fill="currentColor"/>
      </svg>`,
      color: '#ff9800'
    }
  };

  const defaultIcon: { svg: string; color: string } = {
    svg: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <line x1="12" y1="7" x2="12" y2="12" stroke-linecap="round"/>
      <circle cx="12" cy="16" r="0.5" fill="currentColor"/>
    </svg>`,
    color: '#2196f3'
  };

  return icons[type] ?? defaultIcon;
}

// 暴露方法
defineExpose({
  scrollToBottom,
  selectedType
});
</script>

<template>
  <div class="log-viewer" :class="{ 'with-header': showHeader }">
    <!-- 头部 -->
    <div v-if="showHeader" class="log-header">
      <div class="header-left">
        <svg class="header-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span class="header-title">日志</span>
        <span v-if="events.length > 0" class="event-count">{{ events.length }}</span>
      </div>
      <div class="header-right">
        <!-- 类型过滤器 -->
        <div v-if="showFilter" class="type-filter">
          <span
            v-for="type in uniqueTypes"
            :key="type"
            class="filter-tag"
            :class="{ active: selectedType === type }"
            @click="selectedType = type"
          >
            {{ type === 'all' ? '全部' : type.toUpperCase() }}
          </span>
        </div>
        <!-- 清空按钮 -->
        <button @click="emit('clear')" class="header-btn" title="清空日志">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="log-body" :class="containerClass" ref="containerRef">
      <!-- 加载状态 -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <div class="loading-text">加载中...</div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="filteredEvents.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div class="empty-text">等待日志...</div>
      </div>

      <!-- 事件列表 -->
      <div v-else class="event-list">
        <div
          v-for="(event, index) in filteredEvents"
          :key="index"
          class="event-item"
          :class="[event.type?.toLowerCase(), { 'is-data': event.type === 'data' }]"
        >
          <div class="event-icon" :style="{ color: getEventIcon(event).color }">
            <span v-html="getEventIcon(event).svg"></span>
          </div>
          <div class="event-content">
            <div class="event-header">
              <span class="event-type">{{ event.type || 'INFO' }}</span>
              <span v-if="event.node_type || event.node_name" class="event-node">
                {{ event.node_type || event.node_name }}
              </span>
              <span v-if="event.data" class="data-toggle" @click="toggleDataExpand(event)">
                <svg class="toggle-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                  <path v-if="!event.expanded" d="M6 9l6 6 6-6"/>
                  <path v-else d="M18 15l-6-6-6 6"/>
                </svg>
              </span>
              <span class="event-time">{{ formatTime(event.timestamp || '') }}</span>
            </div>
            <div class="event-message" v-if="event.message">{{ event.message }}</div>
            <div class="event-error" v-if="event.error">{{ event.error }}</div>
            <div class="event-data" v-if="event.data && event.expanded">
              <pre>{{ formatData(event.data) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  overflow: hidden;
  background: #1e1e1e;
}

.log-header {
  height: 40px;
  background: #252526;
  border-bottom: 1px solid #333;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  color: #888;
}

.header-title {
  font-size: 13px;
  font-weight: 500;
  color: #e0e0e0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.event-count {
  background: #374151;
  color: #fff;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-filter {
  display: flex;
  gap: 4px;
  background: #1e1e1e;
  border-radius: 4px;
  padding: 4px 8px;
}

.filter-tag {
  font-size: 10px;
  padding: 3px 10px;
  border-radius: 3px;
  background: #374151;
  color: #aaa;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.filter-tag:hover {
  background: #2e7d32;
  color: #fff;
}

.filter-tag.active {
  background: #4caf50;
  color: #fff;
}

.header-btn {
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

.header-btn:hover {
  background: #374151;
  color: #fff;
}

.log-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  background: #1e1e1e;
}

.loading-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid #333;
  border-top-color: #4caf50;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 12px;
}

.empty-state {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #666;
}

.empty-icon {
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 13px;
  color: #888;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.event-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: #252526;
  border-radius: 4px;
  border: 1px solid transparent;
  border-left-width: 3px;
  border-left-style: solid;
  transition: all 0.2s;
  align-items: flex-start;
}

.event-item:hover {
  background: #2d2d30;
  border-color: #3e4040;
}

/* 事件类型边框颜色 */
.event-item.status { border-left-color: #4caf50; }
.event-item.log { border-left-color: #4caf50; }
.event-item.debug { border-left-color: #9e9e9e; }
.event-item.info { border-left-color: #2196f3; }
.event-item.error { border-left-color: #f44336; }
.event-item.data { border-left-color: #2196f3; }
.event-item.file { border-left-color: #ff9800; }
.event-item.execution_completed { border-left-color: #4caf50; }
.event-item.execution_failed { border-left-color: #f44336; }
.event-item.execution_stopped { border-left-color: #ff9800; }

.event-item.is-data {
  align-items: stretch;
}

.event-icon {
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.event-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.event-type {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 3px;
  background: #374151;
  color: #fff;
}

.event-item.status .event-type { background: #4caf50; }
.event-item.log .event-type { background: #4caf50; }
.event-item.debug .event-type { background: #9e9e9e; }
.event-item.info .event-type { background: #2196f3; }
.event-item.error .event-type { background: #f44336; }
.event-item.data .event-type { background: #2196f3; }
.event-item.file .event-type { background: #ff9800; }
.event-item.execution_completed .event-type { background: #4caf50; }
.event-item.execution_failed .event-type { background: #f44336; }
.event-item.execution_stopped .event-type { background: #ff9800; }

.event-node {
  font-size: 11px;
  color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
  padding: 2px 6px;
  border-radius: 3px;
}

.data-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 4px;
  cursor: pointer;
  color: #666;
  transition: all 0.15s;
}

.data-toggle:hover {
  background: #374151;
  color: #4caf50;
}

.toggle-icon {
  transition: transform 0.15s;
}

.event-time {
  font-size: 11px;
  color: #666;
  margin-left: auto;
}

.event-message {
  font-size: 12px;
  color: #ccc;
  line-height: 1.5;
  word-break: break-word;
}

.event-item.data .event-message {
  display: none;
}

.event-error {
  font-size: 12px;
  color: #f88070;
  line-height: 1.5;
  word-break: break-word;
}

.event-data {
  margin-top: 6px;
  padding: 8px;
  background: #1a231e;
  border-radius: 4px;
  border: 1px solid #3e4040;
  overflow-x: auto;
}

.event-item.is-data .event-data {
  display: block;
}

.event-data pre {
  margin: 0;
  font-size: 11px;
  color: #888;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 100px;
  overflow-y: auto;
}

/* 滚动条美化 */
.log-body::-webkit-scrollbar {
  width: 6px;
}

.log-body::-webkit-scrollbar-track {
  background: transparent;
}

.log-body::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
  border: 2px solid #1e1e1e;
}

.log-body::-webkit-scrollbar-thumb:hover {
  background: #4caf50;
}
</style>
