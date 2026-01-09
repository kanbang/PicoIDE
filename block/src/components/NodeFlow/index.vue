<template>
  <BaklavaEditor :view-model="baklava" :blocks="blocks" />
</template>

<script setup lang="ts">
import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import { defineComponent, defineEmits, defineProps, h, onMounted, ref, onUnmounted, nextTick, watch, markRaw } from 'vue';
import SaveIcon from '@/components/icons/Save.vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from './TestNode';
import "@baklavajs/themes/dist/syrup-dark.css";

const SAVE_COMMAND_ID = "SAVE";
const emit = defineEmits<{
  save: [data: any];
  error: [message: string];
  update: [schema: any];
  unsavedChanges: [hasChanges: boolean];
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

  baklava.settings.toolbar.commands = [
    ...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1),
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
}

function registerFixedNodeTypes(): void {
  baklava.editor.registerNodeType(TestNode, { category: "Tests" });
}

// 变化检测
function setupChangeDetection() {
  const updaterToken = Symbol('ChangeDetection');

  for (const prop of ['addNode', 'removeNode', 'addConnection', 'removeConnection']) {
    editor.graphEvents[prop].subscribe(updaterToken, handleChange);
  }

  for (const prop of ['update', 'titleChanged']) {
    editor.nodeEvents[prop].subscribe(updaterToken, handleChange);
  }

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
      attributeFilter: ['class']
    });

    onUnmounted(() => {
      observer.disconnect();
    });
  });
}

// 加载 schema
function loadSchema(newSchema: any) {
  if (!newSchema) 
  {
    return;
  }

  try {
    isLoading.value = true;
    editor.load(newSchema);
    currentSchema.value = newSchema;
    emit('update', newSchema);
    lastSavedSchema.value = deepCopy(newSchema);

    hasUnsavedChanges.value = false;
    emit('unsavedChanges', false);

    if (updateTimeout !== null) {
      clearTimeout(updateTimeout);
      updateTimeout = null;
    }

    nextTick(() => {
      isLoading.value = false;
    });
  } catch (error) {
    isLoading.value = false;
    emit('error', `加载数据失败: ${error}`);
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

  if (props.schema && (props.schema.nodes?.length > 0 || props.schema.connections?.length > 0)) {
    loadSchema(props.schema);
  } else {
    // 空图初始状态
    nextTick(() => {
      const initialState = editor.save();
      lastSavedSchema.value = deepCopy(initialState);
      currentSchema.value = initialState;
    });
  }

  setupChangeDetection();
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