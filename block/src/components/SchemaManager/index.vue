<!--
 * @Descripttion: Schema 管理组件
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09
-->
<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import NodeFlow from '../NodeFlow/index.vue';

interface SchemaItem {
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

const STORAGE_KEY = 'schema_manager_data';

// Schema 列表
const schemas = ref<SchemaItem[]>([]);
// 当前选中的 Schema ID
const selectedSchemaId = ref<string | null>(null);
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

// 当前选中的 Schema
const selectedSchema = computed(() => {
  return schemas.value.find(s => s.id === selectedSchemaId.value) || null;
});

// NodeFlow 组件引用
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// 从本地存储加载数据
function loadFromStorage(): void {
  const savedData = localStorage.getItem(STORAGE_KEY);
  if (savedData) {
    try {
      const data = JSON.parse(savedData);
      schemas.value = data.schemas || [];
      selectedSchemaId.value = data.selectedSchemaId || null;
    } catch (e) {
      console.error('Failed to parse saved data:', e);
    }
  }
}

// 保存到本地存储
function saveToStorage(): void {
  const data = {
    schemas: schemas.value,
    selectedSchemaId: selectedSchemaId.value
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

// 创建新的 Schema
function createSchema(): void {
  const newSchema: SchemaItem = {
    id: Date.now().toString(),
    name: `Schema ${schemas.value.length + 1}`,
    schema: { nodes: [], connections: [] },
    hasUnsavedChanges: false
  };
  schemas.value.push(newSchema);
  selectSchema(newSchema.id);
  saveToStorage();
}

// 选择 Schema
function selectSchema(id: string): void {
  // 如果当前有未保存的更改，显示保存提示
  const current = selectedSchema.value;
  if (current && current.hasUnsavedChanges) {
    pendingSchemaId.value = id;
    showSavePrompt.value = true;
    return;
  }

  // 直接切换
  doSelectSchema(id);
}

// 实际执行选择
function doSelectSchema(id: string): void {
  selectedSchemaId.value = id;
  pendingSchemaId.value = null;
  showSavePrompt.value = false;
  saveToStorage();

  const schema = schemas.value.find(s => s.id === id);
  if (schema) {
    // 切换时先假定没有未保存更改，等待 NodeFlow 加载完毕后通过事件通知我们
    schema.hasUnsavedChanges = false; 
    
    if (nodeFlowRef.value) {
      nodeFlowRef.value.loadSchema(schema.schema);
    }
  }
}
// 保存当前 Schema
function saveCurrentSchema(): void {
  const current = selectedSchema.value;
  if (!current || !nodeFlowRef.value) return;

  // 获取当前 schema
  const currentSchemaData = nodeFlowRef.value.currentSchema;
  if (currentSchemaData) {
    current.schema = currentSchemaData;
    current.hasUnsavedChanges = false;
    saveToStorage();
  }

  // 如果有待切换的 Schema，执行切换
  if (pendingSchemaId.value) {
    doSelectSchema(pendingSchemaId.value);
  } else {
    showSavePrompt.value = false;
  }
}

// 不保存并切换
function discardAndSwitch(): void {
  const current = selectedSchema.value;
  if (current) {
    current.hasUnsavedChanges = false;
  }

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
  if (!confirm('确定要删除这个 Schema 吗？')) return;

  const index = schemas.value.findIndex(s => s.id === id);
  if (index > -1) {
    schemas.value.splice(index, 1);

    // 如果删除的是当前选中的，选中第一个
    if (selectedSchemaId.value === id) {
      if (schemas.value.length > 0) {
        selectSchema(schemas.value[0].id);
      } else {
        selectedSchemaId.value = null;
      }
    }

    saveToStorage();
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

// 确认重命名
function confirmRename(): void {
  if (renamingSchemaId.value && newName.value.trim()) {
    const schema = schemas.value.find(s => s.id === renamingSchemaId.value);
    if (schema) {
      schema.name = newName.value.trim();
      saveToStorage();
    }
  }
  showRenameDialog.value = false;
  renamingSchemaId.value = null;
  newName.value = '';
}

// 取消重命名
function cancelRename(): void {
  showRenameDialog.value = false;
  renamingSchemaId.value = null;
  newName.value = '';
}

// 处理 NodeFlow 的更新事件// 1. 处理数据更新：只负责静默同步数据（备份），绝对不要在这里修改 hasUnsavedChanges
function handleUpdate(schema: any): void {
  const current = selectedSchema.value;
  if (current) {
    // 仅更新数据模型，以便自动保存到 localStorage (防丢失)
    current.schema = schema;
    saveToStorage(); 
    
    // ❌ 以前这里写了 current.hasUnsavedChanges = true; 导致了一加载就变黄
    // ✅ 现在删除了，状态完全交给 handleUnsavedChanges 控制
  }
}

// 2. 新增：专门处理未保存状态（完全听信子组件的判断）
function handleUnsavedChanges(hasChanges: boolean): void {
  const current = selectedSchema.value;
  if (current) {
    // 子组件经过深度对比后，告诉我们是否真的有变化
    current.hasUnsavedChanges = hasChanges;
  }
}

// 3. 处理保存事件：保存后，状态归零
function handleSave(data: any): void {
  const current = selectedSchema.value;
  if (current) {
    current.schema = data;
    current.hasUnsavedChanges = false; // 明确标记为已保存
    saveToStorage();
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadFromStorage();

  // 如果没有 Schema，创建一个默认的
  if (schemas.value.length === 0) {
    createSchema();
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
            <button @click.stop="renameSchema(schema.id)" class="btn-icon">✎</button>
            <button @click.stop="deleteSchema(schema.id)" class="btn-icon">✕</button>
          </div>
        </div>
        <div v-if="schemas.length === 0" class="empty-state">
          暂无 Schema，点击"新建"创建
        </div>
      </div>
    </div>

    <!-- 右侧 NodeFlow 编辑器 -->
    <div class="schema-editor">
      <NodeFlow v-if="selectedSchema" ref="nodeFlowRef" :schema="selectedSchema.schema" :blocks="blocks"
        @update="handleUpdate" @unsavedChanges="handleUnsavedChanges" @save="handleSave" />
      <div v-else class="empty-editor">
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
  </div>
</template>

<style scoped>
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
  height: 32px;
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
  padding: 2px 6px;
  font-size: 12px;
  border-radius: 3px;
  transition: color 0.2s, background 0.2s;
  line-height: 1;
}

.btn-icon:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
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
</style>