/**
 * axios 实例和拦截器配置
 */
import axios from 'axios';
import { useBusinessStore } from '@/stores/business';

export const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从 Pinia store 获取 business（自动缓存）
    const businessStore = useBusinessStore();
    config.headers['X-Business'] = businessStore.business;
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url} (business: ${businessStore.business})`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.config.url}`, response.data);
    return response.data;
  },
  (error) => {
    console.error('[API Response Error]', error);
    const message = error.response?.data?.message || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);