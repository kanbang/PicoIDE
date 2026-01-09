<!--
 * @Descripttion:
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09 10:29:35
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-09 19:12:50
-->
<script setup lang="ts">
import NodeFlow from './components/NodeFlow/index.vue'
import { ref, onMounted } from 'vue'

const STORAGE_KEY = 'nodeflow_schema'

// 使用 ref 引用 NodeFlow 组件实例
const nodeFlowRef = ref<InstanceType<typeof NodeFlow> | null>(null)

// 保存状态（同步 NodeFlow 内部的状态）
const hasUnsavedChanges = ref(false)

// 预定义的 blocks（静态，直接定义并传递）
const blocks = [
  {
    inputs: [],
    name: 'Sensor',
    options: [
      {
        items: ['1000', '2000', '20000', '50000', '52000', '100000', '105000', '128000'],
        name: '采样率',
        properties: { items: ['1000', '2000', '20000', '50000', '52000', '100000', '105000', '128000'] },
        type: 'SelectOption',
        value: '128000'
      },
      {
        items: ['Bipolar[-10V,10V]'],
        name: '量程',
        properties: { items: ['Bipolar[-10V,10V]'] },
        type: 'SelectOption',
        value: 'Bipolar[-10V,10V]'
      }
    ],
    outputs: [{ name: 'O-Sensor' }]
  },
  {
    inputs: [{ name: 'I-Sensor' }],
    name: 'Channel',
    options: [
      { name: '启用', type: 'CheckboxOption', value: true },
      {
        items: ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'],
        name: '通道',
        properties: { items: ['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'] },
        type: 'SelectOption',
        value: null
      },
      { max: 10, min: 0, name: '灵敏度', properties: { max: 10, min: 0 }, type: 'NumberOption', value: null },
      {
        items: ['m', 'm/s', 'm/s²', 'g'],
        name: '单位',
        properties: { items: ['m', 'm/s', 'm/s²', 'g'] },
        type: 'SelectOption',
        value: null
      },
      { name: 'IEPE/ICP/CCLD', type: 'CheckboxOption', value: true }
    ],
    outputs: [{ name: 'O-List-XY' }]
  },
  {
    inputs: [{ name: 'I-List-XY' }],
    name: 'ToList1D',
    options: [
      {
        items: ['X', 'Y'],
        name: '输出',
        properties: { items: ['X', 'Y'] },
        type: 'SelectOption',
        value: 'Y'
      }
    ],
    outputs: [{ name: 'O-List-V' }]
  },
  {
    inputs: [{ name: 'I-List-X' }, { name: 'I-List-Y' }],
    name: 'ToList2D',
    options: [],
    outputs: [{ name: 'O-List-XY' }]
  },
  {
    inputs: [{ name: 'I-List-V' }],
    name: 'FourierTransform',
    options: [{ name: '绝对值', type: 'CheckboxOption', value: true }],
    outputs: [{ name: 'O-List-XY' }]
  },
  {
    inputs: [{ name: 'List-XY' }],
    name: 'Result',
    options: [
      {
        items: ['时域', '频域', 'FREE'],
        name: '类型',
        properties: { items: ['时域', '频域', 'FREE'] },
        type: 'SelectOption',
        value: null
      },
      { name: '名称', type: 'InputOption', value: '' }
    ],
    outputs: []
  }
]

// 从本地存储加载 schema
function loadFromStorage(): void {
  const savedSchema = localStorage.getItem(STORAGE_KEY)
  if (savedSchema) {
    try {
      const schema = JSON.parse(savedSchema)
      // 通过 ref 调用 NodeFlow 的 loadSchema 方法
      nodeFlowRef.value?.loadSchema(schema)
    } catch (e) {
      console.error('Failed to parse saved schema:', e)
    }
  }
}

// 保存 schema 到本地存储
function saveToStorage(data: any): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  hasUnsavedChanges.value = false
}

// 处理 NodeFlow 的保存事件（用户点击保存按钮）
function handleSave(data: any): void {
  saveToStorage(data)
}

// 处理 schema 更新事件（仅日志，不自动保存）
function handleUpdate(schema: any): void {
  console.log('Schema updated:', schema)
}

// 处理未保存更改状态变化（同步到父组件状态，可用于 UI 提示）
function handleUnsavedChanges(changes: boolean): void {
  hasUnsavedChanges.value = changes
  console.log('Unsaved changes:', changes)
}

// 可选：处理错误事件（最新 NodeFlow 有 emit('error')）
function handleError(message: string): void {
  console.error('NodeFlow error:', message)
  // 这里可以添加全局错误提示
}

// 组件挂载后加载存储的数据
onMounted(() => {
  loadFromStorage()
})
</script>

<template>
  <div style="width: 100vw; height: 100vh">
    <NodeFlow ref="nodeFlowRef" :blocks="blocks" @save="handleSave" @update="handleUpdate"
      @unsavedChanges="handleUnsavedChanges" @error="handleError" />
  </div>
</template>

<style scoped>
/* 如需添加全局样式或未保存提示，可在这里扩展 */
</style>