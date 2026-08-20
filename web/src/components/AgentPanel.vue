<script setup>
import { formatTime } from '../utils/format';

defineProps({
  hubConnected: { type: Boolean, default: false },
  agents: { type: Array, default: () => [] }
});
</script>

<template>
  <div class="agents-pop">
    <button class="agents-btn" type="button">
      <i class="dot" :class="{ ok: hubConnected, err: !hubConnected }"></i>
      在线 Agent
      <span class="agents-count">{{ agents.length }}</span>
    </button>
    <div class="agents-menu">
      <div v-if="agents.length">
        <div v-for="agent in agents" :key="agent.agent_id" class="agent-row">
          <div class="name">{{ agent.name ?? agent.agent_id }}</div>
          <div class="meta">{{ agent.agent_id }} · 接入于 {{ formatTime(agent.connected_at) }}</div>
        </div>
      </div>
      <div v-else class="empty">暂无在线 Agent</div>
    </div>
  </div>
</template>

<style scoped>
.agents-pop {
  position: relative;
}
.agents-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 15px;
  border: 1px solid var(--line-2);
  border-radius: 10px;
  background: #fff;
  color: var(--ink-2);
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  box-shadow: var(--shadow);
  transition: all 0.15s;
  font: inherit;
}
.agents-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}
.agents-count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e8f7ef;
  color: #15803d;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.agents-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  width: 280px;
  background: #fff;
  border: 1px solid var(--line-2);
  border-radius: 12px;
  box-shadow: var(--shadow);
  padding: 8px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: all 0.15s;
  z-index: 30;
}
.agents-pop:hover .agents-menu,
.agents-pop:focus-within .agents-menu {
  opacity: 1;
  visibility: visible;
  transform: none;
}
.agent-row {
  padding: 10px 10px;
  border-radius: 8px;
}
.agent-row:hover {
  background: #f8f9fd;
}
.agent-row + .agent-row {
  border-top: 1px solid var(--line);
}
.agent-row .name {
  font-weight: 600;
  font-size: 13px;
}
.agent-row .meta {
  margin-top: 3px;
  color: var(--ink-3);
  font-size: 11.5px;
  word-break: break-all;
}
.empty {
  color: var(--ink-3);
  font-size: 13px;
  padding: 10px;
}
</style>
