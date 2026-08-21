<script setup>
import { computed } from 'vue';
import { statusDotClass, statusLabel, formatTime } from '../utils/format';
import { usePagination } from '../utils/usePagination';
import Pager from './Pager.vue';

const props = defineProps({
  currentActions: { type: Array, default: () => [] },
  historyGroups: { type: Array, default: () => [] },
  currentCalibrationId: { type: String, default: null },
  activeId: { type: String, default: null }
});

const emit = defineEmits(['select']);

const currentList = computed(() => props.currentActions);
const {
  page: currentPage,
  total: currentTotal,
  paged: currentPaged,
  go: currentGo
} = usePagination(currentList, 10);

const historyList = computed(() => props.historyGroups);
const {
  page: historyPage,
  total: historyTotal,
  paged: historyPaged,
  go: historyGo
} = usePagination(historyList, 10);
</script>

<template>
  <div class="action-list">
    <!-- 当前校准：完整框（可折叠） -->
    <details class="cal-group current" open>
      <summary>
        <span class="group-title current"><span class="t-dot"></span>当前校准</span>
        <code class="cal-id">{{ currentCalibrationId ?? '—' }}</code>
        <span class="chev">▶</span>
      </summary>
      <div class="current-body">
        <div v-if="!currentActions.length" class="empty">暂无 Action 记录</div>
        <button
          v-for="action in currentPaged"
          :key="action.action_id"
          class="action-item"
          :class="{ active: action.action_id === activeId }"
          type="button"
          @click="emit('select', action.action_id)"
        >
          <div class="action-head">
            <span class="action-name">{{ action.experiment }}</span>
            <span class="chip" :class="statusDotClass(action.status)">
              <i class="dot"></i>{{ statusLabel(action.status) }}
            </span>
          </div>
          <div class="action-meta">{{ action.step }} · {{ formatTime(action.timestamp) }}</div>
        </button>
        <Pager :page="currentPage" :total="currentTotal" @change="currentGo" />
      </div>
    </details>

    <!-- 历史校准（按 calibration_id 折叠） -->
    <template v-if="historyGroups.length">
      <div class="group-title hist">
        <span class="t-dot"></span>历史校准
      </div>
      <details v-for="g in historyPaged" :key="g.calibration_id" class="cal-group">
        <summary>
          <code>{{ g.calibration_id }}</code>
          <span class="cal-meta">{{ g.actions.length }} 项</span>
          <span class="chev">▶</span>
        </summary>
        <div class="cal-actions">
          <button
            v-for="action in g.actions"
            :key="action.action_id"
            class="action-item"
            :class="{ active: action.action_id === activeId }"
            type="button"
            @click="emit('select', action.action_id)"
          >
            <div class="action-head">
              <span class="action-name">{{ action.experiment }}</span>
              <span class="chip" :class="statusDotClass(action.status)">
                <i class="dot"></i>{{ statusLabel(action.status) }}
              </span>
            </div>
            <div class="action-meta">{{ action.step }} · {{ formatTime(action.timestamp) }}</div>
          </button>
        </div>
      </details>
      <Pager :page="historyPage" :total="historyTotal" @change="historyGo" />
    </template>
  </div>
</template>

<style scoped>
.action-list {
  display: grid;
  gap: 6px;
}
.group-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-2);
}
.group-title .t-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.group-title.current .t-dot {
  background: var(--accent);
}
.group-title.hist {
  color: var(--ink-3);
  border-top: 1px dashed var(--line-2);
  padding-top: 14px;
  margin-top: 0;
}
.group-title.hist .t-dot {
  background: var(--ink-3);
}
.cal-id {
  display: block;
  margin-top: 6px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  background: #f1f2f7;
  padding: 4px 8px;
  border-radius: 6px;
  color: var(--ink-2);
  font-weight: 500;
  word-break: break-all;
}
.action-item {
  text-align: left;
  padding: 11px 13px;
  border: 1px solid transparent;
  border-radius: 11px;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
  width: 100%;
  font: inherit;
  color: inherit;
  display: grid;
  gap: 5px;
}
.action-item:hover {
  background: #fff;
  border-color: var(--line-2);
  box-shadow: var(--shadow);
}
.action-item.active {
  background: #f5f7ff;
  border-color: #cdd7fd;
  box-shadow: 0 0 0 3px rgba(79, 110, 247, 0.08);
}
.action-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.action-name {
  font-weight: 600;
  font-size: 13px;
}
.action-item.active .action-name {
  color: var(--accent);
}
.action-meta {
  color: var(--ink-3);
  font-size: 11.5px;
}

/* 当前校准：完整框（标题 + 内容都在框内） */
.cal-group.current {
  margin: 0 0 16px;
  border: 1px solid var(--line-2);
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}
.cal-group.current > summary {
  background: #f5f7ff;
  border: none;
  border-radius: 0;
  padding: 11px 12px;
}
.cal-group.current > summary:hover {
  box-shadow: none;
  border-color: transparent;
}
.cal-group.current[open] > summary {
  border-bottom: 1px solid var(--line);
}
.cal-group.current > summary .cal-id {
  display: inline-block;
  margin-top: 0;
  flex: 1;
  min-width: 0;
  font-size: 11px;
  padding: 3px 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cal-group.current .current-body {
  padding: 12px;
  display: grid;
  gap: 6px;
}

/* 历史校准折叠组 */
.cal-group {
  margin-top: 2px;
}
.cal-group > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--line);
  background: #fafbfe;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
  transition: all 0.15s;
  user-select: none;
}
.cal-group > summary:hover {
  border-color: var(--line-2);
  box-shadow: var(--shadow);
}
.cal-group > summary::-webkit-details-marker {
  display: none;
}
.cal-group > summary code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cal-group > summary .cal-meta {
  font-weight: 400;
  font-size: 11px;
  color: var(--ink-3);
  white-space: nowrap;
}
.cal-group > summary .chev {
  margin-left: auto;
  color: var(--ink-3);
  transition: transform 0.15s;
  font-size: 10px;
}
.cal-group[open] > summary .chev {
  transform: rotate(90deg);
}
.cal-actions {
  display: grid;
  gap: 6px;
  padding: 8px 0 2px;
}
</style>
