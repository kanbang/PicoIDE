<!--
 * @Descripttion: 
 * @version: 0.x
 * @Author: zhai
 * @Date: 2026-02-04 14:23:16
 * @LastEditors: zhai
 * @LastEditTime: 2026-02-04 14:48:40
-->
<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import LogViewer from '../common/LogViewer.vue';
import type { LogEvent } from '../common/types';


interface Props {
  isVisible?: boolean;
  isConnecting?: boolean;
  isConnected?: boolean;
}

const props = defineProps<Props>();

const visible = ref(props.isVisible || false);
const events = ref<LogEvent[]>([]);

watch(() => props.isVisible, (newValue) => {
  visible.value = newValue;
});

function toggle() {
  visible.value = !visible.value;
}

function show() {
  visible.value = true;
}

function hide() {
  visible.value = false;
}

function addEvent(event: LogEvent) {
  if (event.type === 'data') {
    event.expanded = false;
  }
  events.value.push(event);
}

function setEvents(newEvents: LogEvent[]) {
  events.value = newEvents;
}

function clearEvents() {
  events.value = [];
}

onUnmounted(() => {
});

defineExpose({
  addEvent,
  setEvents,
  clearEvents,
  show,
  hide,
  toggle,
  visible,
  events,
});
</script>

<template>
  <div class="console-panel" :class="{ visible }">
    <LogViewer
      :events="events"
      :is-loading="isConnecting"
      :show-filter="true"
      :show-header="true"
      @clear="clearEvents"
    />
  </div>
</template>

<style scoped>
.console-panel {
  width: 100%;
  height: 100%;
  background: #1e1e1e;
  border-top: 1px solid #333;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
