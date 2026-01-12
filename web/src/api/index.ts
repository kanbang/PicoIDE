/**
 * API 服务模块
 */

const API_BASE_URL = '/api';

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
  const response = await fetch(`${API_BASE_URL}/flow/blocks`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch blocks: ${response.statusText}`);
  }

  const data: BlocksResponse = await response.json();
  return data.blocks || [];
}

/**
 * 执行 block 计算
 */
export async function executeBlocks(request: ExecuteRequest): Promise<ExecuteResponse> {
  const response = await fetch(`${API_BASE_URL}/flow/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to execute blocks: ${response.statusText}`);
  }

  return response.json();
}