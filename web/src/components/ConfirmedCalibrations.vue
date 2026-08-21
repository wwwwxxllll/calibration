<script setup>
import { computed } from 'vue';
import { formatHz } from '../utils/format';
import { usePagination } from '../utils/usePagination';
import Pager from './Pager.vue';

const props = defineProps({
  active: { type: Object, default: () => ({}) }
});

const activeList = computed(() => Object.entries(props.active));
const { page, total, paged, go } = usePagination(activeList);
</script>

<template>
  <details class="panel card" open>
    <summary>
      <span class="panel-title">已确认标定</span>
      <span class="panel-count">{{ activeList.length }}</span>
      <span class="chev">▶</span>
    </summary>
    <div class="panel-body">
      <div v-if="paged.length" class="cal-list">
        <div v-for="[key, cal] in paged" :key="key" class="cal-item">
          <div class="cal-info">
            <div class="cal-key">{{ key }}</div>
            <div class="cal-value mono">{{ formatHz(cal.value) }} {{ cal.unit }}</div>
          </div>
          <span class="chip ok"><i class="dot"></i>已确认</span>
        </div>
      </div>
      <div v-else class="empty">暂无已确认标定值</div>
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
