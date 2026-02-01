<!--
 * @Descripttion:
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-17 17:01:06
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-30 17:42:44
-->
<template>
  <div class="nodeflow-container">
    <SplitPane ref="splitPaneRef" direction="horizontal" :min="250" :max="800" :initial-size="350" button-side="right"
      :visible="false">
      <template #1>
        <div class="main-content">
          <!-- 垂直分割：上方是编辑器，下方是 Console -->
          <SplitterVertical ref="consoleSplitterRef" :min="150" :max="0.7" :initial-size="350" button-side="bottom"
            v-model:visible="consolePanelVisible">
            <template #1>
              <div class="editor-wrapper">
                <BaklavaEditor :view-model="baklava" :blocks="blocks" />
              </div>
            </template>

            <template #2>
              <ConsolePanel ref="consolePanelRef" :isVisible="consolePanelVisible" :isConnecting="isSSEConnecting"
                :isConnected="isSSEConnected" />
            </template>
          </SplitterVertical>
        </div>
      </template>

      <template #2>
        <div class="output-panel-wrapper">
          <OutputPanel ref="outputPanelRef" :flowId="props.flowId" @file-opened="handleFileOpened"
            @file-downloaded="handleFileDownloaded" />
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
import StopIcon from '@/components/icons/Stop.vue';
import { BuildBlock } from './BlockBuilder';
import TestNode from './TestNode';
import OutputPanel from './OutputPanel.vue';
import ConsolePanel from './ConsolePanel.vue';
import type { SSEEvent } from './ConsolePanel.vue';
import SplitPane from '@/components/common/Splitter.vue';
import SplitterVertical from '@/components/common/SplitterVertical.vue';
import "@baklavajs/themes/dist/syrup-dark.css";

// --- 常量与 Emits ---
const SAVE_COMMAND_ID = "SAVE";
const RUN_COMMAND_ID = "RUN";

const emit = defineEmits<{
  save: [data: any];
  error: [message: string];
  update: [flow: any];
  unsavedChanges: [hasChanges: boolean];
  run: [data: any];
  stop: [executionId?: string];
  executionEnded: [executionId: string];
}>();

// --- Baklava 核心 ---
const baklava = useBaklava();
const editor = baklava.editor;

// --- 状态管理 ---
const hasUnsavedChanges = ref(false);
const currentFlow = ref<any>(null);
const lastSavedFlow = ref<any>(null);
const isLoading = ref(false);

// --- OutputPanel 与 SplitPane 引用 ---
const outputPanelRef = ref<InstanceType<typeof OutputPanel> | null>(null);
const consolePanelRef = ref<InstanceType<typeof ConsolePanel> | null>(null);
const consoleSplitterRef = ref<any>(null); // 引用垂直分割组件
const splitPaneRef = ref<any>(null); // 引用水平分割组件

// --- 执行状态 ---
const currentExecutionId = ref<string | undefined>(undefined);
const consolePanelVisible = ref(false);
const isRunning = ref(false);

// --- SSE 连接管理 ---
const isSSEConnecting = ref(false);
const isSSEConnected = ref(false);
const eventSourceRef = ref<EventSource | null>(null);

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
    const savedStr = JSON.stringify(lastSavedFlow.value ?? { nodes: [], connections: [] });

    if (newStr !== savedStr) {
      currentFlow.value = newState;
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

const SeparatorIcon = markRaw(defineComponent({
  setup: () => () => h('div', { style: { width: '1px', height: '20px', background: '#555', margin: '0 4px' } })
}));

// 使用动态按钮，根据运行状态显示不同图标和标题
const RunStopButtonIcon = markRaw(defineComponent({
  setup: () => () => h('div', {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '100%',
      height: '100%'
    }
  }, [h(isRunning.value ? StopIcon : RunIcon, { isRunning: isRunning.value })])
}));

