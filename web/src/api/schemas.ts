/**
 * Schemas 相关 API
 */
import { api } from './request';

export interface SchemaItem {
  id: string;
  name: string;
  schema: any;
  hasUnsavedChanges: boolean;
}

export interface CreateSchemaRequest {
  name: string;
  schema?: any;
}

export interface UpdateSchemaRequest {
  name?: string;
  schema?: any;
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
export async function updateSchema(id: string, request: UpdateSchemaRequest): Promise<SchemaItem> {
  return await api.put(`/schemas/${id}`, request);
}

/**
 * 删除 schema
 */
export async function deleteSchema(id: string): Promise<void> {
  return await api.delete(`/schemas/${id}`);
}

/**
 * 复制 schema
 */
export async function duplicateSchema(id: string, name: string): Promise<SchemaItem> {
  return await api.post(`/schemas/${id}/duplicate`, { name });
}