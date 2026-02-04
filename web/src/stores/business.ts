/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-20 20:49:45
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-21 09:37:41
 */
/**
 * 全局业务状态管理
 */
import { defineStore } from 'pinia';
import { ref, watch } from 'vue';

export const useBusinessStore = defineStore('business', () => {
  // 业务类型
  const business = ref<string>('DEMO');

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
    business
  };
});