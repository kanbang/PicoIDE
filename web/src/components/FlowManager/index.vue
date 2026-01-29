<script setup lang="ts">
import { ref, watch, computed, nextTick } from 'vue';
import NodeFlow from '../NodeFlow/index.vue';
import Modal from '../common/Modal.vue';
import SplitPane from '../common/Splitter.vue';
import FlowList, { FlowItem } from './FlowListPanel.vue'; // 引入新组件

// Props
interface Props {
  blocks: any[];
  showRun?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showRun: true
});

// Model 绑定
const flows = defineModel<FlowItem[]>('flows', { default: () => [] });
const selectedFlowId = defineModel<string | null>('selectedFlowId', { default: null });

// Emits
const emit = defineEmits<{
  save: [id: string, data: any];
  create: [flow: FlowItem];
  delete: [id: string];
  rename: [id: string, newName: string];
  duplicate: [id: string, newFlow: FlowItem];
  run: [id: string, data: any];
}>();

// --- 状态控制 (Modal 等) ---
const showSavePrompt = ref(false);
const pendingFlowId = ref<string | null>(null);
const showRenameDialog = ref(false);
const renamingFlowId = ref<string | null>(null);
const newName = ref('');
const showDeleteDialog = ref(false);
const deletingFlowId = ref<string | null>(null);

const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null);

// --- 计算属性 ---
const activeFlowItem = computed(() =>
  flows.value.find(s => s.id === selectedFlowId.value)
);

const hasSelectedFlow = computed(() => !!selectedFlowId.value && !!activeFlowItem.value);

// --- 监听器 ---
// 确保选中 ID 有效
watch(flows, () => {
  if (flows.value.length === 0) {
    selectedFlowId.value = null;
    return;
  }
  if (!selectedFlowId.value || !flows.value.some(s => s.id === selectedFlowId.value)) {
    doSelectFlow(flows.value[0].id);
  }
}, { deep: true, immediate: true });

function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : null;
}

// 加载 Flow 到编辑器
watch(activeFlowItem, async (newItem) => {
  await nextTick();
  if (!newItem) {
    nodeFlowRef.value?.loadFlow(null);
    return;
  }
  nodeFlowRef.value?.loadFlow(deepCopy(newItem.flow));
}, { immediate: true });

// --- 动作处理 (Actions) ---

// 1. 新建
function createFlow() {
  // 如果当前 Flow 有未保存的更改，提示用户
  if (activeFlowItem.value?.hasUnsavedChanges) {
    // 设置特殊的 pendingFlowId 标识这是一个新建操作
    pendingFlowId.value = '__new__';
    showSavePrompt.value = true;
    return;
  }
  
  doCreateFlow();
}

function doCreateFlow() {
  const newFlow: FlowItem = {
    id: '', // 应由后端或父级生成 UUID，这里暂时留空
    name: `Flow ${flows.value.length + 1}`,
    flow: null,
    hasUnsavedChanges: false
  };
  emit('create', newFlow);
  pendingFlowId.value = null;
  showSavePrompt.value = false;
}

// 2. 选择 (包含未保存检查)
function selectFlow(id: string) {
  // 如果点击的是当前已选中的 Flow，直接返回
  if (id === selectedFlowId.value) {
    return;
  }
  
  // 如果当前 Flow 有未保存的更改，提示用户
  if (activeFlowItem.value?.hasUnsavedChanges) {
    pendingFlowId.value = id;
    showSavePrompt.value = true;
    return;
  }
  doSelectFlow(id);
}

function doSelectFlow(id: string) {
  const flowItem = flows.value.find(s => s.id === selectedFlowId.value);
  if (flowItem) {
    flowItem.hasUnsavedChanges = false;
  }
  selectedFlowId.value = id;
  pendingFlowId.value = null;
  showSavePrompt.value = false;
}

// 3. 保存逻辑
function saveCurrentFlow() {
  if (!selectedFlowId.value || !nodeFlowRef.value) return;

  const data = nodeFlowRef.value.currentFlow;
  if (data !== null) {
    const current = flows.value.find(s => s.id === selectedFlowId.value);
    if (current) {
      current.flow = data;
      current.hasUnsavedChanges = false;
    }
    emit('save', selectedFlowId.value, data);
  }

  if (pendingFlowId.value === '__new__') {
    // 新建操作
    doCreateFlow();
  } else if (pendingFlowId.value) {
    // 切换操作
    doSelectFlow(pendingFlowId.value);
  } else {
    showSavePrompt.value = false;
  }
}

function discardAndSwitch() {
  // 清除当前 Flow 的未保存标记
  if (selectedFlowId.value) {
    const current = flows.value.find(s => s.id === selectedFlowId.value);
    if (current) {
      current.hasUnsavedChanges = false;
    }
  }

  if (pendingFlowId.value === '__new__') {
    // 新建操作
    doCreateFlow();
  } else if (pendingFlowId.value) {
    // 切换操作
    doSelectFlow(pendingFlowId.value);
  } else {
    showSavePrompt.value = false;
  }
}

function cancelSwitch() {
  pendingFlowId.value = null;
  showSavePrompt.value = false;
}

