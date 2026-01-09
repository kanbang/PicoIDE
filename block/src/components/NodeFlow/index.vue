<template>
  <BaklavaEditor
    :view-model="baklava"
    v-model:schema="schema"
    :blocks="blocks"
  />
</template>

<script setup lang="ts">
// ============================================================================
// 导入依赖
// ============================================================================

import { BaklavaEditor, useBaklava, DEFAULT_TOOLBAR_COMMANDS } from "@baklavajs/renderer-vue";
import "@baklavajs/themes/dist/syrup-dark.css";
import { defineComponent, defineEmits, defineModel, defineProps, h, onMounted, watch } from 'vue';

import { BuildBlock } from './BlockBuilder';
import SaveIcon from '@/components/icons/Save.vue';
import TestNode from './TestNode';

// ============================================================================
// 常量定义
// ============================================================================

const SAVE_COMMAND_ID = "SAVE";

// ============================================================================
// Emits 定义
// ============================================================================

const emit = defineEmits<{
  save: [data: any];
  error: [message: string];
}>();

// ============================================================================
// Baklava 编辑器初始化
// ============================================================================

const baklava = useBaklava();
const editor = baklava.editor;

// 配置编辑器设置
configureEditorSettings();

// 注册自定义命令
registerCustomCommands();

// ============================================================================
// Props 和 Model 定义
// ============================================================================

const schema = defineModel('schema', {
  type: Object,
  default: () => ({ nodes: [], connections: [] })
});

interface Props {
  blocks?: BlockDefinition[];
  initialSchema?: any;
}

const props = defineProps<Props>();

// ============================================================================
// 生命周期钩子
// ============================================================================

onMounted(() => {
  registerNodeTypes();
  loadInitialSchema();
});

// 监听 schema 变化，自动同步到编辑器
watch(() => props.initialSchema, (newSchema) => {
  if (newSchema) {
    try {
      baklava.load(newSchema);
    } catch (error) {
      emit('error', `加载初始数据失败: ${error}`);
    }
  }
}, { immediate: true });

// ============================================================================
// 辅助函数
// ============================================================================

/**
 * 配置编辑器的基本设置
 */
function configureEditorSettings(): void {
  // 侧边栏设置
  baklava.settings.sidebar.enabled = false;
  baklava.settings.sidebar.resizable = true;

  // 功能设置
  baklava.settings.enableMinimap = true;
  baklava.settings.toolbar.enabled = true;
}

/**
 * 注册自定义命令（如保存命令）
 */
function registerCustomCommands(): void {
  // 注册保存命令
  baklava.commandHandler.registerCommand(SAVE_COMMAND_ID, {
    execute: () => {
      try {
        const data = editor.save();
        emit('save', data);
      } catch (error) {
        emit('error', `保存失败: ${error}`);
      }
    },
    canExecute: () => baklava.displayedGraph.nodes.length > 0,
  });

  // 添加保存命令到工具栏
  baklava.settings.toolbar.commands = [
    ...DEFAULT_TOOLBAR_COMMANDS.slice(0, -1),
    {
      command: SAVE_COMMAND_ID,
      title: "保存",
      icon: createSaveIconComponent(),
    },
  ];
}

/**
 * 创建保存图标的组件
 */
function createSaveIconComponent() {
  return defineComponent(() => {
    return () => h('div', {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
        height: '100%'
      }
    }, [
      h(SaveIcon)
    ]);
  });
}

/**
 * 注册所有节点类型
 */
function registerNodeTypes(): void {

  baklava.editor.registerNodeType(TestNode, { category: "Tests" });

  if (!props.blocks) {
    return;
  }

  props.blocks.forEach((blockDef) => {
    try {
      const Block = BuildBlock({
        name: blockDef.name,
        inputs: blockDef.inputs,
        outputs: blockDef.outputs,
        options: blockDef.options
      });

      // 注册节点类型，如果有分类则添加分类
      if (Object.prototype.hasOwnProperty.call(blockDef, 'category')) {
        baklava.editor.registerNodeType(Block, { category: blockDef.category });
      } else {
        baklava.editor.registerNodeType(Block);
      }
    } catch (error) {
      emit('error', `注册节点 ${blockDef.name} 失败: ${error}`);
    }
  });
}

/**
 * 加载初始的编辑器数据
 */
function loadInitialSchema(): void {
  // 优先使用 initialSchema prop
  if (props.initialSchema) {
    try {
      baklava.load(props.initialSchema);
    } catch (error) {
      emit('error', `加载初始数据失败: ${error}`);
    }
    return;
  }

  // 如果没有 initialSchema，尝试使用 schema model 的值
  if (schema.value && (schema.value.nodes?.length > 0 || schema.value.connections?.length > 0)) {
    try {
      baklava.load(schema.value);
    } catch (error) {
      emit('error', `加载 schema 数据失败: ${error}`);
    }
  }
}

// ============================================================================
// 类型定义
// ============================================================================

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

<style scoped>
.baklava-node-palette {
  display: none !important;
}
</style>