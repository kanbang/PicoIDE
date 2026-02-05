<script setup lang="ts">
import { defineProps, defineEmits } from 'vue';

// 定义接口 (建议最好提取到单独的 types.ts 文件中)
export interface FlowItem {
  id: string;
  name: string;
  flow: any;
  hasUnsavedChanges: boolean;
}

// Props: 接收列表数据和当前选中的ID
const props = defineProps<{
  flows: FlowItem[];
  selectedId: string | null;
}>();

// Emits: 向父组件发送事件
const emit = defineEmits<{
  (e: 'create'): void;
  (e: 'select', id: string): void;
  (e: 'duplicate', id: string): void;
  (e: 'rename', id: string): void;
  (e: 'delete', id: string): void;
}>();

// 处理点击事件
function handleSelect(id: string) {
  // 不直接修改 props，而是通知父组件
  emit('select', id);
}
</script>

<template>
  <div class="flow-list-container">
    <header class="panel-header">
      <div class="title-group">
        <svg class="header-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
        <h3>Flows</h3>
        <span class="file-count" v-if="flows.length">{{ flows.length }}</span>
      </div>
      <button @click="emit('create')" class="action-btn highlight" title="新建">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </header>

    <div class="panel-body">
      <div v-if="flows.length > 0" class="file-grid">
        <div 
          v-for="flow in flows" 
          :key="flow.id"
          :class="['file-card', { active: flow.id === selectedId }]" 
          @click="handleSelect(flow.id)"
        >
          <div class="card-content">
            <div class="name-row">
              <span class="name" :title="flow.name">{{ flow.name }}</span>
              <span v-if="flow.hasUnsavedChanges" class="unsaved-dot" title="未保存"></span>
            </div>
          </div>

          <div class="card-actions">
            <button @click.stop="emit('duplicate', flow.id)" class="icon-btn" title="复制">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
            </button>
            <button @click.stop="emit('rename', flow.id)" class="icon-btn" title="重命名">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            <button @click.stop="emit('delete', flow.id)" class="icon-btn danger" title="删除">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <div class="empty-illustration">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="2" y="2" width="20" height="20" rx="2" ry="2" />
            <path d="M14 2v6h6" />
            <path d="M16 13H8" />
            <path d="M16 17H8" />
            <path d="M10 9H8" />
          </svg>
        </div>
        <h4>暂无 Flow</h4>
        <p>点击右上角的 + 按钮创建新的 Flow 流程</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 核心容器 */
.flow-list-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #1e1e1e;
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
.action-btn.highlight { color: #4caf50; }
.action-btn.highlight:hover { background: #4caf50; color: #fff; }

/* 主体内容区 */
.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 文件网格 */
.file-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
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
  cursor: pointer;
  position: relative;
}

.file-card:hover {
  background: #2d2d30;
  border-color: #444;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.file-card.active {
  background: #2d2d30;
  border-left: 4px solid #4caf50;
  border-right: none;
  border-top: none;
  border-bottom: none;
}

.card-content { flex: 1; min-width: 0; }

.name-row { display: flex; align-items: center; gap: 8px; }
.name {
  font-size: 13px;
  color: #e1e1e1;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unsaved-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ff9800;
  flex-shrink: 0;
}

/* 按钮组 */
.card-actions {
  display: flex;
  gap: 4px;
  opacity: 0.4;
  transition: opacity 0.2s;
}

.file-card:hover .card-actions,
.file-card.active .card-actions { opacity: 1; }

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