// --- 注册命令 ---
function registerCustomCommands(): void {
  baklava.commandHandler.registerCommand(SAVE_COMMAND_ID, {
    execute: () => {
      try {
        const data = editor.save();
        emit('save', data);
        currentFlow.value = data;
        emit('update', data);
        lastSavedFlow.value = deepCopy(data);
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
        if (isRunning.value) {
          // 运行中状态：发出停止事件
          emit('stop', currentExecutionId.value);
        } else {
          // 未运行状态：发出运行事件
          const data = editor.save();
          emit('run', data);
        }
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

    commands.push({
      command: RUN_COMMAND_ID,
      title: isRunning.value ? "停止" : "运行",
      icon: RunStopButtonIcon
    });
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
  flow?: any;
  flowId?: string;
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
  if (currentFlow.value) loadFlow(currentFlow.value);
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

// --- 加载 Flow ---
function loadFlow(newFlow: any) {
  try {
    isLoading.value = true;
    if (!newFlow || Object.keys(newFlow).length === 0) {
      const graph = editor.graph;
      [...graph.nodes].forEach(node => graph.removeNode(node));
      [...graph.connections].forEach(connection => graph.removeConnection(connection));
      currentFlow.value = editor.save();
    } else {
      editor.load(newFlow);
      currentFlow.value = newFlow;
    }
    lastSavedFlow.value = deepCopy(currentFlow.value);
    hasUnsavedChanges.value = false;
    emit('update', currentFlow.value);
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
  // registerFixedNodeTypes();
  registerBlocks(props.blocks || []);

  watch(() => props.blocks, (newBlocks) => {
    if (newBlocks) updateBlocks(newBlocks);
  }, { deep: true });


  loadFlow(props.flow ?? null);
  setupChangeDetection();
});

onUnmounted(() => {
  graphEvents.forEach(prop => editor.graphEvents[prop].unsubscribe(updaterToken));
  nodeEvents.forEach(prop => editor.nodeEvents[prop].unsubscribe(updaterToken));
  disconnectSSE();
});

// --- SSE 连接管理 ---

// 连接 SSE
function connectSSE(executionId: string) {
  if (!executionId) return;

  disconnectSSE(); // 断开旧连接

  isSSEConnecting.value = true;
  isSSEConnected.value = false;

  // 清空之前的事件
  if (consolePanelRef.value) {
    consolePanelRef.value.setEvents([]);
  }

  // 构建SSE URL
  const baseUrl = window.location.origin;
  const url = `${baseUrl}/api/engine/stream/${executionId}`;

  try {
    const eventSource = new EventSource(url);
    eventSourceRef.value = eventSource;

    eventSource.onopen = () => {
      isSSEConnecting.value = false;
      isSSEConnected.value = true;
      console.log('SSE connection established');
    };

    // 监听自定义的 end 事件（服务端发送的结束标识）
    eventSource.addEventListener('end', () => {
      console.log('Received end event, closing SSE connection');
      eventSource.close();
      isSSEConnected.value = false;
      isSSEConnecting.value = false;
      isRunning.value = false;
      // 发出执行结束事件
      if (currentExecutionId.value) {
        emit('executionEnded', currentExecutionId.value);
      }
    });

    eventSource.onmessage = (event) => {
      try {
        console.log('SSE received:', event.data);
        const eventData = JSON.parse(event.data);

        // 处理错误事件
        if (eventData.error) {
          console.error('SSE error event:', eventData.error);
          // 添加到 ConsolePanel
          if (consolePanelRef.value) {
            consolePanelRef.value.addEvent({
              type: 'error',
              source: 'sse',
              message: eventData.error,
              timestamp: new Date().toISOString()
            });
          }
          // 添加到 OutputPanel
          if (outputPanelRef.value) {
            outputPanelRef.value.handleSSEEvent({
              type: 'error',
              message: eventData.error
            });
          }
        } else {
          // 构造 SSEEvent 对象
          const sseEvent: SSEEvent = {
            type: eventData.type || 'info',
            source: eventData.source,
            node_id: eventData.source,
            message: eventData.message,
            timestamp: eventData.ts ? new Date(eventData.ts * 1000).toISOString() : new Date().toISOString(),
            data: eventData.payload !== undefined ? eventData.payload : eventData.data
          };

          // 添加到 ConsolePanel
          if (consolePanelRef.value) {
            consolePanelRef.value.addEvent(sseEvent);
          }

          // 同时分发到 OutputPanel
          if (outputPanelRef.value) {
            outputPanelRef.value.handleSSEEvent(eventData);
          }
        }
      } catch (error) {
        console.error('Failed to parse SSE message:', error, event.data);
        if (consolePanelRef.value) {
          consolePanelRef.value.addEvent({
            type: 'error',
            source: 'sse',
            message: `解析错误: ${error}`,
            timestamp: new Date().toISOString()
          });
        }
      }
    };

    eventSource.onerror = (error) => {
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('SSE connection closed');
        isSSEConnecting.value = false;
        isSSEConnected.value = false;
        return;
      }
      console.error('SSE connection error:', error, 'readyState:', eventSource.readyState);
      isSSEConnecting.value = false;
      isSSEConnected.value = false;
    };

  } catch (error) {
    console.error('Failed to create SSE connection:', error);
    isSSEConnecting.value = false;
    isSSEConnected.value = false;
  }
}

function disconnectSSE() {
  if (eventSourceRef.value) {
    eventSourceRef.value.close();
    eventSourceRef.value = null;
  }
  isSSEConnected.value = false;
  isSSEConnecting.value = false;
}

// --- Console Panel 控制 ---
function showConsolePanel() {
  consolePanelVisible.value = true;
  if (consoleSplitterRef.value?.resetSize) {
    consoleSplitterRef.value.resetSize();
  }
}

function hideConsolePanel() {
  consolePanelVisible.value = false;
}

function toggleConsolePanel() {
  consolePanelVisible.value = !consolePanelVisible.value;
  if (consolePanelVisible.value && consoleSplitterRef.value?.resetSize) {
    consoleSplitterRef.value.resetSize();
  }
}

// --- 设置当前执行的ID（供外部调用） ---
function setCurrentExecutionId(executionId: string | null) {
  currentExecutionId.value = executionId || undefined;
  if (executionId) {
    // 延迟连接，确保后端执行已开始
    consolePanelVisible.value = true;
    isRunning.value = true;
    setTimeout(() => connectSSE(executionId), 500);
  } else {
    disconnectSSE();
  }
}

// --- 设置运行状态 ---
function setRunning(running: boolean) {
  isRunning.value = running;
  if (!running) {
    currentExecutionId.value = undefined;
    disconnectSSE();
  }
}

// --- Expose ---
defineExpose({
  loadFlow,
  updateBlocks,
  hasUnsavedChanges,
  currentFlow,
  outputPanelRef,
  consolePanelRef,
  consoleSplitterRef,
  ssePanelRef: consolePanelRef, // 保持向后兼容
  toggleOutputPanel,
  showOutputPanel,
  hideOutputPanel,
  showSSEPanel: showConsolePanel,
  hideSSEPanel: hideConsolePanel,
  toggleSSEPanel: toggleConsolePanel,
  showConsolePanel,
  hideConsolePanel,
  toggleConsolePanel,
  setCurrentExecutionId,
  setRunning,
  consolePanelVisible,
  ssePanelVisible: consolePanelVisible, // 保持向后兼容
  currentExecutionId,
  isSSEConnected,
  isRunning,
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
  min-height: 0;
}

/* 确保内部容器填满 */
.main-content,
.editor-wrapper,
.output-panel-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  min-height: 0;
}

/* 适配 Baklava 在新容器中的尺寸 */
.nodeflow-container :deep(.baklava-editor) {
  height: 100%;
  width: 100%;
}
</style>
