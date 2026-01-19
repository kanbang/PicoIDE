/**
 * Schemas 相关 API
 */
import { api } from './request';

export interface FlowItem {
  id: string;
  name: string;
  flow: any;
  hasUnsavedChanges: boolean;
}

export interface CreateFlowRequest {
  name: string;
  flow?: any;
}

export interface UpdateFlowRequest {
  name?: string;
  flow?: any;
}

/**
 * 获取所有 flows
 */
export async function getFlows(): Promise<FlowItem[]> {
  return await api.get('/flows');
}

/**
 * 创建新 flow
 */
export async function createFlow(request: CreateFlowRequest): Promise<FlowItem> {
  return await api.post('/flows', request);
}

/**
 * 更新 flow
 */
export async function updateFlow(id: string, request: UpdateFlowRequest): Promise<FlowItem> {
  return await api.put(`/flows/${id}`, request);
}

/**
 * 删除 flow
 */
export async function deleteFlow(id: string): Promise<void> {
  return await api.delete(`/flows/${id}`);
}

/**
 * 复制 flow
 */
export async function duplicateFlow(id: string, name: string): Promise<FlowItem> {
  return await api.post(`/flows/${id}/duplicate`, { name });
}