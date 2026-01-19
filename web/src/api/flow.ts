/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 20:11:28
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-19 10:46:56
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
  schema?: Record<string, any>;
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
 * 获取所有输出文件
 */
export async function getOutputFiles(): Promise<OutputFile[]> {
  return await api.get('/flow/output-files');
}

/**
 * 获取输出文件内容
 */
export async function getOutputFile(fileId: string): Promise<Blob> {
  const url = `/flow/output-files/${fileId}`;
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
  return await api.delete(`/flow/output-files/${fileId}`);
}

/**
 * 清理旧输出文件
 */
export async function cleanupOutputFiles(maxAgeHours: number = 24): Promise<any> {
  return await api.delete(`/flow/output-files/cleanup?max_age_hours=${maxAgeHours}`);
}