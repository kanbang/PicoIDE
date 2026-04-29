/*
 * @Descripttion:
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 20:11:28
 * @LastEditors: zhai
 * @LastEditTime: 2026-03-05 19:29:21
 */
/**
 * Execution-related API
 */
import { api } from './request';

export interface BlocksResponse {
  blocks: any[];
}

export interface StartExecutionResponse {
  ok: boolean;
  execution_id: string;
  status: string;
  timestamp: string;
}

export interface OutputFile {
  file_id: string;
  filename: string;
  file_path?: string;
  file_type: string;
  file_size: number;
  created_at: string;
  block_name?: string;
  can_open: boolean;
  can_download: boolean;
}

export interface RuntimeEvent {
  execution_id?: string;
  type?: string;
  source?: string;
  message?: string;
  data?: any;
  ts?: number;
  [key: string]: any;
}

const TERMINAL_EVENT_TYPES = new Set([
  'execution_completed',
  'execution_failed',
  'execution_stopped',
]);

export async function getBlocks(): Promise<any[]> {
  const data: BlocksResponse = await api.get('/engine/blocks');
  return data.blocks || [];
}

export async function executeSavedFlow(flowId: string): Promise<StartExecutionResponse> {
  return await api.post('/engine/execute-saved', { flow_id: flowId });
}

export async function stopExecution(executionId: string): Promise<{ ok: boolean }> {
  return await api.post('/engine/stop', { execution_id: executionId });
}

export async function getOutputFiles(): Promise<OutputFile[]> {
  return await api.get('/engine/output-files');
}

export async function getOutputFile(fileId: string): Promise<Blob> {
  const url = `/api/engine/output-files/${fileId}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`获取文件失败: ${response.status}`);
  }
  return await response.blob();
}

export async function deleteOutputFile(fileId: string): Promise<any> {
  return await api.delete(`/engine/output-files/${fileId}`);
}

export async function cleanupOutputFiles(maxAgeHours: number = 24): Promise<any> {
  return await api.delete(`/engine/output-files/cleanup?max_age_hours=${maxAgeHours}`);
}

export async function getFlowExecutions(
  flowId: string,
  status?: string,
  includeOutputs: boolean = true,
  limit: number = 20,
  offset: number = 0
): Promise<{
  executions: ExecutionRecord[];
  total: number;
  limit: number;
  offset: number;
}> {
  let url = `/engine/executions?flow_id=${flowId}&include_outputs=${includeOutputs}&limit=${limit}&offset=${offset}`;
  if (status) {
    url += `&status=${status}`;
  }
  const result = await api.get(url) as any;
  return {
    executions: result.data?.executions ?? [],
    total: result.data?.count ?? 0,
    limit: result.data?.limit ?? limit,
    offset: result.data?.offset ?? offset,
  };
}

export async function getExecutionOutputs(executionId: string): Promise<{
  execution_id: string;
  output_files: OutputFile[];
}> {
  const result = await api.get(`/engine/executions/${executionId}/outputs`) as any;
  return result;
}

export async function deleteExecution(executionId: string): Promise<any> {
  return await api.delete(`/engine/executions/${executionId}`);
}

export async function getRunningFlows(): Promise<{
  ok: boolean;
  running_executions: string[];
  count: number;
}> {
  return await api.get('/engine/running');
}

export async function getExecution(executionId: string): Promise<ExecutionRecord> {
  return await api.get(`/engine/executions/${executionId}`);
}

export function streamExecutionEvents(
  executionId: string,
  onMessage: (event: RuntimeEvent) => void,
  onError?: (error: string) => void,
  onEnd?: () => void
): EventSource {
  const url = `/api/engine/stream/${executionId}`;
  const eventSource = new EventSource(url);
  let ended = false;

  const finalize = () => {
    if (ended) {
      return;
    }
    ended = true;
    onEnd?.();
    eventSource.close();
  };

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.error) {
        onError?.(data.error);
        return;
      }
      onMessage(data);
      if (TERMINAL_EVENT_TYPES.has(data.type)) {
        finalize();
      }
    } catch (error) {
      console.error('Failed to parse SSE event:', error);
    }
  };

  eventSource.addEventListener('end', () => {
    finalize();
  });

  eventSource.onerror = () => {
    onError?.('SSE connection error');
    eventSource.close();
  };

  return eventSource;
}

export async function getExecutions(params?: {
  status?: string;
  source?: string;
  tag?: string;
  flow_id?: string;
  scripts_hash?: string;
  include_outputs?: boolean;
  limit?: number;
  offset?: number;
  start_time?: string;
  end_time?: string;
}): Promise<{
  executions: ExecutionRecord[];
  count: number;
  limit: number;
  offset: number;
}> {
  const queryParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        queryParams.append(key, String(value));
      }
    });
  }
  return await api.get(`/engine/executions?${queryParams.toString()}`);
}

export interface ExecutionRecord {
  execution_id: string;
  flow_id: string;
  status: string;
  source?: string;
  start_time: string;
  end_time: string | null;
  execution_time: number;
  total_nodes: number;
  executed_nodes: number;
  failed_nodes: number;
  tag: string | null;
  scripts_path: string;
  scripts_hash: string;
  output_files?: OutputFile[];
  output_files_count?: number;
}
