<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import NodeFlow from '../NodeFlow/index.vue';
import SchemaList from './SchemaList.vue';
import Modal from '../common/Modal.vue';
import Splitter from '../common/Splitter.vue';

export interface SchemaItem {
  id: string;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

// Props
interface Props {
  blocks: any[];
  showRun?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showRun: true
});

// Model 绑定
const schemas = defineModel<SchemaItem[]>('schemas', { default: () => [] });
const selectedSchemaId = defineModel<string | null>('selectedSchemaId', { default: null });

// Emits
const emit = defineEmits<{
  save: [id: string, data: any];
  create: [schema: SchemaItem];
  delete: [id: string];
  rename: [id: string, newName: string];
  duplicate: [id: string, newSchema: SchemaItem];
  run: [id: string, data: any];
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

// 分割条拖拽
const listWidth = ref(300);
const isListVisible = ref(true);

function handleSplitterDrag(delta: number) {
  const newWidth = listWidth.value + delta;
  if (newWidth >= 200 && newWidth <= 600) {
    listWidth.value = newWidth;
  }
}

function toggleList() {
  isListVisible.value = !isListVisible.value;
}

// 当前选中项
const activeSchemaItem = computed(() =>
  schemas.value.find(s => s.id === selectedSchemaId.value)
);

const hasSelectedSchema = computed(() => !!selectedSchemaId.value && !!activeSchemaItem.value);

// 关键：schemas 变化时维护 selectedSchemaId
watch(schemas, () => {
  if (schemas.value.length === 0) {
    selectedSchemaId.value = null;
    return;
  }

  if (!selectedSchemaId.value || !schemas.value.some(s => s.id === selectedSchemaId.value)) {
    doSelectSchema(schemas.value[0].id);
  }
}, { deep: true, immediate: true });

// 监听选中变化并加载到 NodeFlow
function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : null;
}

watch(activeSchemaItem, async (newItem) => {
  await nextTick();
  if (!newItem) {
    nodeFlowRef.value?.loadSchema(null);
    return;
  }
  nodeFlowRef.value?.loadSchema(deepCopy(newItem.schema));
}, { immediate: true });

// 创建
function createSchema() {
  const newSchema: SchemaItem = {
    id: '',
    name: `Schema ${schemas.value.length + 1}`,
    schema: null,
    hasUnsavedChanges: false
  };
  emit('create', newSchema);
}

// 选择逻辑
function selectSchema(id: string) {
  if (activeSchemaItem.value?.hasUnsavedChanges) {
    pendingSchemaId.value = id;
    showSavePrompt.value = true;
    return;
  }
  doSelectSchema(id);
}

function doSelectSchema(id: string) {
  // 清除未保存标记（切换成功即视为已“确认”当前状态）
  const schemaItem = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (schemaItem) {
    schemaItem.hasUnsavedChanges = false;
  }

  selectedSchemaId.value = id;
  pendingSchemaId.value = null;
  showSavePrompt.value = false;
}

