/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 19:53:48
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-19 19:36:56
 */
/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 19:53:48
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-12 20:27:30
 */
/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 19:53:48
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-12 20:18:28
 */
/**
 * API 统一导出
 */

// 导出 axios 实例
export { api } from './request';

// 导出 blocks 相关 API
export { getBlocks, executeBlocks } from './run';
export type { ExecuteRequest, ExecuteResponse } from './run';

// 导出 schemas 相关 API
export { getFlows, createFlow, updateFlow, deleteFlow, duplicateFlow } from './flows';
export type { FlowItem, CreateFlowRequest, UpdateFlowRequest } from './flows';