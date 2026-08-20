<script setup>
import { formatHz, statusLabel, statusDotClass } from '../utils/format';

defineProps({
  candidates: { type: Array, default: () => [] }
});
</script>

<template>
  <details class="panel card" open>
    <summary>
      <span class="panel-title">候选校准值</span>
      <span class="panel-count">{{ candidates.length }}</span>
      <span class="chev">▶</span>
    </summary>
    <div class="panel-body">
      <div v-if="candidates.length" class="cal-list">
        <div v-for="cand in candidates" :key="cand.candidate_id" class="cal-item">
          <div class="cal-key">{{ cand.key }}</div>
          <div class="cal-value mono">{{ formatHz(cand.value) }} {{ cand.unit }}</div>
          <div class="cal-status">
            <span class="chip" :class="statusDotClass(cand.status)">
              <i class="dot"></i>{{ statusLabel(cand.status) }}
            </span>
          </div>
        </div>
      </div>
      <div v-else class="empty">暂无候选值</div>
    </div>
  </details>
</template>

<style scoped>
.cal-list {
  display: grid;
  gap: 6px;
}
.cal-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}
.cal-item:last-child {
  border-bottom: none;
}
.cal-key {
  font-weight: 600;
  font-size: 13px;
  word-break: break-all;
}
.cal-value {
  margin-top: 4px;
  color: var(--accent);
  font-size: 13px;
  font-weight: 500;
}
.cal-status {
  margin-top: 7px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
