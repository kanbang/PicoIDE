/**
 * 全局业务状态管理
 */
import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useBusinessStore = defineStore('business', () => {
  // 业务类型
  const business = ref<string>('daq');

  // 从 localStorage 初始化
  const savedBusiness = localStorage.getItem('global_business');
  if (savedBusiness) {
    business.value = savedBusiness;
  }

  // 监听变化并保存到 localStorage，同时重新加载页面
  watch(business, (newValue) => {
    localStorage.setItem('global_business', newValue);
    // 重新加载页面以应用新的业务类型
    window.location.reload();
  });

  return {
    business,
    setBusiness: (value: string) => {
      business.value = value;
    }
  };
});