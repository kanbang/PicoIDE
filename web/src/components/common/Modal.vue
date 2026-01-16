<template>
  <Transition name="modal">
    <div v-if="visible" class="modal-overlay" @click="handleOverlayClick">
      <div class="modal-container" :class="sizeClass" @click.stop>
        <div v-if="showHeader" class="modal-header">
          <slot name="header">
            <h3 class="modal-title">{{ title }}</h3>
          </slot>
          <button v-if="closable" class="modal-close" @click="close">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <slot></slot>
        </div>
        <div v-if="showFooter" class="modal-footer">
          <slot name="footer">
            <button v-if="showCancel" class="modal-btn modal-btn-cancel" @click="handleCancel">
              {{ cancelText }}
            </button>
            <button v-if="showConfirm" class="modal-btn modal-btn-confirm" @click="handleConfirm">
              {{ confirmText }}
            </button>
          </slot>
        </div>
      </div>
    </div>
  </Transition>
</template>



<script setup lang="ts">
import { computed, watch } from 'vue';

export interface ModalProps {
  visible: boolean;
  title?: string;
  size?: 'small' | 'medium' | 'large' | 'full';
  closable?: boolean;
  closeOnClickOverlay?: boolean;
  showHeader?: boolean;
  showFooter?: boolean;
  showCancel?: boolean;
  showConfirm?: boolean;
  cancelText?: string;
  confirmText?: string;
}

const props = withDefaults(defineProps<ModalProps>(), {
  title: '',
  size: 'medium',
  closable: true,
  closeOnClickOverlay: true,
  showHeader: true,
  showFooter: true,
  showCancel: true,
  showConfirm: true,
  cancelText: '取消',
  confirmText: '确认'
});

const emit = defineEmits<{
  'update:visible': [value: boolean];
  close: [];
  cancel: [];
  confirm: [];
}>();

const sizeClass = computed(() => `modal-size-${props.size}`);

function close() {
  emit('update:visible', false);
  emit('close');
}

function handleCancel() {
  emit('cancel');
  close();
}

function handleConfirm() {
  emit('confirm');
  // 注意：confirm 不自动关闭，由调用方决定
}

function handleOverlayClick() {
  if (props.closeOnClickOverlay) {
    close();
  }
}

// ESC 键关闭
watch(() => props.visible, (newVal) => {
  if (newVal) {
    document.addEventListener('keydown', handleKeydown);
  } else {
    document.removeEventListener('keydown', handleKeydown);
  }
});

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.closable) {
    close();
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  background: #2d2d2d;
  padding: 24px;
  border-radius: 8px;
  min-width: 400px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
}

.modal-size-small {
  width: 400px;
}

.modal-size-medium {
  width: 600px;
}

.modal-size-large {
  width: 800px;
}

.modal-size-full {
  width: 100%;
  height: 100%;
  max-height: 100%;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.modal-title {
  margin: 0;
  font-size: 18px;
  color: #fff;
}

.modal-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  color: #aaa;
  transition: all 0.2s;
}

.modal-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  color: #ccc;
}

.modal-body p {
  margin: 0 0 24px 0;
  font-size: 14px;
  color: #ccc;
}

/* 输入框样式 */
.modal-body input {
  width: 100%;
  padding: 8px 12px;
  background: #3d3d3d;
  border: 1px solid #555;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
  box-sizing: border-box;
}

.modal-body input:focus {
  outline: none;
  border-color: #4caf50;
}

.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  flex-shrink: 0;
}

.modal-btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.modal-btn-cancel {
  background: #3d3d3d;
  border: 1px solid #555;
  color: #fff;
}

.modal-btn-cancel:hover {
  background: #4d4d4d;
}

.modal-btn-confirm {
  background: #4caf50;
  border-color: #4caf50;
  color: #fff;
}

.modal-btn-confirm:hover {
  background: #45a049;
}

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  opacity: 0;
  transform: scale(0.9) translateY(-20px);
}

.modal-enter-from .modal-overlay,
.modal-leave-to .modal-overlay {
  opacity: 0;
}
</style>