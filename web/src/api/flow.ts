/**
 * Blocks 相关 API
 */
import { api } from './request';

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