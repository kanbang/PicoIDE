<script setup lang="ts">
import { computed } from 'vue';

export interface SchemaItem {
  id: string;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

interface Props {
  schemas: SchemaItem[];
  selectedId: string | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  select: [id: string];
  create: [];
  duplicate: [id: string];
  rename: [id: string];
  delete: [id: string];
}>();

const hasSchemas = computed(() => props.schemas.length > 0);
</script>

<template>
  <div class="schema-list">
    <div class="schema-list-header">
      <h3>Schemas</h3>
      <button @click="emit('create')" class="btn btn-primary">+ 新建</button>
    </div>
    <div class="schema-list-body">
      <div
        v-for="schema in schemas"
        :key="schema.id"
        :class="['schema-item', { active: schema.id === selectedId }]"
        @click="emit('select', schema.id)"
      >
        <div class="schema-item-content">
          <span class="schema-name">{{ schema.name }}</span>
          <span v-if="schema.hasUnsavedChanges" class="unsaved-indicator">●</span>
        </div>
        <div class="schema-item-actions">
          <button @click.stop="emit('duplicate', schema.id)" class="btn-icon" title="复制">📋</button>
          <button @click.stop="emit('rename', schema.id)" class="btn-icon" title="重命名">✎</button>
          <button @click.stop="emit('delete', schema.id)" class="btn-icon btn-icon-delete" title="删除">✕</button>
        </div>
      </div>
      <div v-if="!hasSchemas" class="empty-state">
        暂无 Schema，点击"新建"创建
      </div>
    </div>
  </div>
</template>

<style scoped>
.schema-list {
  background: #2d2d2d;
  border-right: 1px solid #444;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.schema-list-header {
  padding: 16px;
  border-bottom: 1px solid #444;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.schema-list-header h3 {
  margin: 0;
  color: #fff;
  font-size: 16px;
}

.schema-list-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.schema-item {
  padding: 8px 12px;
  margin-bottom: 4px;
  background: #3d3d3d;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 40px;
  box-sizing: border-box;
}

.schema-item:hover {
  background: #4d4d4d;
}

.schema-item.active {
  background: #5a5a5a;
  border-left: 3px solid #4caf50;
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
}

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
  line-height: 1;
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

.btn {
  padding: 8px 16px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.btn:hover {
  background: #4d4d4d;
}

.btn-primary {
  background: #4caf50;
  border-color: #4caf50;
}

.btn-primary:hover {
  background: #45a049;
}
</style>