<!--
 * @Descripttion: Schema 管理组件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import { ref, onMounted, computed, nextTick } from 'vue';
import NodeFlow from '../NodeFlow/index.vue';

export interface SchemaItem {
  id: string;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

// Props
interface Props {
  blocks: any[];
}

const props = defineProps<Props>();

// 使用 Vue 3.4+ 的 defineModel
const schemas = defineModel<SchemaItem[]>('schemas', { default: () => [] });
const selectedSchemaId = defineModel<string | null>('selectedSchemaId', { default: null });

// Emits
const emit = defineEmits<{
  'save': [id: string, data: any];
  'create': [schema: SchemaItem];
  'delete': [id: string];
  'rename': [id: string, newName: string];
  'duplicate': [id: string, newSchema: SchemaItem];
}>();

// 是否显示保存提示
const showSavePrompt = ref(false);
// 待切换的目标 Schema ID
const pendingSchemaId = ref<string | null>(null);
// 是否显示重命名对话框
const showRenameDialog = ref(false);
// 重命名的 Schema ID
const renamingSchemaId = ref<string | null>(null);
// 新名称
const newName = ref('');
// 是否显示删除确认对话框
const showDeleteDialog = ref(false);
// 待删除的 Schema ID
const deletingSchemaId = ref<string | null>(null);

// 当前选中的 Schema（仅用于判断是否存在）
const hasSelectedSchema = computed(() => selectedSchemaId.value !== null);

// NodeFlow 组件引用
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// 创建新的 Schema
function createSchema(): void {
  const newSchema: SchemaItem = {
    id: crypto.randomUUID(),
    name: `Schema ${schemas.value.length + 1}`,
    schema: null,
    hasUnsavedChanges: false
  };
  emit('create', newSchema);
  selectSchema(newSchema.id);
}

// 选择 Schema
function selectSchema(id: string): void {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current && current.hasUnsavedChanges) {
    pendingSchemaId.value = id;
    showSavePrompt.value = true;
    return;
  }

  doSelectSchema(id);
}



function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : null;
}
// 实际执行选择
async function doSelectSchema(id: string): void {
  selectedSchemaId.value = id;
  pendingSchemaId.value = null;
  showSavePrompt.value = false;

  const schemaItem = schemas.value.find(s => s.id === id);
  if (schemaItem) {
    schemaItem.hasUnsavedChanges = false;
    schemas.value = [...schemas.value];

    await nextTick();
    if (nodeFlowRef.value) {
      nodeFlowRef.value.loadSchema(schemaItem.schema);
    }
  }
}

// 保存当前 Schema（用户明确操作）
function saveCurrentSchema(): void {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (!current || !nodeFlowRef.value) return;

  const currentSchemaData = nodeFlowRef.value.currentSchema;
  if (currentSchemaData !== null) {
    current.schema = currentSchemaData;
    current.hasUnsavedChanges = false;
    emit('save', current.id, currentSchemaData);
    schemas.value = [...schemas.value];
  }

  if (pendingSchemaId.value) {
    doSelectSchema(pendingSchemaId.value);
  } else {
    showSavePrompt.value = false;
  }
}

// 不保存并切换（丢弃 NodeFlow 中的更改，直接切换）
async function discardAndSwitch(): void {
  if (pendingSchemaId.value) {
    doSelectSchema(pendingSchemaId.value);
  } else {
    showSavePrompt.value = false;
  }
}

// 取消切换
function cancelSwitch(): void {
  pendingSchemaId.value = null;
  showSavePrompt.value = false;
}

// 删除 Schema
function deleteSchema(id: string): void {
  deletingSchemaId.value = id;
  showDeleteDialog.value = true;
}

function confirmDelete(): void {
  if (!deletingSchemaId.value) return;

  emit('delete', deletingSchemaId.value);

  if (selectedSchemaId.value === deletingSchemaId.value) {
    if (schemas.value.length > 1) {
      const nextSchema = schemas.value.find(s => s.id !== deletingSchemaId.value);
      if (nextSchema) {
        doSelectSchema(nextSchema.id);
      }
    } else {
      selectedSchemaId.value = null;
      if (nodeFlowRef.value) {
        nodeFlowRef.value.loadSchema(null);
      }
    }
  }

  showDeleteDialog.value = false;
  deletingSchemaId.value = null;
}

function cancelDelete(): void {
  showDeleteDialog.value = false;
  deletingSchemaId.value = null;
}

// 复制 Schema
function duplicateSchema(id: string): void {
  const original = schemas.value.find(s => s.id === id);
  if (original) {
    const newSchema: SchemaItem = {
      id: crypto.randomUUID(),
      name: `Copy of ${original.name}`,
      schema: JSON.parse(JSON.stringify(original.schema)),
      hasUnsavedChanges: false
    };
    emit('duplicate', id, newSchema);
    selectSchema(newSchema.id);
  }
}

// 重命名 Schema
function renameSchema(id: string): void {
  const schema = schemas.value.find(s => s.id === id);
  if (schema) {
    renamingSchemaId.value = id;
    newName.value = schema.name;
    showRenameDialog.value = true;
  }
}

