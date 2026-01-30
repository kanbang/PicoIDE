<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width="24"
    height="24"
    fill="currentColor"
    :class="{ 'running': isRunning, 'animate-spin': isRunning }"
  >
    <path
      v-if="!isRunning"
      d="M8 5v14l11-7z"
    />
    <rect
      v-else
      x="6" y="6" width="12" height="12" rx="2"
    />
  </svg>
</template>

<script setup lang="ts">
defineProps<{
  isRunning?: boolean;
}>();
</script>

<style scoped>
.running {
  color: #ff6b6b;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 2s linear infinite;
}
</style>