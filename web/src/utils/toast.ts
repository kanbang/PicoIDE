import { createApp, h } from 'vue';
import ToastContainer from '@/components/common/ToastContainer.vue';

interface ToastOptions {
  message: string;
  type?: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
  position?: 'top' | 'bottom' | 'top-right' | 'bottom-right';
}

let toastContainerInstance: any = null;

function initToastContainer() {
  if (toastContainerInstance) return;

  const container = document.createElement('div');
  container.className = 'toast-wrapper';
  document.body.appendChild(container);

  const app = createApp(ToastContainer);
  toastContainerInstance = app.mount(container);
}

export function showToast(options: ToastOptions): number {
  initToastContainer();
  return toastContainerInstance.showToast(options);
}

export function showSuccess(message: string, duration?: number): number {
  return showToast({ message, type: 'success', duration });
}

export function showError(message: string, duration?: number): number {
  return showToast({ message, type: 'error', duration });
}

export function showInfo(message: string, duration?: number): number {
  return showToast({ message, type: 'info', duration });
}

export function showWarning(message: string, duration?: number): number {
  return showToast({ message, type: 'warning', duration });
}

// 默认导出
export default {
  showToast,
  showSuccess,
  showError,
  showInfo,
  showWarning
};