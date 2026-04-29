/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 19:53:48
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-19 19:36:56
 */

/**
 * API 统一导出
 */

// 导出 axios 实例
export { api } from './request';

// 导出 blocks 相关 API
export {
  getBlocks,
  executeSavedFlow,
  getFlowExecutions,
  getExecutionOutputs,
  stopExecution,
  getRunningFlows,
  getExecution,
  streamExecutionEvents,
  getExecutions
} from './execute';
export type {
  StartExecutionResponse,
  ExecutionRecord,
  OutputFile
} from './execute';

// 导出 schemas 相关 API
export { getFlows, createFlow, updateFlow, deleteFlow, duplicateFlow, getFlow } from './flows';
export type { FlowItem, CreateFlowRequest, UpdateFlowRequest } from './flows';
