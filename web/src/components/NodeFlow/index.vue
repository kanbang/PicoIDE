<template>
  <div class="nodeflow-container">
    <Splitter direction="horizontal" :min="0.3" :max="0.8" :default-split="0.7">
      <template #1>
        <div class="editor-pane">
          <button @click="toggleOutputPanel" class="btn-toggle-overlay" :title="outputPanelVisible ? '隐藏输出面板' : '显示输出面板'">
            <svg v-if="outputPanelVisible" width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M6 1L2 5L6 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none">
              <path d="M4 1L8 5L4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <BaklavaEditor :view-model="baklava" :blocks="blocks" />
        </div>
      </template>
      <template #2>
        <OutputPanel
          ref="outputPanelRef"
          @file-opened="handleFileOpened"
          @file-downloaded="handleFileDownloaded"
        />
      </template>
    </Splitter>
  </div>
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import { defineComponent, defineEmits, defineProps, h, onMounted, onUnmounted, nextTick, ref, watch, markRaw } from 'vue';
import SaveIcon from '@/components/icons/Save.vue';
import RunIcon from '@/components/icons/Run.vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from './TestNode';
import OutputPanel from '@/components/OutputPanel.vue';
import Splitter from '@/components/common/Splitter.vue';
import "@baklavajs/themes/dist/syrup-dark.css";

const SAVE_COMMAND_ID = "SAVE";
const RUN_COMMAND_ID = "RUN";

const emit = defineEmits<{
  save: [data: any];
  error: [message: string];
  update: [schema: any];
  unsavedChanges: [hasChanges: boolean];
  run: [data: any];
}>();

const baklava = useBaklava();
const editor = baklava.editor;

// 未保存变化标记（控制保存按钮可用性）
const hasUnsavedChanges = ref(false);
// 当前 schema（仅在真实变化时更新并 emit）
const currentSchema = ref<any>(null);
// 上次保存/加载的 schema（用于精确比较）
const lastSavedSchema = ref<any>(null);
// 加载中
const isLoading = ref(false);

// OutputPanel引用
const outputPanelRef = ref<InstanceType<typeof OutputPanel> | null>(null);
const outputPanelVisible = ref(false);

// OutputPanel显示/隐藏
function toggleOutputPanel() {
  outputPanelVisible.value = !outputPanelVisible.value;
  outputPanelRef.value?.toggle();
}

function showOutputPanel() {
  outputPanelVisible.value = true;
  outputPanelRef.value?.show();
}

function hideOutputPanel() {
  outputPanelVisible.value = false;
  outputPanelRef.value?.hide();
}

// debounce 更新
const DEBOUNCE_TIME = 500;
let updateTimeout: number | null = null;

function deepCopy(obj: any): any {
  return obj ? JSON.parse(JSON.stringify(obj)) : {};
}

// 处理文件打开
function handleFileOpened(file: any) {
  console.log('文件已打开:', file.filename);
}

// 处理文件下载
function handleFileDownloaded(file: any) {
  console.log('文件已下载:', file.filename);
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
      // 真实发生变化
      currentSchema.value = newState;
      emit('update', newState);

      if (!hasUnsavedChanges.value) {
        hasUnsavedChanges.value = true;
        emit('unsavedChanges', true);
      }
    } else {
      // 没有真实变化（回到了保存状态）
      if (hasUnsavedChanges.value) {
        hasUnsavedChanges.value = false;
        emit('unsavedChanges', false);
      }
    }

    updateTimeout = null;
  }, DEBOUNCE_TIME);
}

// 统一变化处理：仅调度检查，不提前标记
function handleChange() {
  if (isLoading.value) return;
  scheduleUpdate();
}

// 配置编辑器
function configureEditorSettings(): void {
  baklava.settings.sidebar.enabled = false;
  baklava.settings.sidebar.resizable = true;
  baklava.settings.enableMinimap = true;
  baklava.settings.toolbar.enabled = true;
}
configureEditorSettings();

// 把组件定义提前、静态化，并用 markRaw 包裹（只创建一次）
const SaveButtonIcon = markRaw(
  defineComponent({
    name: 'SaveButtonIcon',  // 可选：加个名字方便调试
    setup() {
      return () => h('div', {
        style: {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100%'
        }
      }, [h(SaveIcon)]);
    }
  })
);

const RunButtonIcon = markRaw(
  defineComponent({
    name: 'RunButtonIcon',
    setup() {
      return () => h('div', {
        style: {
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '100%',
          height: '100%'
        }
      }, [h(RunIcon)]);
    }
  })
);

const SeparatorIcon = markRaw(
  defineComponent({
    name: 'SeparatorIcon',
    setup() {
      return () => h('div', {
        style: {
          width: '1px',
          height: '20px',
          background: '#555',
          margin: '0 4px'
        }
      });
    }
  })
);


// 注册保存命令
function registerCustomCommands(): void {
  baklava.commandHandler.registerCommand(SAVE_COMMAND_ID, {
    execute: () => {
      try {
        const data = editor.save();
        emit('save', data);

        // 保存后立即同步（视为真实状态）
        currentSchema.value = data;
        emit('update', data);
        lastSavedSchema.value = deepCopy(data);

        hasUnsavedChanges.value = false;
        emit('unsavedChanges', false);

        // 清除 pending debounce
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
        // 只 emit run 事件，由父组件负责调用 API
        emit('run', data);
      } catch (error) {
        console.error('运行失败:', error);
        emit('error', `运行失败: ${error}`);
      }
    },
    canExecute: () => editor.graph.nodes.length > 0,
  });


  const commands = [
    ...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1),
  ];

  commands.push({
    command: SAVE_COMMAND_ID,
    title: "保存",
    icon: SaveButtonIcon,
  });


  if (props.showRun) {
    commands.push({
      command: 'SEPARATOR',
      title: "",
      icon: SeparatorIcon,
    });
    commands.push({
      command: RUN_COMMAND_ID,
      title: "运行",
      icon: RunButtonIcon,
    });
  }

  baklava.settings.toolbar.commands = commands;
}