// 4. 删除逻辑
function handleDeleteRequest(id: string) {
  deletingFlowId.value = id;
  showDeleteDialog.value = true;
}

function confirmDelete() {
  if (!deletingFlowId.value) return;
  const idToDelete = deletingFlowId.value;
  const isDeletingCurrent = selectedFlowId.value === idToDelete;
  let oldIndex = -1;
  if (isDeletingCurrent) {
    oldIndex = flows.value.findIndex(s => s.id === idToDelete);
  }

  emit('delete', idToDelete);

  nextTick(() => {
    if (flows.value.length === 0) {
      selectedFlowId.value = null;
      return;
    }
    if (isDeletingCurrent && oldIndex !== -1) {
      let newIndex = oldIndex;
      if (oldIndex >= flows.value.length) {
        newIndex = flows.value.length - 1;
      }
      doSelectFlow(flows.value[newIndex].id);
    }
  });

  showDeleteDialog.value = false;
  deletingFlowId.value = null;
}

// 5. 复制
function handleDuplicateRequest(id: string) {
  const original = flows.value.find(s => s.id === id);
  if (!original) return;

  const newFlow: FlowItem = {
    id: '',
    name: `${original.name} (副本)`,
    flow: deepCopy(original.flow),
    hasUnsavedChanges: false
  };
  emit('duplicate', id, newFlow);
}

// 6. 重命名
function handleRenameRequest(id: string) {
  const flow = flows.value.find(s => s.id === id);
  if (!flow) return;

  renamingFlowId.value = id;
  newName.value = flow.name;
  showRenameDialog.value = true;
}

function confirmRename() {
  if (renamingFlowId.value && newName.value.trim()) {
    emit('rename', renamingFlowId.value, newName.value.trim());
  }
  showRenameDialog.value = false;
}

// --- NodeFlow 事件处理 ---
function handleUpdate(_flow: any) {}

function handleUnsavedChanges(hasChanges: boolean) {
  if (!selectedFlowId.value) return;
  const current = flows.value.find(s => s.id === selectedFlowId.value);
  if (current) current.hasUnsavedChanges = hasChanges;
}

function handleSave(data: any) {
  if (!selectedFlowId.value) return;
  const current = flows.value.find(s => s.id === selectedFlowId.value);
  if (current) {
    current.flow = data;
    current.hasUnsavedChanges = false;
    emit('save', selectedFlowId.value, data);
  }
}

function handleRun(data: any) {
  if (!selectedFlowId.value) return;
  emit('run', selectedFlowId.value, data);
}

defineExpose({ nodeFlowRef });
</script>

<template>
  <div class="flow-manager">
    
    <SplitPane 
      direction="horizontal" 
      :min="200" 
      :max="600" 
      :initial-size="300" 
      button-side="left"
    >
      <template #1>
        <FlowList 
          :flows="flows" 
          :selected-id="selectedFlowId"
          @create="createFlow"
          @select="selectFlow"
          @duplicate="handleDuplicateRequest"
          @rename="handleRenameRequest"
          @delete="handleDeleteRequest"
        />
      </template>

      <template #2>
        <div class="flow-editor">
          <NodeFlow v-if="hasSelectedFlow" ref="nodeFlowRef" :blocks="props.blocks" :show-run="props.showRun" :flowId="selectedFlowId"
            @update="handleUpdate" @unsavedChanges="handleUnsavedChanges" @save="handleSave" @run="handleRun" />

          <div v-if="!hasSelectedFlow" class="empty-editor-full">
            <div class="empty-message">
              <div class="empty-title">暂无 Flow</div>
              <div class="empty-subtitle">请在左侧列表中新建或选择一个 Flow 开始编辑</div>
            </div>
          </div>
        </div>
      </template>
    </SplitPane>

    <Modal v-model:visible="showSavePrompt" title="未保存的更改" size="small" @close="cancelSwitch">
      <p>当前 Flow 有未保存的更改，是否保存？</p>
      <template #footer>
        <button @click="saveCurrentFlow" class="btn btn-primary">保存</button>
        <button @click="discardAndSwitch" class="btn">不保存</button>
        <button @click="cancelSwitch" class="btn">取消</button>
      </template>
    </Modal>

    <Modal v-model:visible="showRenameDialog" title="重命名 Flow" size="small" @close="showRenameDialog = false">
      <input v-model="newName" @keyup.enter="confirmRename" class="input" autofocus />
      <template #footer>
        <button @click="confirmRename" class="btn btn-primary">确定</button>
        <button @click="showRenameDialog = false" class="btn">取消</button>
      </template>
    </Modal>

    <Modal v-model:visible="showDeleteDialog" title="删除 Flow" size="small" @close="showDeleteDialog = false">
      <p>确定要删除这个 Flow 吗？此操作无法撤销。</p>
      <template #footer>
        <button @click="confirmDelete" class="btn btn-danger">删除</button>
        <button @click="showDeleteDialog = false" class="btn">取消</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.flow-manager {
  display: flex;
  width: 100vw;
  height: 100%;
  overflow: hidden;
}

/* 编辑器部分样式保持不变 */
.flow-editor {
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
  background: #202b3c;
  color: #888;
  text-align: center;
  z-index: 0;
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