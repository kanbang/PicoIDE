<template>
  <BaklavaEditor :view-model="baklava" :blocks="blocks" />
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import { defineComponent, defineEmits, defineProps, h, onMounted, onUnmounted, nextTick, ref, watch, markRaw } from 'vue';
import SaveIcon from '@/components/icons/Save.vue';
import RunIcon from '@/components/icons/Run.vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from './TestNode';
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

// debounce 更新
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
        emit('run', data);
      } catch (error) {
        emit('error', `运行失败: ${error}`);
      }
    },
    canExecute: () => true,
  });

  baklava.settings.toolbar.commands = [
    ...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1),
    {
      command: RUN_COMMAND_ID,
      title: "运行",
      icon: RunButtonIcon,
    },
    {
      command: SAVE_COMMAND_ID,
      title: "保存",
      icon: SaveButtonIcon,
    },
  ];
}
registerCustomCommands();

// Props
interface Props {
  schema?: any;
  blocks?: BlockDefinition[];
}
const props = defineProps<Props>();

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
  currentSchema
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
</style>