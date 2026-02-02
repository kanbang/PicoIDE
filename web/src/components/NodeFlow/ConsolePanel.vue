<script setup lang="ts">
import { ref, watch, onUnmounted, nextTick, computed } from 'vue';

// SSE Event Type
export interface SSEEvent {
  type: string;
  source?: string;
  node_type?: string;
  message?: string;
  timestamp?: string;
  data?: any;
  expanded?: boolean;
}

interface Props {
  isVisible?: boolean;
  isConnecting?: boolean;
  isConnected?: boolean;
}

const props = defineProps<Props>();

const visible = ref(props.isVisible || false);
const events = ref<SSEEvent[]>([]);
const containerRef = ref<HTMLElement | null>(null);

const selectedType = ref<string>('all');
const uniqueTypes = computed(() => {
  const types = new Set<string>();
  events.value.forEach(e => {
    if (e.type && !['log', 'info'].includes(e.type)) {
      types.add(e.type);
    }
  });
  return ['all', ...Array.from(types).sort()];
});

const filteredEvents = computed(() => {
  if (selectedType.value === 'all') {
    return events.value;
  }
  return events.value.filter(e => e.type === selectedType.value);
});

watch(() => props.isVisible, (newValue) => {
  visible.value = newValue;
});

function toggle() {
  visible.value = !visible.value;
}

function show() {
  visible.value = true;
  nextTick(() => scrollToBottom());
}

function hide() {
  visible.value = false;
}

function addEvent(event: SSEEvent) {
  if (event.type === 'data') {
    event.expanded = false;
  }
  events.value.push(event);
  nextTick(() => scrollToBottom());
}

function setEvents(newEvents: SSEEvent[]) {
  events.value = newEvents;
  nextTick(() => scrollToBottom());
}

function clearEvents() {
  events.value = [];
}

function scrollToBottom() {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight;
  }
}

function formatTime(isoString: string): string {
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

function toggleDataExpand(event: SSEEvent) {
    event.expanded = !event.expanded;
}

function getEventIcon(event: SSEEvent) {
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

  return icons[type] || icons.info;
}

function formatData(data: any): string {
  if (data === null || data === undefined) return '';
  if (typeof data === 'string') return data;
  if (typeof data === 'number') return data.toString();
  if (typeof data === 'boolean') return data ? 'true' : 'false';
  return JSON.stringify(data, null, 2);
}

onUnmounted(() => {
});

defineExpose({
  addEvent,
  setEvents,
  clearEvents,
  show,
  hide,
  toggle,
  visible,
  events: filteredEvents,
  selectedType
});
</script>

<template>
  <div class="console-panel" :class="{ visible }">
    <div class="panel-header">
      <div class="header-left">
        <svg class="header-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span class="header-title">执行日志</span>
        <span v-if="events.length > 0" class="event-count">{{ events.length }}</span>
      </div>
      <div class="header-right">
        <div class="type-filter">
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
        <div class="connection-status" :class="{ connected: isConnected, connecting: isConnecting }">
          <span v-if="isConnecting" class="status-dot connecting"></span>
          <span v-else-if="isConnected" class="status-dot connected"></span>
          <span v-else class="status-dot disconnected"></span>
          <span class="status-text">
            {{ isConnecting ? '连接中...' : isConnected ? '已连接' : '未连接' }}
          </span>
        </div>
        <button @click="clearEvents" class="header-btn" title="清空日志">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="panel-body" ref="containerRef">
      <div v-if="filteredEvents.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
            <polyline points="13 2 13 9 20 9" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <polyline points="10 9 9 9 8 9" />
          </svg>
        </div>
        <div class="empty-text">等待执行...</div>
        <div class="empty-hint">点击运行按钮开始执行，日志将实时显示</div>
      </div>
      <div v-else-if="isConnecting" class="loading-state">
        <div class="spinner"></div>
        <div class="loading-text">连接中...</div>
      </div>
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
              <span v-if="event.node_type" class="event-node">{{ event.node_type }}</span>
              <span v-if="event.data" class="data-toggle" @click="toggleDataExpand(event)">
                <svg class="toggle-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                  <path v-if="!event.expanded" d="M6 9l6 6 6-6"/>
                  <path v-else d="M18 15l-6-6-6 6"/>
                </svg>
              </span>
              <span class="event-time">{{ formatTime(event.timestamp || '') }}</span>
            </div>
            <div class="event-message" v-if="event.message">{{ event.message }}</div>
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
.console-panel {
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  border-top: 1px solid #333;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
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

.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 4px;
  background: #2d2d30;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-dot.connecting {
  background: #ffa726;
  animation: pulse 1.5s infinite;
}

.status-dot.connected {
  background: #4caf50;
}

.status-dot.disconnected {
  background: #666;
}

.status-text {
  font-size: 11px;
  color: #aaa;
}

.connection-status.connected .status-text {
  color: #4caf50;
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

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  background: #1e1e1e;
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
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 11px;
  color: #666;
  max-width: 260px;
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
  transition: all 0.2s;
  align-items: flex-start;
}

.event-item:hover {
  background: #2d2d30;
  border-color: #3e4040;
}

/* 事件类型样式 */
.event-item.status {
  padding-left: 8px;
  border-left: 3px solid #4caf50;
}

.event-item.log {
  padding-left: 8px;
  border-left: 3px solid #4caf50;
}

.event-item.debug {
  padding-left: 8px;
  border-left: 3px solid #9e9e9e;
}

.event-item.info {
  padding-left: 8px;
  border-left: 3px solid #2196f3;
}

.event-item.error {
  padding-left: 8px;
  border-left: 3px solid #f44336;
}

.event-item.data {
  padding-left: 8px;
  border-left: 3px solid #2196f3;
}

.event-item.file {
  padding-left: 8px;
  border-left: 3px solid #ff9800;
}

.event-item.execution_completed {
  padding-left: 8px;
  border-left: 3px solid #4caf50;
}

.event-item.execution_failed {
  padding-left: 8px;
  border-left: 3px solid #f44336;
}

.event-item.execution_stopped {
  padding-left: 8px;
  border-left: 3px solid #ff9800;
}

.event-item.is-data {
  flex-direction: column;
  align-items: stretch;
  padding-left: 8px;
  border-left: 3px solid #2196f3;
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

.event-item.status .event-type {
  background: #4caf50;
}

.event-item.log .event-type {
  background: #4caf50;
}

.event-item.debug .event-type {
  background: #9e9e9e;
}

.event-item.info .event-type {
  background: #2196f3;
}

.event-item.error .event-type {
  background: #f44336;
}

.event-item.data .event-type {
  background: #2196f3;
}

.event-item.file .event-type {
  background: #ff9800;
}

.event-item.execution_completed .event-type {
  background: #4caf50;
}

.event-item.execution_failed .event-type {
  background: #f44336;
}

.event-item.execution_stopped .event-type {
  background: #ff9800;
}

.event-node {
  font-size: 11px;
  color: #4caf50;
  background: rgba(76, 175, 80, 0.15);
  padding: 2px 6px;
  border-radius: 3px;
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

/* 数据切换按钮 */
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

/* 滚动条美化 */
.panel-body::-webkit-scrollbar {
  width: 6px;
}

.panel-body::-webkit-scrollbar-track {
  background: transparent;
}

.panel-body::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 3px;
  border: 2px solid #1e1e1e;
}

.panel-body::-webkit-scrollbar-thumb:hover {
  background: #4caf50;
}
</style>