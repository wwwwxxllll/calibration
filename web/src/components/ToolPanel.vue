<script setup>
defineProps({
  tools: { type: Array, default: () => [] }
});
</script>

<template>
  <details class="panel card" open>
    <summary>
      <span class="panel-title">可用工具</span>
      <span class="panel-count">{{ tools.length }}</span>
      <span class="chev">▶</span>
    </summary>
    <div class="panel-body">
      <div v-if="tools.length" class="tool-list">
        <div v-for="tool in tools" :key="tool.name" class="tool-item">
          <div class="tool-name">{{ tool.name }}</div>
          <div class="tool-desc">{{ tool.description }}</div>
        </div>
      </div>
      <div v-else class="empty">暂无工具</div>
    </div>
  </details>
</template>

<style scoped>
.tool-list {
  display: grid;
  gap: 6px;
}
.tool-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}
.tool-item:last-child {
  border-bottom: none;
}
.tool-name {
  font-weight: 600;
  font-size: 13px;
}
.tool-desc {
  margin-top: 4px;
  color: var(--ink-3);
  font-size: 12px;
  line-height: 1.5;
}
</style>
