<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
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

// Model 绑定
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

// 状态控制
const showSavePrompt = ref(false);
const pendingSchemaId = ref<string | null>(null);
const showRenameDialog = ref(false);
const renamingSchemaId = ref<string | null>(null);
const newName = ref('');
const showDeleteDialog = ref(false);
const deletingSchemaId = ref<string | null>(null);

const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// 计算当前选中的对象
const activeSchemaItem = computed(() =>
  schemas.value.find(s => s.id === selectedSchemaId.value)
);

const hasSelectedSchema = computed(() => !!selectedSchemaId.value);

// --- 核心修复：监听选中的 Schema 变化并加载到编辑器 ---

function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : {};
}


watch(activeSchemaItem, async (newItem, oldItem) => {
  if (!newItem) return;

  // 仅在 ID 变化时（切换或初次加载）重载 NodeFlow 
  if (!oldItem || newItem.id !== oldItem.id) {
    await nextTick();
    if (nodeFlowRef.value) {

      // deepCopy 切断引用
      nodeFlowRef.value.loadSchema(deepCopy(newItem.schema));
    }
  }
}, { immediate: true });

// 创建
async function createSchema() {
  const newSchema: SchemaItem = {
    id: crypto.randomUUID(),
    name: `Schema ${schemas.value.length + 1}`,
    schema: null,
    hasUnsavedChanges: false
  };
  emit('create', newSchema);

  // 等待父组件更新 schemas 后再选中
  await nextTick();
  selectSchema(newSchema.id);
}

// 选择逻辑
function selectSchema(id: string) {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current && current.hasUnsavedChanges) {
    pendingSchemaId.value = id;
    showSavePrompt.value = true;
    return;
  }
  doSelectSchema(id);
}

function doSelectSchema(id: string) {
  selectedSchemaId.value = id;
  pendingSchemaId.value = null;
  showSavePrompt.value = false;

  const schemaItem = schemas.value.find(s => s.id === id);
  if (schemaItem) {
    schemaItem.hasUnsavedChanges = false;
    // schemas.value = [...schemas.value];
  }
}

// 保存
function saveCurrentSchema() {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (!current || !nodeFlowRef.value) return;

  const currentSchemaData = nodeFlowRef.value.currentSchema;
  if (currentSchemaData !== null) {
    current.schema = currentSchemaData;
    current.hasUnsavedChanges = false;
    emit('save', current.id, currentSchemaData);
    // schemas.value = [...schemas.value];
  }

  if (pendingSchemaId.value) {
    doSelectSchema(pendingSchemaId.value);
  } else {
    showSavePrompt.value = false;
  }
}

function discardAndSwitch() {
  if (pendingSchemaId.value) {
    doSelectSchema(pendingSchemaId.value);
  } else {
    showSavePrompt.value = false;
  }
}

function cancelSwitch() {
  pendingSchemaId.value = null;
  showSavePrompt.value = false;
}

// 删除、重命名、复制逻辑
function deleteSchema(id: string) {
  deletingSchemaId.value = id;
  showDeleteDialog.value = true;
}

function confirmDelete() {
  if (!deletingSchemaId.value) return;
  const idToDelete = deletingSchemaId.value;
  emit('delete', idToDelete);

  if (selectedSchemaId.value === idToDelete) {
    const remaining = schemas.value.filter(s => s.id !== idToDelete);
    if (remaining.length > 0) {
      doSelectSchema(remaining[0].id);
    } else {
      selectedSchemaId.value = null;
      if (nodeFlowRef.value) nodeFlowRef.value.loadSchema(null);
    }
  }
  showDeleteDialog.value = false;
  deletingSchemaId.value = null;
}

function duplicateSchema(id: string) {
  const original = schemas.value.find(s => s.id === id);
  if (original) {
    const newSchema: SchemaItem = {
      id: crypto.randomUUID(),
      name: `${original.name} (副本)`,
      schema: JSON.parse(JSON.stringify(original.schema)),
      hasUnsavedChanges: false
    };
    emit('duplicate', id, newSchema);
    nextTick(() => selectSchema(newSchema.id));
  }
}

function renameSchema(id: string) {
  const schema = schemas.value.find(s => s.id === id);
  if (schema) {
    renamingSchemaId.value = id;
    newName.value = schema.name;
    showRenameDialog.value = true;
  }
}

function confirmRename() {
  if (renamingSchemaId.value && newName.value.trim()) {
    emit('rename', renamingSchemaId.value, newName.value.trim());
  }
  showRenameDialog.value = false;
}

// 子组件事件处理
function handleUpdate(schema: any) { }

function handleUnsavedChanges(hasChanges: boolean) {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) {
    current.hasUnsavedChanges = hasChanges;
    // schemas.value = [...schemas.value];
  }
}

function handleSave(data: any) {
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) {
    current.schema = data;
    current.hasUnsavedChanges = false;
    emit('save', current.id, data);
    // schemas.value = [...schemas.value];
  }
}
</script>

<template>
  <div class="schema-manager">
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

    <div class="schema-editor">
      <NodeFlow ref="nodeFlowRef" :blocks="props.blocks" @update="handleUpdate" @unsavedChanges="handleUnsavedChanges"
        @save="handleSave" />
      <div v-if="!hasSelectedSchema" class="empty-editor-overlay">
        请选择或创建一个 Schema
      </div>
    </div>

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

    <div v-if="showRenameDialog" class="modal-overlay">
      <div class="modal">
        <h3>重命名 Schema</h3>
        <input v-model="newName" @keyup.enter="confirmRename" class="input" autofocus />
        <div class="modal-actions">
          <button @click="confirmRename" class="btn btn-primary">确定</button>
          <button @click="showRenameDialog = false" class="btn">取消</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteDialog" class="modal-overlay">
      <div class="modal">
        <h3>删除 Schema</h3>
        <p>确定要删除这个 Schema 吗？此操作无法撤销。</p>
        <div class="modal-actions">
          <button @click="confirmDelete" class="btn btn-danger">删除</button>
          <button @click="showDeleteDialog = false" class="btn">取消</button>
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