function confirmRename(): void {
  if (renamingSchemaId.value && newName.value.trim()) {
    emit('rename', renamingSchemaId.value, newName.value.trim());
  }
  showRenameDialog.value = false;
  renamingSchemaId.value = null;
  newName.value = '';
}

function cancelRename(): void {
  showRenameDialog.value = false;
  renamingSchemaId.value = null;
  newName.value = '';
}

// 处理 NodeFlow 的更新事件（不再更新 parent 的 schema，仅在保存时更新）
function handleUpdate(schema: any): void {
  // 空实现：更改仅保留在 NodeFlow 中，直到明确保存
}

// 处理未保存状态（完全信任子组件）
function handleUnsavedChanges(hasChanges: boolean): void {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) {
    current.hasUnsavedChanges = hasChanges;
    schemas.value = [...schemas.value];
  }
}

// 处理保存事件（用户点击保存按钮）
function handleSave(data: any): void {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) {
    current.schema = data;
    current.hasUnsavedChanges = false;
    emit('save', current.id, data);
    schemas.value = [...schemas.value];
  }
}

// 组件挂载时加载选中的 schema
onMounted(async () => {
  if (selectedSchemaId.value) {
    await nextTick();
    doSelectSchema(selectedSchemaId.value);
  }
});
</script>

<template>
  <div class="schema-manager">
    <!-- 左侧 Schema 列表 -->
    <div class="schema-list">
      <div class="schema-list-header">
        <h3>Schemas</h3>
        <button @click="createSchema" class="btn btn-primary">+ 新建</button>
      </div>
      <div class="schema-list-body">
        <div v-for="schema in schemas" :key="schema.id"
          :class="['schema-item', { active: schema.id === selectedSchemaId }]" @click="selectSchema(schema.id)">
          <div class="schema-item-content">
            <span class="schema-name">{{ schema.name }}</span>
            <span v-if="schema.hasUnsavedChanges" class="unsaved-indicator">●</span>
          </div>
          <div class="schema-item-actions">
            <button @click.stop="duplicateSchema(schema.id)" class="btn-icon" title="复制">📋</button>
            <button @click.stop="renameSchema(schema.id)" class="btn-icon" title="重命名">✎</button>
            <button @click.stop="deleteSchema(schema.id)" class="btn-icon btn-icon-delete" title="删除">✕</button>
          </div>
        </div>
        <div v-if="!schemas || schemas.length === 0" class="empty-state">
          暂无 Schema，点击"新建"创建
        </div>
      </div>
    </div>

    <!-- 右侧 NodeFlow 编辑器（始终挂载） -->
    <div class="schema-editor">
      <NodeFlow ref="nodeFlowRef" :blocks="props.blocks" @update="handleUpdate" @unsavedChanges="handleUnsavedChanges"
        @save="handleSave" />
      <div v-if="!hasSelectedSchema" class="empty-editor-overlay">
        请选择或创建一个 Schema
      </div>
    </div>

    <!-- 保存提示对话框 -->
    <div v-if="showSavePrompt" class="modal-overlay">
      <div class="modal">
        <h3>未保存的更改</h3>
        <p>当前 Schema 有未保存的更改，是否保存？</p>
        <div class="modal-actions">
          <button @click="saveCurrentSchema" class="btn btn-primary">保存</button>
          <button @click="discardAndSwitch" class="btn">不保存</button>
          <button @click="cancelSwitch" class="btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 重命名对话框 -->
    <div v-if="showRenameDialog" class="modal-overlay">
      <div class="modal">
        <h3>重命名 Schema</h3>
        <input v-model="newName" @keyup.enter="confirmRename" @keyup.esc="cancelRename" class="input"
          placeholder="输入新名称" autofocus />
        <div class="modal-actions">
          <button @click="confirmRename" class="btn btn-primary">确定</button>
          <button @click="cancelRename" class="btn">取消</button>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="showDeleteDialog" class="modal-overlay">
      <div class="modal">
        <h3>删除 Schema</h3>
        <p>确定要删除这个 Schema 吗？此操作无法撤销。</p>
        <div class="modal-actions">
          <button @click="confirmDelete" class="btn btn-danger">删除</button>
          <button @click="cancelDelete" class="btn">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 原样式保持不变，仅新增一个 overlay 用于空状态覆盖 */
.empty-editor-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.3);
  color: #888;
  font-size: 16px;
  pointer-events: none;
  z-index: 10;
}

.schema-manager {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.schema-list {
  width: 300px;
  background: #2d2d2d;
  border-right: 1px solid #444;
  display: flex;
  flex-direction: column;
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

.schema-editor {
  flex: 1;
  overflow: hidden;
}

.empty-editor {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #888;
  font-size: 16px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #2d2d2d;
  padding: 24px;
  border-radius: 8px;
  min-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.modal h3 {
  margin: 0 0 16px 0;
  color: #fff;
  font-size: 18px;
}

.modal p {
  margin: 0 0 24px 0;
  color: #ccc;
  font-size: 14px;
}

.input {
  width: 100%;
  padding: 8px 12px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
  margin-bottom: 16px;
  box-sizing: border-box;
}

.input:focus {
  outline: none;
  border-color: #4caf50;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
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

.btn-danger {
  background: #f44336;
  border-color: #f44336;
}

.btn-danger:hover {
  background: #d32f2f;
}
</style>