// 保存当前
function saveCurrentSchema() {
  if (!selectedSchemaId.value || !nodeFlowRef.value) return;

  const data = nodeFlowRef.value.currentSchema;
  if (data !== null) {
    const current = schemas.value.find(s => s.id === selectedSchemaId.value);
    if (current) {
      current.schema = data;
      current.hasUnsavedChanges = false;
    }
    emit('save', selectedSchemaId.value, data);
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

// 删除（修复索引：删除后原下一个变成 oldIndex）
function deleteSchema(id: string) {
  deletingSchemaId.value = id;
  showDeleteDialog.value = true;
}

function confirmDelete() {
  if (!deletingSchemaId.value) return;
  const idToDelete = deletingSchemaId.value;

  // 预记录是否删除当前 + 旧索引
  const isDeletingCurrent = selectedSchemaId.value === idToDelete;
  let oldIndex = -1;
  if (isDeletingCurrent) {
    oldIndex = schemas.value.findIndex(s => s.id === idToDelete);
  }

  emit('delete', idToDelete);

  nextTick(() => {
    if (schemas.value.length === 0) {
      selectedSchemaId.value = null;
      return;
    }

    if (isDeletingCurrent && oldIndex !== -1) {
      // 删除后：
      let newIndex = oldIndex;
      if (oldIndex >= schemas.value.length) {
        // 删除最后一个 → 选中上一个
        newIndex = schemas.value.length - 1;
      }
      doSelectSchema(schemas.value[newIndex].id);
    }
    // 非当前删除：watch 已处理
  });

  showDeleteDialog.value = false;
  deletingSchemaId.value = null;
}

function duplicateSchema(id: string) {
  const original = schemas.value.find(s => s.id === id);
  if (!original) return;

  const newSchema: SchemaItem = {
    id: '',
    name: `${original.name} (副本)`,
    schema: deepCopy(original.schema),
    hasUnsavedChanges: false
  };
  emit('duplicate', id, newSchema);
}

function renameSchema(id: string) {
  const schema = schemas.value.find(s => s.id === id);
  if (!schema) return;

  renamingSchemaId.value = id;
  newName.value = schema.name;
  showRenameDialog.value = true;
}

function confirmRename() {
  if (renamingSchemaId.value && newName.value.trim()) {
    emit('rename', renamingSchemaId.value, newName.value.trim());
  }
  showRenameDialog.value = false;
}

// NodeFlow 事件处理
function handleUpdate(_schema: any) {
  // 若需要实时更新，可在这里处理（当前未使用）
}

function handleUnsavedChanges(hasChanges: boolean) {
  if (!selectedSchemaId.value) return;
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) current.hasUnsavedChanges = hasChanges;
}

function handleSave(data: any) {
  if (!selectedSchemaId.value) return;
  const current = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (current) {
    current.schema = data;
    current.hasUnsavedChanges = false;
    emit('save', selectedSchemaId.value, data);
  }
}

function handleRun(data: any) {
  if (!selectedSchemaId.value) return;
  emit('run', selectedSchemaId.value, data);
}

// 暴露方法供父组件调用
defineExpose({
  nodeFlowRef
});
</script>
<template>
  <div class="schema-manager">
    <SchemaList 
      v-if="isListVisible"
      :schemas="schemas"
      :selected-id="selectedSchemaId"
      :width="listWidth"
      @select="selectSchema"
      @create="createSchema"
      @duplicate="duplicateSchema"
      @rename="renameSchema"
      @delete="deleteSchema"
    />

    <Splitter
      v-if="isListVisible"
      direction="horizontal"
      :min-size="200"
      :max-size="600"
      @drag="handleSplitterDrag"
    />

    <div class="schema-editor">
      <button @click="toggleList" class="btn-toggle-overlay" :title="isListVisible ? '隐藏列表' : '显示列表'">
        <svg v-if="isListVisible" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M6 1L2 5L6 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M4 1L8 5L4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>

      <NodeFlow v-if="hasSelectedSchema" ref="nodeFlowRef" :blocks="props.blocks" :show-run="props.showRun"
        @update="handleUpdate" @unsavedChanges="handleUnsavedChanges" @save="handleSave" @run="handleRun" />

      <div v-if="!hasSelectedSchema" class="empty-editor-full">
        <div class="empty-message">
          <div class="empty-title">暂无 Schema</div>
          <div class="empty-subtitle">请在左侧列表中新建或选择一个 Schema 开始编辑</div>
        </div>
      </div>
    </div>

    <!-- 模态框 -->
    <Modal v-model:visible="showSavePrompt" title="未保存的更改" size="small" @close="cancelSwitch">
      <p>当前 Schema 有未保存的更改，是否保存？</p>
      <template #footer>
        <button @click="saveCurrentSchema" class="btn btn-primary">保存</button>
        <button @click="discardAndSwitch" class="btn">不保存</button>
        <button @click="cancelSwitch" class="btn">取消</button>
      </template>
    </Modal>

    <Modal v-model:visible="showRenameDialog" title="重命名 Schema" size="small" @close="showRenameDialog = false">
      <input v-model="newName" @keyup.enter="confirmRename" class="input" autofocus />
      <template #footer>
        <button @click="confirmRename" class="btn btn-primary">确定</button>
        <button @click="showRenameDialog = false" class="btn">取消</button>
      </template>
    </Modal>

    <Modal v-model:visible="showDeleteDialog" title="删除 Schema" size="small" @close="showDeleteDialog = false">
      <p>确定要删除这个 Schema 吗？此操作无法撤销。</p>
      <template #footer>
        <button @click="confirmDelete" class="btn btn-danger">删除</button>
        <button @click="showDeleteDialog = false" class="btn">取消</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.empty-editor-full {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(30, 30, 30, 0.95);
  color: #888;
  text-align: center;
  z-index: 10;
  pointer-events: none;
}

.empty-message {
  max-width: 400px;
  padding: 32px;
}

.empty-title {
  font-size: 24px;
  color: #ccc;
  margin-bottom: 12px;
}

.empty-subtitle {
  font-size: 16px;
  color: #999;
}


.schema-manager {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.schema-list {
  min-width: 200px;
  max-width: 600px;
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
  position: relative;
}

.btn-toggle-overlay {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 60px;
  background: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: 0 6px 6px 0;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: all 0.25s ease;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.3);
  padding: 0;
}

.btn-toggle-overlay:hover {
  width: 20px;
  background: rgba(50, 50, 50, 0.9);
  color: #fff;
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.5);
}

.btn-toggle-overlay svg {
  width: 12px;
  height: 12px;
  stroke-width: 2;
}

/* Modal 内部样式 */
.input {
  width: 100%;
  padding: 10px 12px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 6px;
  color: #fff;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.input:focus {
  outline: none;
  border-color: #4caf50;
}

.btn {
  padding: 10px 20px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 6px;
  color: #fff;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn:hover {
  background: #4d4d4d;
  transform: translateY(-1px);
}

.btn-primary {
  background: #4caf50;
  border-color: #4caf50;
}

.btn-primary:hover {
  background: #45a049;
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-danger {
  background: #f44336;
  border-color: #f44336;
}

.btn-danger:hover {
  background: #d32f2f;
  box-shadow: 0 4px 12px rgba(244, 67, 54, 0.3);
}
</style>