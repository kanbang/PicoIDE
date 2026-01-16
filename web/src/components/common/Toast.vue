<template>
  <Transition name="toast">
    <div v-if="visible" :class="['toast', `toast-${type}`]" :style="style">
      <div class="toast-content">
        <span class="toast-icon">{{ icon }}</span>
        <span class="toast-message">{{ message }}</span>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

export interface ToastProps {
  message: string;
  type?: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
  position?: 'top' | 'bottom' | 'top-right' | 'bottom-right';
}

const props = withDefaults(defineProps<ToastProps>(), {
  type: 'info',
  duration: 3000,
  position: 'top-right'
});

const visible = ref(false);

const icon = computed(() => {
  const icons = {
    success: '✓',
    error: '✕',
    info: 'ℹ',
    warning: '⚠'
  };
  return icons[props.type];
});

const style = computed(() => {
  const positions = {
    'top': 'top: 20px; left: 50%; transform: translateX(-50%);',
    'bottom': 'bottom: 20px; left: 50%; transform: translateX(-50%);',
    'top-right': 'top: 20px; right: 20px;',
    'bottom-right': 'bottom: 20px; right: 20px;'
  };
  return positions[props.position];
});

onMounted(() => {
  // 触发动画
  requestAnimationFrame(() => {
    visible.value = true;
  });

  // 自动隐藏
  if (props.duration > 0) {
    setTimeout(() => {
      visible.value = false;
      // 等待动画完成后移除
      setTimeout(() => {
        emit('close');
      }, 300);
    }, props.duration);
  }
});

const emit = defineEmits<{
  close: [];
}>();
</script>

<style scoped>
.toast {
  position: fixed;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 9999;
  min-width: 300px;
  max-width: 500px;
}

.toast-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toast-icon {
  font-size: 18px;
  font-weight: bold;
  flex-shrink: 0;
}

.toast-message {
  flex: 1;
  word-break: break-word;
}

.toast-success {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.toast-error {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
}

.toast-info {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.toast-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

/* 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>