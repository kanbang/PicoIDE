<template>
  <div class="nodeflow-container">
    <SplitPane ref="splitPaneRef" direction="horizontal" :min="250" :max="800" :initial-size="350" button-side="right"
      :visible="false">
      <template #1>
        <div class="editor-wrapper">
          <BaklavaEditor :view-model="baklava" :blocks="blocks" />
        </div>
      </template>

      <template #2>
        <div class="output-panel-wrapper">
          <OutputPanel ref="outputPanelRef" @file-opened="handleFileOpened" @file-downloaded="handleFileDownloaded" />
        </div>
      </template>
    </SplitPane>
  </div>
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import { defineComponent, defineEmits, defineProps, h, onMounted, onUnmounted, nextTick, ref, watch, markRaw, computed } from 'vue';
import SaveIcon from '@/components/icons/Save.vue';
import RunIcon from '@/components/icons/Run.vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from './TestNode';
import OutputPanel from './OutputPanel.vue';
import SplitPane from '@/components/common/Splitter.vue';
import "@baklavajs/themes/dist/syrup-dark.css";

// --- 常量与 Emits ---
const SAVE_COMMAND_ID = "SAVE";
const RUN_COMMAND_ID = "RUN";

const emit = defineEmits<{
  save: [data: any];
  error: [message: string];
  update: [schema: any];
  unsavedChanges: [hasChanges: boolean];
  run: [data: any];
}>();

// --- Baklava 核心 ---
const baklava = useBaklava();
const editor = baklava.editor;

// --- 状态管理 ---
const hasUnsavedChanges = ref(false);
const currentSchema = ref<any>(null);
const lastSavedSchema = ref<any>(null);
const isLoading = ref(false);

// --- OutputPanel 与 SplitPane 引用 ---
const outputPanelRef = ref<InstanceType<typeof OutputPanel> | null>(null);
const splitPaneRef = ref<any>(null); // 引用 SplitPane 组件实例

// --- 外部控制方法 (保持 API 兼容) ---

// 如果父组件调用这些方法，我们尝试调用 SplitPane 内部的方法
// 注意：这要求 SplitPane.vue 中使用了 defineExpose({ togglePane, ... })
function toggleOutputPanel() {
  if (splitPaneRef.value?.togglePane) {
    splitPaneRef.value.togglePane();
  }
}

function showOutputPanel() {
  // 如果 SplitPane 有暴露显示方法或变量，在这里操作
  // 简单实现：如果没有暴露强制显示的方法，通常 toggle 已经够用
  // 或者在此处访问 SplitPane 的 isSidebarVisible 变量
  if (splitPaneRef.value && !splitPaneRef.value.isSidebarVisible) {
    splitPaneRef.value.togglePane();
  }
}

function hideOutputPanel() {
  if (splitPaneRef.value && splitPaneRef.value.isSidebarVisible) {
    splitPaneRef.value.togglePane();
  }
}

// --- 文件处理回调 ---
function handleFileOpened(file: any) {
  console.log('文件已打开:', file.filename);
}

function handleFileDownloaded(file: any) {
  console.log('文件已下载:', file.filename);
}

// --- 自动保存/变化检测逻辑 ---
const DEBOUNCE_TIME = 500;
let updateTimeout: number | null = null;

function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : {};
}

function scheduleUpdate() {
  if (updateTimeout !== null) {
    clearTimeout(updateTimeout);
  }
  updateTimeout = setTimeout(() => {
    const newState = editor.save();
    const newStr = JSON.stringify(newState);
    const savedStr = JSON.stringify(lastSavedSchema.value ?? { nodes: [], connections: [] });

    if (newStr !== savedStr) {
      currentSchema.value = newState;
      emit('update', newState);

      if (!hasUnsavedChanges.value) {
        hasUnsavedChanges.value = true;
        emit('unsavedChanges', true);
      }
    } else {
      if (hasUnsavedChanges.value) {
        hasUnsavedChanges.value = false;
        emit('unsavedChanges', false);
      }
    }
    updateTimeout = null;
  }, DEBOUNCE_TIME);
}

function handleChange() {
  if (isLoading.value) return;
  scheduleUpdate();
}

// --- 编辑器配置 ---
function configureEditorSettings(): void {
  baklava.settings.sidebar.enabled = false;
  baklava.settings.sidebar.resizable = true;
  baklava.settings.enableMinimap = true;
  baklava.settings.toolbar.enabled = true;
}
configureEditorSettings();

// --- 图标组件 (MarkRaw) ---
const SaveButtonIcon = markRaw(defineComponent({
  setup: () => () => h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' } }, [h(SaveIcon)])
}));

