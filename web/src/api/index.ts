/**
 * API 服务模块
 */
import axios from 'axios';

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
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

// 类型定义
interface BlocksResponse {
  blocks: any[];
}

interface ExecuteRequest {
  scripts?: string[];
  data?: Record<string, any>;
}

interface ExecuteResponse {
  ok: boolean;
  result?: any;
}

export interface SchemaItem {
  id: number;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

interface CreateSchemaRequest {
  name: string;
  schema?: any;
}

interface UpdateSchemaRequest {
  name?: string;
  schema?: any;
}

/**
 * 获取所有可用的 blocks
 */
export async function getBlocks(): Promise<any[]> {
  const data: BlocksResponse = await api.get('/flow/blocks');
  return data.blocks || [];
}

/**
 * 执行 block 计算
 */
export async function executeBlocks(request: ExecuteRequest): Promise<ExecuteResponse> {
  return await api.post('/flow/execute', request);
}

/**
 * 获取所有 schemas
 */
export async function getSchemas(): Promise<SchemaItem[]> {
  return await api.get('/schemas');
}

/**
 * 创建新 schema
 */
export async function createSchema(request: CreateSchemaRequest): Promise<SchemaItem> {
  return await api.post('/schemas', request);
}

/**
 * 更新 schema
 */
export async function updateSchema(id: number, request: UpdateSchemaRequest): Promise<SchemaItem> {
  return await api.put(`/schemas/${id}`, request);
}

/**
 * 删除 schema
 */
export async function deleteSchema(id: number): Promise<void> {
  return await api.delete(`/schemas/${id}`);
}

/**
 * 复制 schema
 */
export async function duplicateSchema(id: number, name: string): Promise<SchemaItem> {
  return await api.post(`/schemas/${id}/duplicate`, { name });
}