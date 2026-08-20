<script setup>
import { ref, computed } from 'vue';
import { statusDotClass, statusLabel, formatTime } from '../utils/format';

const props = defineProps({
  currentActions: { type: Array, default: () => [] },
  historyGroups: { type: Array, default: () => [] },
  currentCalibrationId: { type: String, default: null },
  activeId: { type: String, default: null }
});

const emit = defineEmits(['select']);

const CURRENT_LIMIT = 5;
const currentCollapsed = ref(true);
const visibleCurrent = computed(() =>
  currentCollapsed.value ? props.currentActions.slice(0, CURRENT_LIMIT) : props.currentActions
);
const currentHidden = computed(() => props.currentActions.length - visibleCurrent.value.length);
</script>

<template>
  <div class="action-list">
    <!-- 当前校准（字段与 calibration_id 分两行） -->
    <div class="current-head">
      <div class="group-title current"><span class="t-dot"></span>当前校准</div>
      <code class="cal-id">{{ currentCalibrationId ?? '—' }}</code>
    </div>
    <div v-if="!currentActions.length" class="empty">暂无 Action 记录</div>
    <button
      v-for="action in visibleCurrent"
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
    <button v-if="currentHidden > 0" class="fold" type="button" @click="currentCollapsed = !currentCollapsed">
      {{ currentCollapsed ? `展开当前校准 ${currentHidden} 项` : '收起' }}
    </button>

    <!-- 历史校准（按 calibration_id 折叠） -->
    <template v-if="historyGroups.length">
      <div class="group-title hist">
        <span class="t-dot"></span>历史校准
      </div>
      <details v-for="g in historyGroups" :key="g.calibration_id" class="cal-group">
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
    </template>
  </div>
</template>

<style scoped>
.action-list {
  display: grid;
  gap: 6px;
}
.current-head {
  margin: 2px 0 6px;
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
  margin-top: 10px;
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
.fold {
  padding: 7px 12px;
  border: 1px dashed var(--line-2);
  border-radius: 8px;
  background: transparent;
  color: var(--ink-3);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  font: inherit;
  transition: all 0.15s;
}
.fold:hover {
  border-color: var(--accent);
  color: var(--accent);
}
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
