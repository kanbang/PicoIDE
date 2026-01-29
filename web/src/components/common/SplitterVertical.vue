<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';

interface Props {
  min?: number;
  max?: number;
  initialSize?: number | string;
  buttonSide?: 'top' | 'bottom';
}

const props = withDefaults(defineProps<Props>(), {
  min: 100,
  max: 0.9,
  initialSize: 250,
  buttonSide: 'bottom'
});

// 使用 defineModel 处理双向绑定
const isSidebarVisible = defineModel('visible', {
  default: true,
  local: true
});

const containerRef = ref<HTMLElement | null>(null);
const currentSize = ref(250);
const isDragging = ref(false);

const isBottomSidebar = computed(() => props.buttonSide === 'bottom');

// 计算初始像素值，用于双击恢复
const getInitialPixelSize = () => {
  if (!containerRef.value) return 250;
  if (typeof props.initialSize === 'number') {
    return props.initialSize;
  } else if (typeof props.initialSize === 'string' && props.initialSize.endsWith('%')) {
    const percent = parseFloat(props.initialSize) / 100;
    return containerRef.value.clientHeight * percent;
  }
  return 250;
};

// 限制范围逻辑
const getLimit = (val: number, total: number) => {
  return val < 1 ? total * val : val;
};

// --- 拖拽逻辑 ---
function startDrag(e: MouseEvent) {
  e.preventDefault();
  isDragging.value = true;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.body.style.cursor = 'row-resize';
  document.body.style.userSelect = 'none';
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value || !containerRef.value) return;

  const containerRect = containerRef.value.getBoundingClientRect();
  const totalHeight = containerRect.height;
  const mouseY = e.clientY - containerRect.top;

  let newSize = isBottomSidebar.value ? totalHeight - mouseY : mouseY;

  const minPixel = getLimit(props.min, totalHeight);
  const maxPixel = getLimit(props.max, totalHeight);

  if (newSize < minPixel) newSize = minPixel;
  if (newSize > maxPixel) newSize = maxPixel;

  currentSize.value = newSize;
}

function stopDrag() {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
}

// --- 功能方法 ---
function togglePane() {
  isSidebarVisible.value = !isSidebarVisible.value;
}

function resetSize() {
  currentSize.value = getInitialPixelSize();
}

defineExpose({ togglePane, resetSize, isSidebarVisible });

// --- 样式计算 ---
const pane1Style = computed(() => {
  if (isBottomSidebar.value) return { flex: 1, minHeight: 0, overflow: 'hidden' };
  if (!isSidebarVisible.value) return { height: '0px', minHeight: '0', overflow: 'hidden' };
  return { height: `${currentSize.value}px`, minHeight: 0, overflow: 'hidden' };
});

const pane2Style = computed(() => {
  if (!isBottomSidebar.value) return { flex: 1, minHeight: 0, overflow: 'hidden' };
  if (!isSidebarVisible.value) return { height: '0px', minHeight: '0', overflow: 'hidden' };
  return { height: `${currentSize.value}px`, minHeight: 0, overflow: 'hidden' };
});

const arrowDirection = computed(() => {
  if (isSidebarVisible.value) return isBottomSidebar.value ? 'down' : 'up';
  return isBottomSidebar.value ? 'up' : 'down';
});

onMounted(() => {
  currentSize.value = getInitialPixelSize();
});
</script>

<template>
  <div class="split-container" ref="containerRef" :class="{ 'is-resizing': isDragging }">

    <div class="split-pane pane-1" :style="pane1Style">
      <slot name="1"></slot>
    </div>

    <div class="split-trigger" :class="{ dragging: isDragging }" v-show="isSidebarVisible" @mousedown="startDrag"
      @dblclick="resetSize" title="拖拽调整大小，双击恢复默认">
      <button @click.stop="togglePane" class="btn-toggle-overlay" :class="buttonSide" @mousedown.stop @dblclick.stop>
        <svg v-if="arrowDirection === 'up'" viewBox="0 0 10 10">
          <path d="M1 6L5 2L9 6" />
        </svg>
        <svg v-else viewBox="0 0 10 10">
          <path d="M1 4L5 8L9 4" />
        </svg>
      </button>
    </div>

    <div v-show="!isSidebarVisible" class="split-trigger-placeholder">
      <button @click.stop="togglePane" class="btn-toggle-overlay" :class="buttonSide" @mousedown.stop @dblclick.stop>
        <svg v-if="arrowDirection === 'up'" viewBox="0 0 10 10">
          <path d="M1 6L5 2L9 6" />
        </svg>
        <svg v-else viewBox="0 0 10 10">
          <path d="M1 4L5 8L9 4" />
        </svg>
      </button>
    </div>

    <div class="split-pane pane-2" :style="pane2Style">
      <slot name="2"></slot>
    </div>
  </div>
</template>

<style scoped>
.split-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: #1e1e1e;
}

.split-pane {
  overflow: hidden;
  /* 双击恢复或折叠时使用动画 */
  transition: height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 拖拽时立即响应，禁用动画 */
.is-resizing .split-pane {
  transition: none !important;
}

.split-trigger {
  height: 4px;
  background: #333;
  cursor: row-resize;
  position: relative;
  z-index: 10;
  transition: background 0.2s;
  flex-shrink: 0;
}

.split-trigger:hover,
.split-trigger.dragging {
  background: #4caf50;
}

/* 增加点击区域 */
.split-trigger::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -4px;
  bottom: -4px;
}

.split-trigger-placeholder {
  height: 0;
  position: relative;
  z-index: 10;
  flex-shrink: 0;
}

.btn-toggle-overlay {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  width: 48px;
  height: 16px;
  background: #2d2d2d;
  border: none;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-toggle-overlay:hover {
  background: #4caf50;
  color: white;
}

.btn-toggle-overlay.top {
  top: 100%;
  border-radius: 0 0 4px 4px;
}

.btn-toggle-overlay.bottom {
  bottom: 100%;
  border-radius: 4px 4px 0 0;
}

svg {
  width: 10px;
  height: 10px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
