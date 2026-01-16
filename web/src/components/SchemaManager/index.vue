<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import NodeFlow from '../NodeFlow/index.vue';
import Modal from '../common/Modal.vue';
import SplitPane from '../common/Splitter.vue';
import SchemaList, { SchemaItem } from './SchemaList.vue'; // 引入新组件

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

// --- 状态控制 (Modal 等) ---
const showSavePrompt = ref(false);
const pendingSchemaId = ref<string | null>(null);
const showRenameDialog = ref(false);
const renamingSchemaId = ref<string | null>(null);
const newName = ref('');
const showDeleteDialog = ref(false);
const deletingSchemaId = ref<string | null>(null);

const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// --- 计算属性 ---
const activeSchemaItem = computed(() =>
  schemas.value.find(s => s.id === selectedSchemaId.value)
);

const hasSelectedSchema = computed(() => !!selectedSchemaId.value && !!activeSchemaItem.value);

// --- 监听器 ---
// 确保选中 ID 有效
watch(schemas, () => {
  if (schemas.value.length === 0) {
    selectedSchemaId.value = null;
    return;
  }
  if (!selectedSchemaId.value || !schemas.value.some(s => s.id === selectedSchemaId.value)) {
    doSelectSchema(schemas.value[0].id);
  }
}, { deep: true, immediate: true });

function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : null;
}

// 加载 Schema 到编辑器
watch(activeSchemaItem, async (newItem) => {
  await nextTick();
  if (!newItem) {
    nodeFlowRef.value?.loadSchema(null);
    return;
  }
  nodeFlowRef.value?.loadSchema(deepCopy(newItem.schema));
}, { immediate: true });

// --- 动作处理 (Actions) ---

// 1. 新建
function createSchema() {
  const newSchema: SchemaItem = {
    id: '', // 应由后端或父级生成 UUID，这里暂时留空
    name: `Schema ${schemas.value.length + 1}`,
    schema: null,
    hasUnsavedChanges: false
  };
  emit('create', newSchema);
}

// 2. 选择 (包含未保存检查)
function selectSchema(id: string) {
  if (activeSchemaItem.value?.hasUnsavedChanges) {
    pendingSchemaId.value = id;
    showSavePrompt.value = true;
    return;
  }
  doSelectSchema(id);
}

function doSelectSchema(id: string) {
  const schemaItem = schemas.value.find(s => s.id === selectedSchemaId.value);
  if (schemaItem) {
    schemaItem.hasUnsavedChanges = false;
  }
  selectedSchemaId.value = id;
  pendingSchemaId.value = null;
  showSavePrompt.value = false;
}

// 3. 保存逻辑
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

// 4. 删除逻辑
function handleDeleteRequest(id: string) {
  deletingSchemaId.value = id;
  showDeleteDialog.value = true;
}

function confirmDelete() {
  if (!deletingSchemaId.value) return;
  const idToDelete = deletingSchemaId.value;
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
      let newIndex = oldIndex;
      if (oldIndex >= schemas.value.length) {
        newIndex = schemas.value.length - 1;
      }
      doSelectSchema(schemas.value[newIndex].id);
    }
  });

  showDeleteDialog.value = false;
  deletingSchemaId.value = null;
}

// 5. 复制
function handleDuplicateRequest(id: string) {
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

// 6. 重命名
function handleRenameRequest(id: string) {
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

// --- NodeFlow 事件处理 ---
function handleUpdate(_schema: any) {}

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

defineExpose({ nodeFlowRef });
</script>

<template>
  <div class="schema-manager">
    
    <SplitPane 
      direction="horizontal" 
      :min="200" 
      :max="600" 
      :initial-size="300" 
      button-side="left"
    >
      <template #1>
        <SchemaList 
          :schemas="schemas" 
          :selected-id="selectedSchemaId"
          @create="createSchema"
          @select="selectSchema"
          @duplicate="handleDuplicateRequest"
          @rename="handleRenameRequest"
          @delete="handleDeleteRequest"
        />
      </template>

      <template #2>
        <div class="schema-editor">
          <NodeFlow v-if="hasSelectedSchema" ref="nodeFlowRef" :blocks="props.blocks" :show-run="props.showRun"
            @update="handleUpdate" @unsavedChanges="handleUnsavedChanges" @save="handleSave" @run="handleRun" />

          <div v-if="!hasSelectedSchema" class="empty-editor-full">
            <div class="empty-message">
              <div class="empty-title">暂无 Schema</div>
              <div class="empty-subtitle">请在左侧列表中新建或选择一个 Schema 开始编辑</div>
            </div>
          </div>
        </div>
      </template>
    </SplitPane>

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
.schema-manager {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* 编辑器部分样式保持不变 */
.schema-editor {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

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

/* Modal Internal Styles (Generic) */
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