// Props
interface Props {
  schema?: any;
  blocks?: BlockDefinition[];
  showRun?: boolean;
}
const props = withDefaults(defineProps<Props>(), {
  showRun: true
});

// 跟踪自定义节点类型（用于清空）
const registeredCustomNodeTypes = new Set<any>();

// 清空并重新注册所有块
function registerBlocks(blocks: BlockDefinition[] = []) {
  registeredCustomNodeTypes.forEach(nodeClass => {
    editor.unregisterNodeType(nodeClass);
  });
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
  // 刷新当前 schema 以匹配新块
  if (currentSchema.value) {
    loadSchema(currentSchema.value);
  }
}

function registerFixedNodeTypes(): void {
  baklava.editor.registerNodeType(TestNode, { category: "Tests" });
}

// 变化检测

const graphEvents = ['addNode', 'removeNode', 'addConnection', 'removeConnection'];
const nodeEvents = ['update', 'titleChanged'];

const updaterToken = Symbol('ChangeDetection');
function setupChangeDetection() {
  graphEvents.forEach(prop => {
    editor.graphEvents[prop].subscribe(updaterToken, handleChange);
  });

  nodeEvents.forEach(prop => {
    editor.nodeEvents[prop].subscribe(updaterToken, handleChange);
  });

  // 如果 Baklava 支持 positionChanged 等事件，可添加
  // editor.nodeEvents.positionChanged.subscribe(updaterToken, handleChange);

  setupNodeDragObserver();
}

function setupNodeDragObserver() {
  nextTick(() => {
    const editorElement = document.querySelector('.baklava-editor');
    if (!editorElement) return;

    const nodeContainer = editorElement.querySelector('.node-container');
    if (!nodeContainer) return;

    const observer = new MutationObserver(() => {
      handleChange();
    });

    observer.observe(nodeContainer, {
      attributes: true,
      subtree: true,
      attributeFilter: ['style']  // 优化为 style 属性，针对位置变化
    });

    onUnmounted(() => {
      observer.disconnect();
    });
  });
}

// 加载 schema
function loadSchema(newSchema: any) {
  try {
    isLoading.value = true;

    if (!newSchema || Object.keys(newSchema).length === 0) {
      // 清空编辑器
      const graph = editor.graph;

      // 移除所有节点和连接
      [...graph.nodes].forEach(node => graph.removeNode(node));
      [...graph.connections].forEach(connection => graph.removeConnection(connection));

      // 重置当前 schema
      currentSchema.value = editor.save();
    } else {
      // 加载新 Schema
      editor.load(newSchema);
      currentSchema.value = newSchema;
    }

    lastSavedSchema.value = deepCopy(currentSchema.value);
    hasUnsavedChanges.value = false;
    emit('update', currentSchema.value);
    emit('unsavedChanges', false);

    // 清除更新定时器
    if (updateTimeout !== null) {
      clearTimeout(updateTimeout);
      updateTimeout = null;
    }

    nextTick(() => {
      isLoading.value = false;
    });
  } catch (error) {
    isLoading.value = false;
    hasUnsavedChanges.value = false;
    emit('unsavedChanges', false);
    emit('error', `操作失败: ${error}`);
  }
}

// 生命周期
onMounted(() => {
  registerCustomCommands();
  registerFixedNodeTypes();
  registerBlocks(props.blocks || []);

  watch(() => props.blocks, (newBlocks) => {
    if (newBlocks) {
      updateBlocks(newBlocks);
    }
  }, { deep: true });

  // 统一加载 props.schema，如果为空也处理
  loadSchema(props.schema ?? null);

  setupChangeDetection();
});

onUnmounted(() => {
  graphEvents.forEach(prop => {
    editor.graphEvents[prop].unsubscribe(updaterToken);
  });

  nodeEvents.forEach(prop => {
    editor.nodeEvents[prop].unsubscribe(updaterToken);
  });
});

defineExpose({
  loadSchema,
  updateBlocks,
  hasUnsavedChanges,
  currentSchema,
  outputPanelRef,
  outputPanelVisible,
  toggleOutputPanel,
  showOutputPanel,
  hideOutputPanel,
});

interface BlockDefinition {
  name: string;
  inputs?: Array<{ name: string }>;
  outputs?: Array<{ name: string }>;
  options?: Array<{
    name: string;
    type: string;
    value?: any;
    items?: any[];
    min?: number;
    max?: number;
    title?: string;
  }>;
  category?: string;
}
</script>

<style>
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

.nodeflow-container :deep(.pane) {
  height: 100%;
  overflow: hidden;
}

.nodeflow-container :deep(.baklava-editor) {
  height: 100%;
  width: 100%;
}

.editor-pane {
  position: relative;
  height: 100%;
  width: 100%;
  overflow: hidden;
}

.btn-toggle-overlay {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 60px;
  background: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: 6px 0 0 6px;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: all 0.25s ease;
  box-shadow: -2px 0 8px rgba(0, 0, 0, 0.3);
  padding: 0;
}

.btn-toggle-overlay:hover {
  width: 20px;
  background: rgba(50, 50, 50, 0.9);
  color: #fff;
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.5);
}

.btn-toggle-overlay svg {
  width: 12px;
  height: 12px;
  stroke-width: 2;
}
</style>