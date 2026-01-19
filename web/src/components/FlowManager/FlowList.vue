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
    <div class="flow-list-header">
      <h3>Flows</h3>
      <button @click="emit('create')" class="btn btn-primary">+ 新建</button>
    </div>

    <div class="flow-list-body">
      <div 
        v-for="flow in flows" 
        :key="flow.id"
        :class="['flow-item', { active: flow.id === selectedId }]" 
        @click="handleSelect(flow.id)"
      >
        <div class="flow-item-content">
          <span class="flow-name" :title="flow.name">{{ flow.name }}</span>
          <span v-if="flow.hasUnsavedChanges" class="unsaved-indicator" title="未保存">●</span>
        </div>
        
        <div class="flow-item-actions">
          <button @click.stop="emit('duplicate', flow.id)" class="btn-icon" title="复制">📋</button>
          <button @click.stop="emit('rename', flow.id)" class="btn-icon" title="重命名">✎</button>
          <button @click.stop="emit('delete', flow.id)" class="btn-icon btn-icon-delete" title="删除">✕</button>
        </div>
      </div>

      <div v-if="flows.length === 0" class="empty-state">
        暂无 Flow，点击"新建"创建
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 容器占满父容器 */
.flow-list-container {
  width: 100%;
  height: 100%;
  background: #2d2d2d;
  display: flex;
  flex-direction: column;
  user-select: none;
}

.flow-list-header {
  padding: 16px;
  border-bottom: 1px solid #444;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.flow-list-header h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.flow-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 滚动条美化 (可选) */
.flow-list-body::-webkit-scrollbar {
  width: 6px;
}
.flow-list-body::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.flow-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  background: #3d3d3d;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 40px;
  box-sizing: border-box;
  border-left: 3px solid transparent;
}

.flow-item:hover {
  background: #4d4d4d;
}

.flow-item.active {
  background: #5a5a5a;
  border-left-color: #4caf50;
}

.flow-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.flow-name {
  color: #fff;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.unsaved-indicator {
  color: #ff9800;
  font-size: 12px;
  flex-shrink: 0;
}

.flow-item-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  flex-shrink: 0;
  opacity: 0; /* 默认隐藏操作按钮 */
  transition: opacity 0.2s;
}

/* 鼠标悬停或选中时显示按钮 */
.flow-item:hover .flow-item-actions,
.flow-item.active .flow-item-actions {
  opacity: 1;
}

/* 按钮基础样式 (复制自原代码) */
.btn {
  padding: 6px 12px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}
.btn:hover { background: #4d4d4d; }

.btn-primary {
  background: #4caf50;
  border-color: #4caf50;
}
.btn-primary:hover { background: #45a049; }

/* 图标按钮样式 */
.btn-icon {
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  width: 24px;
  height: 24px;
  font-size: 12px;
  border-radius: 4px;
  transition: color 0.2s, background 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.btn-icon-delete:hover {
  background: #f44336;
  color: #fff;
}

.empty-state {
  color: #888;
  text-align: center;
  padding: 32px 16px;
  font-size: 14px;
}
</style>