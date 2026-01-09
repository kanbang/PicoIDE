<script setup lang="ts">
import { reactive } from 'vue';
import { NodeFlow } from './components/NodeFlow.vue';

const block = reactive({
  schema: {},
  blocks: []
});

defineProps<{
  msg: string
}>()
</script>

<template>
  <div style="width: 100vw; height: 100vh">
    <NodeFlow v-if="block.blocks.length > 0" v-model:schema="block.schema" :blocks="block.blocks"/>
  </div>
</template>

<style scoped>
h1 {
  font-weight: 500;
  font-size: 2.6rem;
  position: relative;
  top: -10px;
}

h3 {
  font-size: 1.2rem;
}

.greetings h1,
.greetings h3 {
  text-align: center;
}

@media (min-width: 1024px) {
  .greetings h1,
  .greetings h3 {
    text-align: left;
  }
}
</style>
