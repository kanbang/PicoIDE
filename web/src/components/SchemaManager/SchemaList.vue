<script setup lang="ts">
import { defineProps, defineEmits } from 'vue';

// 定义接口 (建议最好提取到单独的 types.ts 文件中)
export interface SchemaItem {
  id: string;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

// Props: 接收列表数据和当前选中的ID
const props = defineProps<{
  schemas: SchemaItem[];
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
  <div class="schema-list-container">
    <div class="schema-list-header">
      <h3>Schemas</h3>
      <button @click="emit('create')" class="btn btn-primary">+ 新建</button>
    </div>

    <div class="schema-list-body">
      <div 
        v-for="schema in schemas" 
        :key="schema.id"
        :class="['schema-item', { active: schema.id === selectedId }]" 
        @click="handleSelect(schema.id)"
      >
        <div class="schema-item-content">
          <span class="schema-name" :title="schema.name">{{ schema.name }}</span>
          <span v-if="schema.hasUnsavedChanges" class="unsaved-indicator" title="未保存">●</span>
        </div>
        
        <div class="schema-item-actions">
          <button @click.stop="emit('duplicate', schema.id)" class="btn-icon" title="复制">📋</button>
          <button @click.stop="emit('rename', schema.id)" class="btn-icon" title="重命名">✎</button>
          <button @click.stop="emit('delete', schema.id)" class="btn-icon btn-icon-delete" title="删除">✕</button>
        </div>
      </div>

      <div v-if="schemas.length === 0" class="empty-state">
        暂无 Schema，点击"新建"创建
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 容器占满父容器 */
.schema-list-container {
  width: 100%;
  height: 100%;
  background: #2d2d2d;
  display: flex;
  flex-direction: column;
  user-select: none;
}

.schema-list-header {
  padding: 16px;
  border-bottom: 1px solid #444;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.schema-list-header h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.schema-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 滚动条美化 (可选) */
.schema-list-body::-webkit-scrollbar {
  width: 6px;
}
.schema-list-body::-webkit-scrollbar-thumb {
  background: #555;
  border-radius: 3px;
}

.schema-item {
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

.schema-item:hover {
  background: #4d4d4d;
}

.schema-item.active {
  background: #5a5a5a;
  border-left-color: #4caf50;
}

.schema-item-content {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.schema-name {
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

.schema-item-actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
  flex-shrink: 0;
  opacity: 0; /* 默认隐藏操作按钮 */
  transition: opacity 0.2s;
}

/* 鼠标悬停或选中时显示按钮 */
.schema-item:hover .schema-item-actions,
.schema-item.active .schema-item-actions {
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