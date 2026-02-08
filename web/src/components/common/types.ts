/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-02-04 14:54:08
 * @LastEditors: zhai
 * @LastEditTime: 2026-02-04 15:13:42
 */
/**
 * 公共类型定义 - 供多个组件复用
 */

// Block 定义类型
export interface BlockDefinition {
  name: string;
  inputs?: Array<{ name: string }>;
  outputs?: Array<{ name: string }>;
  options?: Array<{ name: string; type: string; value?: any; items?: any[]; min?: number; max?: number; title?: string; }>;
  category?: string;
}

// 日志事件类型
export interface LogEvent {
  type: string;
  timestamp: string;
  source?: string;
  node_type?: string;
  node_id?: string;
  node_name?: string;
  message?: string;
  data?: any;
  error?: string;
  expanded?: boolean;
}

// 执行状态类型
export type ExecutionStatus = 'running' | 'completed' | 'failed' | 'stopping' | 'stopped' | null;

// 日志类型过滤器
export type LogTypeFilter = 'all' | string;

// 转换事件为 LogEvent 的辅助函数
export function toLogEvent(event: any): LogEvent {
  // 处理时间戳 - 支持 timestamp (ms), ts (s), 或默认当前时间
  let timestamp: string;
  if (event.timestamp) {
    timestamp = event.timestamp;
  } else if (event.ts !== undefined) {
    timestamp = new Date(event.ts * 1000).toISOString();
  } else {
    timestamp = new Date().toISOString();
  }

  return {
    type: event.type || 'info',
    timestamp,
    source: event.source ?? event.execution_id,
    node_type: event.node_type ?? event.node_name,
    node_id: event.node_id,
    message: event.message,
    data: event.data,
    error: event.error
  };
}
