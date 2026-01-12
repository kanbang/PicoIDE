/*
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-12 19:53:48
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-12 20:27:54
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
export { getBlocks, executeBlocks } from './flow';
export type { ExecuteRequest, ExecuteResponse } from './flow';

// 导出 schemas 相关 API
export { getSchemas, createSchema, updateSchema, deleteSchema, duplicateSchema } from './schemas';
export type { SchemaItem, CreateSchemaRequest, UpdateSchemaRequest } from './schemas';