const RunButtonIcon = markRaw(defineComponent({
  setup: () => () => h('div', { style: { display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' } }, [h(RunIcon)])
}));

const SeparatorIcon = markRaw(defineComponent({
  setup: () => () => h('div', { style: { width: '1px', height: '20px', background: '#555', margin: '0 4px' } })
}));

// --- 注册命令 ---
function registerCustomCommands(): void {
  baklava.commandHandler.registerCommand(SAVE_COMMAND_ID, {
    execute: () => {
      try {
        const data = editor.save();
        emit('save', data);
        currentSchema.value = data;
        emit('update', data);
        lastSavedSchema.value = deepCopy(data);
        hasUnsavedChanges.value = false;
        emit('unsavedChanges', false);
        if (updateTimeout !== null) {
          clearTimeout(updateTimeout);
          updateTimeout = null;
        }
      } catch (error) {
        emit('error', `保存失败: ${error}`);
      }
    },
    canExecute: () => hasUnsavedChanges.value,
  });

  baklava.commandHandler.registerCommand(RUN_COMMAND_ID, {
    execute: () => {
      try {
        const data = editor.save();
        emit('run', data);
      } catch (error) {
        console.error('运行失败:', error);
        emit('error', `运行失败: ${error}`);
      }
    },
    canExecute: () => editor.graph.nodes.length > 0,
  });

  const commands = [...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1)];
  commands.push({ command: SAVE_COMMAND_ID, title: "保存", icon: SaveButtonIcon });

  if (props.showRun) {
    commands.push({ command: 'SEPARATOR', title: "", icon: SeparatorIcon });
    commands.push({ command: RUN_COMMAND_ID, title: "运行", icon: RunButtonIcon });
  }

  baklava.settings.toolbar.commands = commands;
}

// --- Props & Blocks Logic ---
interface BlockDefinition {
  name: string;
  inputs?: Array<{ name: string }>;
  outputs?: Array<{ name: string }>;
  options?: Array<{ name: string; type: string; value?: any; items?: any[]; min?: number; max?: number; title?: string; }>;
  category?: string;
}

interface Props {
  schema?: any;
  blocks?: BlockDefinition[];
  showRun?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  showRun: true
});

const registeredCustomNodeTypes = new Set<any>();

function registerBlocks(blocks: BlockDefinition[] = []) {
  registeredCustomNodeTypes.forEach(nodeClass => editor.unregisterNodeType(nodeClass));
  registeredCustomNodeTypes.clear();

  blocks.forEach((blockDef) => {
    try {
      const Block = BuildBlock({
        name: blockDef.name,
        inputs: blockDef.inputs,
        outputs: blockDef.outputs,
        options: blockDef.options
      });
      const category = 'category' in blockDef ? blockDef.category : undefined;
      editor.registerNodeType(Block, { category });
      registeredCustomNodeTypes.add(Block);
    } catch (error) {
      emit('error', `注册节点 ${blockDef.name} 失败: ${error}`);
    }
  });
}

function updateBlocks(newBlocks: BlockDefinition[]) {
  registerBlocks(newBlocks);
  if (currentSchema.value) loadSchema(currentSchema.value);
}

function registerFixedNodeTypes(): void {
  baklava.editor.registerNodeType(TestNode, { category: "Tests" });
}

// --- 变化检测监听 ---
const graphEvents = ['addNode', 'removeNode', 'addConnection', 'removeConnection'];
const nodeEvents = ['update', 'titleChanged'];
const updaterToken = Symbol('ChangeDetection');

function setupChangeDetection() {
  graphEvents.forEach(prop => editor.graphEvents[prop].subscribe(updaterToken, handleChange));
  nodeEvents.forEach(prop => editor.nodeEvents[prop].subscribe(updaterToken, handleChange));
  setupNodeDragObserver();
}

function setupNodeDragObserver() {
  nextTick(() => {
    const editorElement = document.querySelector('.baklava-editor');
    if (!editorElement) return;
    const nodeContainer = editorElement.querySelector('.node-container');
    if (!nodeContainer) return;
    const observer = new MutationObserver(() => handleChange());
    observer.observe(nodeContainer, { attributes: true, subtree: true, attributeFilter: ['style'] });
    onUnmounted(() => observer.disconnect());
  });
}

// --- 加载 Schema ---
function loadSchema(newSchema: any) {
  try {
    isLoading.value = true;
    if (!newSchema || Object.keys(newSchema).length === 0) {
      const graph = editor.graph;
      [...graph.nodes].forEach(node => graph.removeNode(node));
      [...graph.connections].forEach(connection => graph.removeConnection(connection));
      currentSchema.value = editor.save();
    } else {
      editor.load(newSchema);
      currentSchema.value = newSchema;
    }
    lastSavedSchema.value = deepCopy(currentSchema.value);
    hasUnsavedChanges.value = false;
    emit('update', currentSchema.value);
    emit('unsavedChanges', false);
    if (updateTimeout !== null) {
      clearTimeout(updateTimeout);
      updateTimeout = null;
    }
    nextTick(() => isLoading.value = false);
  } catch (error) {
    isLoading.value = false;
    hasUnsavedChanges.value = false;
    emit('unsavedChanges', false);
    emit('error', `操作失败: ${error}`);
  }
}

// --- 生命周期 ---
onMounted(() => {
  registerCustomCommands();
  registerFixedNodeTypes();
  registerBlocks(props.blocks || []);

  watch(() => props.blocks, (newBlocks) => {
    if (newBlocks) updateBlocks(newBlocks);
  }, { deep: true });

  loadSchema(props.schema ?? null);
  setupChangeDetection();
});

onUnmounted(() => {
  graphEvents.forEach(prop => editor.graphEvents[prop].unsubscribe(updaterToken));
  nodeEvents.forEach(prop => editor.nodeEvents[prop].unsubscribe(updaterToken));
});

// --- Expose ---
defineExpose({
  loadSchema,
  updateBlocks,
  hasUnsavedChanges,
  currentSchema,
  outputPanelRef,
  toggleOutputPanel,
  showOutputPanel,
  hideOutputPanel,
});
</script>

<style>
/* Baklava 样式覆盖 */
.baklava-node-palette {
  display: none !important;
}

.nodeflow-container {
  display: flex;
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
}

/* 确保内部容器填满 */
.editor-wrapper,
.output-panel-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}

/* 适配 Baklava 在新容器中的尺寸 */
.nodeflow-container :deep(.baklava-editor) {
  height: 100%;
  width: 100%;
}
</style>