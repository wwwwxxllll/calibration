<script setup>
import { computed } from 'vue';
import { formatHz, statusLabel, statusDotClass } from '../utils/format';
import { usePagination } from '../utils/usePagination';
import Pager from './Pager.vue';

const props = defineProps({
  candidates: { type: Array, default: () => [] }
});

const list = computed(() => props.candidates);
const { page, total, paged, go } = usePagination(list);
</script>

<template>
  <details class="panel card" open>
    <summary>
      <span class="panel-title">候选校准值</span>
      <span class="panel-count">{{ candidates.length }}</span>
      <span class="chev">▶</span>
    </summary>
    <div class="panel-body">
      <div v-if="paged.length" class="cal-list">
        <div v-for="cand in paged" :key="cand.candidate_id" class="cal-item">
          <div class="cal-info">
            <div class="cal-key">{{ cand.key }}</div>
            <div class="cal-value mono">{{ formatHz(cand.value) }} {{ cand.unit }}</div>
          </div>
          <span class="chip" :class="statusDotClass(cand.status)">
            <i class="dot"></i>{{ statusLabel(cand.status) }}
          </span>
        </div>
      </div>
      <div v-else class="empty">暂无候选值</div>
      <Pager :page="page" :total="total" @change="go" />
    </div>
  </details>
</template>

<style scoped>
.cal-list {
  display: grid;
  gap: 6px;
}
.cal-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}
.cal-item:last-child {
  border-bottom: none;
}
.cal-info {
  flex: 1;
  min-width: 0;
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
.cal-item .chip {
  flex-shrink: 0;
  margin-top: 2px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
