/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 20:11:28
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-19 20:32:09
 */
/**
 * Blocks 相关 API
 */
import { api } from './request';

export interface BlocksResponse {
  blocks: any[];
}

export interface ExecuteRequest {
  scripts?: string[];
  flow?: Record<string, any>;
}

export interface ExecuteResponse {
  ok: boolean;
  result?: any;
  output_files?: OutputFile[];
  execution_time?: number;
  timestamp?: string;
}

export interface OutputFile {
  file_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  file_size: number;
  created_at: string;
  can_open: boolean;
  can_download: boolean;
}

/**
 * 获取所有可用的 blocks
 */
export async function getBlocks(): Promise<any[]> {
  const data: BlocksResponse = await api.get('/engine/blocks');
  return data.blocks || [];
}

/**
 * 执行 block 计算
 */
export async function executeBlocks(request: ExecuteRequest): Promise<ExecuteResponse> {
  return await api.post('/engine/execute', request);
}

/**
 * 执行已保存的 Flow
 */
export async function executeSavedFlow(flowId: string): Promise<ExecuteResponse> {
  return await api.post('/engine/execute-saved', { flow_id: flowId });
}

/**
 * 获取所有输出文件
 */
export async function getOutputFiles(): Promise<OutputFile[]> {
  return await api.get('/engine/output-files');
}

/**
 * 获取输出文件内容
 */
export async function getOutputFile(fileId: string): Promise<Blob> {
  const url = `/engine/output-files/${fileId}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`获取文件失败: ${response.status}`);
  }
  return await response.blob();
}

/**
 * 删除输出文件
 */
export async function deleteOutputFile(fileId: string): Promise<any> {
  return await api.delete(`/engine/output-files/${fileId}`);
}

/**
 * 清理旧输出文件
 */
export async function cleanupOutputFiles(maxAgeHours: number = 24): Promise<any> {
  return await api.delete(`/engine/output-files/cleanup?max_age_hours=${maxAgeHours}`);
}

/**
 * 获取指定 Flow 的所有执行记录
 */
export async function getFlowExecutions(
  flowId: string,
  status?: string,
  limit: number = 20,
  offset: number = 0
): Promise<{
  executions: ExecutionRecord[];
  total: number;
  limit: number;
  offset: number;
}> {
  let url = `/engine/flows/${flowId}/executions?limit=${limit}&offset=${offset}`;
  if (status) {
    url += `&status=${status}`;
  }
  return await api.get(url);
}

/**
 * 获取指定执行的所有输出文件
 */
export async function getExecutionOutputs(executionId: string): Promise<{
  execution_id: string;
  output_files: OutputFile[];
}> {
  return await api.get(`/engine/executions/${executionId}/outputs`);
}

// ==================== 类型定义 ====================

export interface ExecutionRecord {
  execution_id: string;
  flow_id: string;
  status: string;
  start_time: string;
  end_time: string | null;
  execution_time: number;
  total_nodes: number;
  executed_nodes: number;
  failed_nodes: number;
  tag: string | null;
  scripts_path: string;
  scripts_hash: string;
}