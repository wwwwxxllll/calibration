<script setup>
defineProps({
  page: { type: Number, default: 1 },
  total: { type: Number, default: 1 }
});

const emit = defineEmits(['change']);
</script>

<template>
  <div v-if="total > 1" class="pager">
    <button class="pager-btn" type="button" :disabled="page <= 1" @click="emit('change', page - 1)">‹</button>
    <span class="pager-info">{{ page }} / {{ total }}</span>
    <button class="pager-btn" type="button" :disabled="page >= total" @click="emit('change', page + 1)">›</button>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.pager-btn {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid var(--line-2);
  background: #fff;
  color: var(--ink-2);
  cursor: pointer;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
  padding: 0;
}
.pager-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}
.pager-btn:disabled {
  opacity: 0.4;
  cursor: default;
}
.pager-info {
  margin-left: auto;
  font-size: 12px;
  color: var(--ink-3);
}
</style>
