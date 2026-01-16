<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';

interface Props {
  direction?: 'horizontal' | 'vertical';
  min?: number;
  max?: number;
  defaultSplit?: number; // 默认分割比例 (0-1)
}

const props = withDefaults(defineProps<Props>(), {
  direction: 'horizontal',
  min: 0.2,
  max: 0.8,
  defaultSplit: 0.5
});

const splitRatio = ref(props.defaultSplit);
const isDragging = ref(false);
const startPos = ref(0);
const startSplit = ref(0);
const containerRef = ref<HTMLElement | null>(null);

// 计算第一个面板的尺寸
const pane1Size = computed(() => {
  return `${splitRatio.value * 100}%`;
});

function startDrag(e: MouseEvent) {
  isDragging.value = true;
  startPos.value = props.direction === 'horizontal' ? e.clientX : e.clientY;
  startSplit.value = splitRatio.value;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.body.style.cursor = props.direction === 'horizontal' ? 'col-resize' : 'row-resize';
  document.body.style.userSelect = 'none';
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return;
  if (!containerRef.value) return;
  
  const rect = containerRef.value.getBoundingClientRect();
  const containerSize = props.direction === 'horizontal' ? rect.width : rect.height;
  const currentPos = props.direction === 'horizontal' ? e.clientX : e.clientY;
  
  // 计算新的分割比例
  let newSplit = startSplit.value + (currentPos - startPos.value) / containerSize;
  
  // 限制在 min 和 max 之间
  newSplit = Math.max(props.min, Math.min(props.max, newSplit));
  
  splitRatio.value = newSplit;
}

function stopDrag() {
  isDragging.value = false;
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
}

onUnmounted(() => {
  if (isDragging.value) {
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', stopDrag);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
});
</script>

<template>
  <div 
    ref="containerRef"
    class="split-container"
    :class="`split-${direction}`"
  >
    <div class="pane pane-1" :style="direction === 'horizontal' ? { width: pane1Size } : { height: pane1Size }">
      <slot name="1"></slot>
    </div>
    
    <div class="splitter-handle" @mousedown="startDrag"></div>
    
    <div class="pane pane-2">
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
}

.split-horizontal {
  flex-direction: row;
}

.split-vertical {
  flex-direction: column;
}

.pane {
  overflow: auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.pane-1 {
  flex-shrink: 0;
  height: 100%;
}

.pane-2 {
  flex: 1;
  height: 100%;
}

.splitter-handle {
  background: #444;
  transition: background 0.2s;
  flex-shrink: 0;
}

.split-horizontal .splitter-handle {
  width: 4px;
  cursor: col-resize;
}

.split-vertical .splitter-handle {
  height: 4px;
  cursor: row-resize;
}

.splitter-handle:hover {
  background: #666;
}

.splitter-handle:active {
  background: #4caf50;
}
</style>