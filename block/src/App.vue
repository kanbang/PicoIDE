<!--
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-01-09 10:29:35
 * @LastEditors: zhai
 * @LastEditTime: 2026-01-09 11:22:08
-->
<script setup lang="ts">
import NodeFlow from './components/NodeFlow/index.vue'
import { reactive } from 'vue';

const block = reactive({
  schema: {},
  blocks: []
});


block.blocks = [{ "inputs": [], "name": "Sensor", "options": [{ "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"], "name": "采样率", "properties": { "items": ["1000", "2000", "20000", "50000", "52000", "100000", "105000", "128000"] }, "type": "SelectOption", "value": "128000" }, { "items": ["Bipolar[-10V,10V]"], "name": "量程", "properties": { "items": ["Bipolar[-10V,10V]"] }, "type": "SelectOption", "value": "Bipolar[-10V,10V]" }], "outputs": [{ "name": "O-Sensor" }] }, { "inputs": [{ "name": "I-Sensor" }], "name": "Channel", "options": [{ "name": "启用", "type": "CheckboxOption", "value": true }, { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"], "name": "通道", "properties": { "items": ["Channel 1", "Channel 2", "Channel 3", "Channel 4"] }, "type": "SelectOption", "value": null }, { "max": 10, "min": 0, "name": "灵敏度", "properties": { "max": 10, "min": 0 }, "type": "NumberOption", "value": null }, { "items": ["m", "m/s", "m/s²", "g"], "name": "单位", "properties": { "items": ["m", "m/s", "m/s²", "g"] }, "type": "SelectOption", "value": null }, { "name": "IEPE/ICP/CCLD", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] }, { "inputs": [{ "name": "I-List-XY" }], "name": "ToList1D", "options": [{ "items": ["X", "Y"], "name": "输出", "properties": { "items": ["X", "Y"] }, "type": "SelectOption", "value": "Y" }], "outputs": [{ "name": "O-List-V" }] }, { "inputs": [{ "name": "I-List-X" }, { "name": "I-List-Y" }], "name": "ToList2D", "options": [], "outputs": [{ "name": "O-List-XY" }] }, { "inputs": [{ "name": "I-List-V" }], "name": "FourierTransform", "options": [{ "name": "绝对值", "type": "CheckboxOption", "value": true }], "outputs": [{ "name": "O-List-XY" }] }, { "inputs": [{ "name": "List-XY" }], "name": "Result", "options": [{ "items": ["时域", "频域", "FREE"], "name": "类型", "properties": { "items": ["时域", "频域", "FREE"] }, "type": "SelectOption", "value": null }, { "name": "名称", "type": "InputOption", "value": "" }], "outputs": [] }]

</script>

<template>
  <div style="width: 100vw; height: 100vh">
    <NodeFlow v-if="block.blocks.length > 0" v-model:schema="block.schema" :blocks="block.blocks" />
  </div>
</template>

<style scoped>
header {
  line-height: 1.5;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>
