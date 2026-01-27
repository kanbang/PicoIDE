<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue';

// SSE Event Type
export interface SSEEvent {
  type: string;
  node_id?: string;
  message?: string;
  timestamp?: string;
  data?: any;
}

interface Props {
  executionId?: string;
  isVisible?: boolean;
}

const props = defineProps<Props>();

// 状态
const visible = ref(props.isVisible || false);
const events = ref<SSEEvent[]>([]);
const isConnecting = ref(false);
const isConnected = ref(false);
const eventSourceRef = ref<EventSource | null>(null);
const containerRef = ref<HTMLElement | null>(null);

// 监听 props.isVisible 变化
watch(() => props.isVisible, (newValue) => {
  visible.value = newValue;
});

// 监听 executionId 变化
watch(() => props.executionId, (newId, oldId) => {
  if (oldId && oldId !== newId) {
    disconnectSSE();
  }
  if (newId) {
    connectSSE(newId);
  }
});

// 显示/隐藏功能
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

// SSE 连接管理
function connectSSE(executionId: string) {
  if (!executionId) return;

  disconnectSSE(); // 断开旧连接

  isConnecting.value = true;
  events.value = []; // 清空之前的事件

  // 构建SSE URL
  const baseUrl = window.location.origin;
  const url = `${baseUrl}/api/engine/stream/${executionId}`;

  try {
    const eventSource = new EventSource(url);
    eventSourceRef.value = eventSource;

    eventSource.onopen = () => {
      isConnecting.value = false;
      isConnected.value = true;
      console.log('SSE connection established');
    };

    eventSource.onmessage = (event) => {
      try {
        // SSE消息格式: data: {...}
        if (event.data.startsWith('data: ')) {
          const eventData = JSON.parse(event.data.slice(6));
          events.value.push({
            ...eventData,
            timestamp: eventData.timestamp || new Date().toISOString()
          });
          nextTick(() => scrollToBottom());
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      isConnecting.value = false;
      isConnected.value = false;
      // 自动重连
      setTimeout(() => {
        if (props.executionId && !eventSourceRef.value) {
          connectSSE(props.executionId);
        }
      }, 3000);
    };

  } catch (error) {
    console.error('Failed to create SSE connection:', error);
    isConnecting.value = false;
    isConnected.value = false;
  }
}

function disconnectSSE() {
  if (eventSourceRef.value) {
    eventSourceRef.value.close();
    eventSourceRef.value = null;
  }
  isConnected.value = false;
  isConnecting.value = false;
}

function clearEvents() {
  events.value = [];
}

function scrollToBottom() {
  if (containerRef.value) {
    containerRef.value.scrollTop = containerRef.value.scrollHeight;
  }
}

// 格式化时间
function formatTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  // 如果差异很小，直接显示时间
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

// 获取事件类型图标
function getEventIcon(event: SSEEvent) {
  const type = event.type?.toLowerCase() || 'info';

  switch (type) {
    case 'status':
      return {
        svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="16" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>`,
        color: '#888'
      };
    case 'node_start':
      return {
        svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>`,
        color: '#4caf50'
      };
    case 'node_complete':
      return {
        svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"/>
        </svg>`,
        color: '#4caf50'
      };
    case 'node_error':
      return {
        svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>`,
        color: '#f44336'
      };
    default:
      return {
        svg: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>`,
        color: '#888'
      };
  }
}

// 格式化数据展示
function formatData(data: any): string {
  if (data === null || data === undefined) return '';
  if (typeof data === 'string') return data;
  if (typeof data === 'number') return data.toString();
  if (typeof data === 'boolean') return data ? 'true' : 'false';
  return JSON.stringify(data, null, 2);
}

// 清理
onUnmounted(() => {
  disconnectSSE();
});

// 暴露方法供父组件调用
defineExpose({
  connect: connectSSE,
  disconnect: disconnectSSE,
  clear: clearEvents,
  show,
  hide,
  toggle,
  visible,
});
</script>

<template>
  <div class="sse-panel" :class="{ visible }">
    <!-- 面板头部 -->
    <div class="panel-header">
      <div class="header-left">
        <svg class="header-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
        <span class="header-title">执行日志</span>
        <span v-if="events.length > 0" class="event-count">{{ events.length }}</span>
      </div>
      <div class="header-right">
        <!-- 连接状态 -->
        <div class="connection-status" :class="{ connected: isConnected, connecting: isConnecting }">
          <span v-if="isConnecting" class="status-dot connecting"></span>
          <span v-else-if="isConnected" class="status-dot connected"></span>
          <span v-else class="status-dot disconnected"></span>
          <span class="status-text">
            {{ isConnecting ? '连接中...' : isConnected ? '已连接' : '未连接' }}
          </span>
        </div>
        <!-- 清空按钮 -->
        <button @click="clearEvents" class="header-btn" title="清空日志">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
        <!-- 关闭按钮 -->
        <button @click="hide" class="header-btn close-btn" title="关闭">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 事件列表 -->
    <div class="panel-body" ref="containerRef">
      <!-- 空状态 -->
      <div v-if="events.length === 0 && !isConnecting && !isConnected" class="empty-state">
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

      <!-- 加载状态 -->
      <div v-else-if="isConnecting" class="loading-state">
        <div class="spinner"></div>
        <div class="loading-text">连接中...</div>
      </div>

      <!-- 事件列表 -->
      <div v-else class="event-list">
        <div
          v-for="(event, index) in events"
          :key="index"
          class="event-item"
          :class="[event.type?.toLowerCase()]"
        >
          <div class="event-icon" :style="{ color: getEventIcon(event).color }" v-html="getEventIcon(event).svg"></div>
          <div class="event-content">
            <div class="event-header">
              <span class="event-type">{{ event.type || 'INFO' }}</span>
              <span v-if="event.node_id" class="event-node">{{ event.node_id }}</span>
              <span class="event-time">{{ formatTime(event.timestamp || '') }}</span>
            </div>
            <div v-if="event.message" class="event-message">{{ event.message }}</div>
            <div v-if="event.data" class="event-data">
              <pre>{{ formatData(event.data) }}</pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sse-panel {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 0;
  background: #1e1e1e;
  border-top: 1px solid #333;
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 100;
}

.sse-panel.visible {
  height: 350px;
}

/* 面板头部 */
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
  font-size: 12px;
  font-weight: 500;
  color: #ccc;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.event-count {
  background: #333;
  color: #aaa;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 连接状态 */
.connection-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  background: #2d2d30;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #666;
}

.status-dot.connecting {
  background: #ffa726;
  animation: pulse 1s infinite;
}

.status-dot.connected {
  background: #4caf50;
}

.status-dot.disconnected {
  background: #666;
}

.status-text {
  font-size: 11px;
  color: #888;
}

.connection-status.connected .status-text {
  color: #4caf50;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 头部按钮 */
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
  background: #37373d;
  color: #fff;
}

.header-btn.close-btn:hover {
  background: #902722;
  color: #fff;
}

/* 面板主体 */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  background: #1e1e1e;
}

/* 空状态 */
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
  opacity: 0.2;
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

/* 加载状态 */
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
  border-top-color: #007acc;
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

/* 事件列表 */
.event-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-item {
  display: flex;
  gap: 10px;
  padding: 8px 10px;
  background: #252526;
  border-radius: 6px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.event-item:hover {
  background: #2d2d30;
  border-color: #3e3e40;
}

.event-item.status {
  background: rgba(0, 122, 204, 0.1);
}

.event-item.node_start {
  background: rgba(76, 175, 80, 0.1);
}

.event-item.node_complete {
  background: rgba(76, 175, 80, 0.1);
}

.event-item.node_error {
  background: rgba(244, 67, 54, 0.1);
  border-color: rgba(244, 67, 54, 0.3);
}

.event-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.event-content {
  flex: 1;
  min-width: 0;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.event-type {
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  color: #888;
}

.event-node {
  font-size: 10px;
  color: #007acc;
  background: rgba(0, 122, 204, 0.15);
  padding: 1px 6px;
  border-radius: 3px;
}

.event-time {
  font-size: 10px;
  color: #666;
  margin-left: auto;
}

.event-message {
  font-size: 12px;
  color: #ccc;
  line-height: 1.5;
  word-break: break-word;
}

.event-data {
  margin-top: 6px;
  padding: 8px;
  background: #1a1a1a;
  border-radius: 4px;
  border: 1px solid #333;
}

.event-data pre {
  margin: 0;
  font-size: 11px;
  color: #888;
  font-family: 'Consolas', 'Monaco', monospace;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 150px;
  overflow-y: auto;
}

/* 滚动条美化 */
.panel-body::-webkit-scrollbar {
  width: 8px;
}

.panel-body::-webkit-scrollbar-track {
  background: transparent;
}

.panel-body::-webkit-scrollbar-thumb {
  background: #333;
  border-radius: 4px;
  border: 2px solid #1e1e1e;
}

.panel-body::-webkit-scrollbar-thumb:hover {
  background: #444;
}
</style>
