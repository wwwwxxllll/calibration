<script setup>
import { ref, computed } from 'vue';
import { formatClock } from '../utils/format';

const props = defineProps({
  events: { type: Array, default: () => [] }
});

const LIMIT = 5;
const collapsed = ref(true);

const stageLabel = (stage) =>
  ({
    received: '已接收',
    validating: '校验中',
    validated: '已校验',
    executing: '执行中',
    running: '进行中',
    succeeded: '成功',
    completed: '已完成',
    failed: '失败',
    file_read: '读取文件'
  }[stage] ?? stage);

const sorted = computed(() => [...props.events].sort((a, b) => String(a.timestamp).localeCompare(String(b.timestamp))));
const visible = computed(() => (collapsed.value ? sorted.value.slice(0, LIMIT) : sorted.value));
const hiddenCount = computed(() => sorted.value.length - visible.value.length);

const dotClass = (stage) => {
  if (stage === 'succeeded' || stage === 'completed') return 'ok';
  if (stage === 'failed') return 'err';
  if (stage === 'running' || stage === 'executing' || stage === 'validating') return 'running';
  return '';
};
</script>

<template>
  <section class="card">
    <div class="card-head">
      <h2 class="sec-title">执行时间线</h2>
      <span v-if="!events.length" class="hint">轮询中…</span>
    </div>

    <div v-if="sorted.length" class="timeline">
      <div v-for="(event, index) in visible" :key="index" class="tl-item">
        <i class="tl-dot" :class="dotClass(event.stage)"></i>
        <div class="tl-body">
          <div class="tl-head">
            <span class="tl-stage">{{ stageLabel(event.stage) }}</span>
            <span class="tl-time">{{ formatClock(event.timestamp) }}</span>
          </div>
          <div class="tl-msg">{{ event.message }}</div>
        </div>
      </div>
    </div>
    <div v-else class="empty">暂无事件</div>

    <button v-if="hiddenCount > 0" class="toggle" type="button" @click="collapsed = !collapsed">
      {{ collapsed ? `展开全部 ${hiddenCount} 项` : '收起' }}
    </button>
  </section>
</template>

<style scoped>
.timeline {
  display: grid;
}
.tl-item {
  display: flex;
  gap: 12px;
  position: relative;
  padding-bottom: 18px;
}
.tl-item:last-child {
  padding-bottom: 0;
}
.tl-item:not(:last-child)::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 16px;
  bottom: 0;
  width: 2px;
  background: var(--line-2);
  border-radius: 1px;
}
.tl-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--ink-3);
  margin-top: 3px;
  flex-shrink: 0;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px var(--line-2);
}
.tl-dot.ok {
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.18);
}
.tl-dot.err {
  background: var(--err);
  box-shadow: 0 0 0 3px rgba(225, 29, 72, 0.14);
}
.tl-dot.running {
  background: var(--accent);
  box-shadow: 0 0 0 3px rgba(79, 110, 247, 0.18);
  animation: pulse 1.4s ease-in-out infinite;
}
.tl-body {
  min-width: 0;
  flex: 1;
}
.tl-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}
.tl-stage {
  font-weight: 600;
  font-size: 13px;
  white-space: nowrap;
}
.tl-time {
  color: var(--ink-3);
  font-size: 11px;
  flex-shrink: 0;
}
.tl-msg {
  margin-top: 4px;
  color: var(--ink-2);
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
}
.toggle {
  margin-top: 14px;
  width: 100%;
  padding: 7px 12px;
  border: 1px solid var(--line-2);
  border-radius: 8px;
  background: #fff;
  color: var(--ink-2);
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  font: inherit;
  transition: all 0.15s;
}
.toggle:hover {
  border-color: var(--accent);
  color: var(--accent);
}
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}
</style>
