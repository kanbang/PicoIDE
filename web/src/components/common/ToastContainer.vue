<template>
  <div class="toast-container">
    <Toast
      v-for="toast in toasts"
      :key="toast.id"
      :message="toast.message"
      :type="toast.type"
      :duration="toast.duration"
      :position="toast.position"
      @close="removeToast(toast.id)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Toast, { ToastProps } from './Toast.vue';

interface ToastItem extends ToastProps {
  id: number;
}

const toasts = ref<ToastItem[]>([]);
let toastIdCounter = 0;

function showToast(props: Omit<ToastProps, 'duration'> & { duration?: number }) {
  const id = ++toastIdCounter;
  const toast: ToastItem = {
    id,
    ...props,
    duration: props.duration ?? 3000
  };
  toasts.value.push(toast);
  return id;
}

function removeToast(id: number) {
  const index = toasts.value.findIndex(t => t.id === id);
  if (index !== -1) {
    toasts.value.splice(index, 1);
  }
}

// 导出供全局使用
defineExpose({
  showToast
});
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 9998;
}
</style>