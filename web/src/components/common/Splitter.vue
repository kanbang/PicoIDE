<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';

interface Props {
  direction?: 'horizontal' | 'vertical'; // 暂时只实现水平
  min?: number;
  max?: number;
  initialSize?: number | string;
  buttonSide?: 'left' | 'right'; // 决定哪一边是侧边栏
}

const props = withDefaults(defineProps<Props>(), {
  direction: 'horizontal',
  min: 100,
  max: 0.9,
  initialSize: 300,
  buttonSide: 'left'
});

const containerRef = ref<HTMLElement | null>(null);
const currentSize = ref(300); // 当前侧边栏的宽度（无论是左还是右）
const isDragging = ref(false);
const isSidebarVisible = ref(true);

// 判断是否为右侧侧边栏模式
const isRightSidebar = computed(() => props.buttonSide === 'right');

const getLimit = (val: number, total: number) => {
  return val < 1 ? total * val : val;
};

function startDrag(e: MouseEvent) {
  e.preventDefault();
  isDragging.value = true;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value || !containerRef.value) return;

  const containerRect = containerRef.value.getBoundingClientRect();
  const totalWidth = containerRect.width;
  const mouseX = e.clientX - containerRect.left;

  let newSize;

  if (isRightSidebar.value) {
    // 右侧模式：鼠标越往左，宽度越大
    // 宽度 = 容器总宽 - 鼠标位置
    newSize = totalWidth - mouseX;
  } else {
    // 左侧模式：鼠标越往右，宽度越大
    newSize = mouseX;
  }

  const minPixel = getLimit(props.min, totalWidth);
  const maxPixel = getLimit(props.max, totalWidth);

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

function togglePane() {
  isSidebarVisible.value = !isSidebarVisible.value;
}

defineExpose({
  togglePane,
  isSidebarVisible
});

// 左侧面板样式
const pane1Style = computed(() => {
  if (isRightSidebar.value) {
    // 如果是右侧栏模式，左侧就是自适应内容区
    return { flex: 1, minWidth: 0 };
  } else {
    // 如果是左侧栏模式，左侧受宽度控制
    if (!isSidebarVisible.value) return { width: '0px', minWidth: '0', overflow: 'hidden' };
    return { width: `${currentSize.value}px` };
  }
});

// 右侧面板样式
const pane2Style = computed(() => {
  if (isRightSidebar.value) {
    // 如果是右侧栏模式，右侧受宽度控制
    if (!isSidebarVisible.value) return { width: '0px', minWidth: '0', overflow: 'hidden' };
    return { width: `${currentSize.value}px` };
  } else {
    // 如果是左侧栏模式，右侧是自适应内容区
    return { flex: 1, minWidth: 0 };
  }
});

// 箭头的方向逻辑
const arrowDirection = computed(() => {
  if (isSidebarVisible.value) {
    // 展开状态：左侧栏显示向左箭头，右侧栏显示向右箭头
    return isRightSidebar.value ? 'right' : 'left';
  } else {
    // 收起状态：反之
    return isRightSidebar.value ? 'left' : 'right';
  }
});

onMounted(() => {
  if (typeof props.initialSize === 'number') {
    currentSize.value = props.initialSize;
  } else if (containerRef.value && typeof props.initialSize === 'string' && props.initialSize.endsWith('%')) {
    const percent = parseFloat(props.initialSize) / 100;
    currentSize.value = containerRef.value.clientWidth * percent;
  }
});
</script>

<template>
  <div class="split-container" ref="containerRef" :class="[direction, { 'is-resizing': isDragging }]">

    <div class="split-pane pane-1" :style="pane1Style">
      <slot name="1"></slot>
    </div>

    <div class="split-trigger" :class="{ dragging: isDragging }" v-show="isSidebarVisible" @mousedown="startDrag">
      <button @click.stop="togglePane" class="btn-toggle-overlay" :class="buttonSide"
        :title="isSidebarVisible ? '隐藏侧边栏' : '显示侧边栏'">
        <svg v-if="arrowDirection === 'left'" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M6 1L2 5L6 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
        <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M4 1L8 5L4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
      </button>
    </div>

    <div v-show="!isSidebarVisible" class="split-trigger-placeholder">
      <button @click.stop="togglePane" class="btn-toggle-overlay" :class="buttonSide" title="显示侧边栏">
        <svg v-if="arrowDirection === 'left'" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M6 1L2 5L6 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
        <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M4 1L8 5L4 9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
            stroke-linejoin="round" />
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
  width: 100%;
  height: 100%;
  overflow: hidden;
  user-select: none;
}

.split-container.horizontal {
  flex-direction: row;
}

.split-pane {
  overflow: hidden;
  transition: width 0.3s ease;
  will-change: width;
}

/* 拖拽时禁用过渡 */
.split-container.is-resizing .split-pane {
  transition: none !important;
  pointer-events: none;
}

/* Trigger 样式 */
.split-trigger {
  width: 4px;
  background: #444;
  cursor: col-resize;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
  transition: background 0.2s;
}

.split-trigger:hover,
.split-trigger.dragging {
  background: #4caf50;
}

.split-trigger::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: -4px;
  right: -4px;
  z-index: 1;
  cursor: col-resize;
}

.split-trigger-placeholder {
  width: 0;
  position: relative;
  z-index: 10;
}

/* 按钮基础样式 */
.btn-toggle-overlay {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 60px;
  background: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(8px);
  border: none;
  border-radius: 0 6px 6px 0;
  color: #aaa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  transition: all 0.2s ease;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.2);
  padding: 0;
  pointer-events: auto;
}

.btn-toggle-overlay:hover {
  width: 20px;
  background: rgba(50, 50, 50, 0.9);
  color: #fff;
  box-shadow: 4px 0 12px rgba(0, 0, 0, 0.5);
}

/* --- 左侧侧边栏模式 (Button Side Left) --- */
/* 按钮贴在分割条右侧，控制左侧面板 */
.btn-toggle-overlay.left {
  left: 100%;
  /* 贴在分割条右边 */
  border-radius: 0 6px 6px 0;
  border-left: none;
  box-shadow: 4px 0 8px rgba(0, 0, 0, 0.2);
}

/* --- 右侧侧边栏模式 (Button Side Right) --- */
/* 按钮贴在分割条左侧，控制右侧面板 */
.btn-toggle-overlay.right {
  right: 100%;
  /* 贴在分割条左边 */
  border-radius: 6px 0 0 6px;
  border-right: none;
  box-shadow: -4px 0 8px rgba(0, 0, 0, 0.2);
  /* 阴影向左 */
}

/* SVG 图标通用样式 */
.btn-toggle-overlay svg {
  width: 12px;
  height: 12px;
  stroke-width: 2;
}
</style>