<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';

interface Props {
  direction?: 'horizontal' | 'vertical';
  minSize?: number;
  maxSize?: number;
}

const props = withDefaults(defineProps<Props>(), {
  direction: 'horizontal',
  minSize: 200,
  maxSize: 600
});

const emit = defineEmits<{
  drag: [delta: number];
  dragEnd: [size: number];
}>();

const isDragging = ref(false);
const startPos = ref(0);
const startSize = ref(0);

function startDrag(e: MouseEvent) {
  isDragging.value = true;
  startPos.value = props.direction === 'horizontal' ? e.clientX : e.clientY;
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
  document.body.style.cursor = props.direction === 'horizontal' ? 'col-resize' : 'row-resize';
  document.body.style.userSelect = 'none';
}

function onDrag(e: MouseEvent) {
  if (!isDragging.value) return;
  
  const currentPos = props.direction === 'horizontal' ? e.clientX : e.clientY;
  const delta = props.direction === 'horizontal' 
    ? currentPos - startPos.value 
    : startPos.value - currentPos; // 垂直方向向上拖动为正
  
  emit('drag', delta);
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
    class="splitter"
    :class="`splitter-${direction}`"
    @mousedown="startDrag"
  ></div>
</template>

<style scoped>
.splitter {
  background: #444;
  transition: background 0.2s;
  flex-shrink: 0;
}

.splitter-horizontal {
  width: 4px;
  cursor: col-resize;
}

.splitter-vertical {
  height: 4px;
  cursor: row-resize;
}

.splitter:hover {
  background: #666;
}

.splitter:active {
  background: #4caf50;
}
</style>