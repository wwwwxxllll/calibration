<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { api } from './api/client';
import StepTimeline from './components/StepTimeline.vue';
import ActionList from './components/ActionList.vue';
import ActionDetail from './components/ActionDetail.vue';
import EventTimeline from './components/EventTimeline.vue';
import AgentPanel from './components/AgentPanel.vue';
import ToolPanel from './components/ToolPanel.vue';
import ConfirmedCalibrations from './components/ConfirmedCalibrations.vue';
import CandidateCalibrations from './components/CandidateCalibrations.vue';

const state = ref(null);
const agents = ref([]);
const hubConnected = ref(false);
const tools = ref([]);
const actions = ref([]);
const calibrations = ref({ candidates: [], active: {} });
const activeId = ref(null);
const activeAction = ref(null);
const actionEvents = ref([]);
const connected = ref(false);
const error = ref('');
const lastUpdated = ref('--:--:--');

let agentsTimer = null;
let eventsTimer = null;

const statusText = computed(() => {
  if (!connected.value) return error.value ? '连接失败' : '未连接';
  return `${state.value?.backend_mode ?? '-'} · ${state.value?.device_id ?? '-'} / ${state.value?.qubit_id ?? '-'}`;
});

// 按 calibration_id 分组，最新校准在前；旧数据缺失 calibration_id 时回退到 action_id。
const calibrationGroups = computed(() => {
  const map = new Map();
  for (const a of actions.value) {
    const id = a.calibration_id ?? a.action_id;
    if (!map.has(id)) map.set(id, []);
    map.get(id).push(a);
  }
  return [...map.entries()]
    .map(([calibration_id, acts]) => {
      acts.sort((x, y) => String(y.timestamp).localeCompare(String(x.timestamp)));
      return { calibration_id, actions: acts, latest: acts[0]?.timestamp };
    })
    .sort((a, b) => String(b.latest).localeCompare(String(a.latest)));
});
const currentCalibrationId = computed(() => calibrationGroups.value[0]?.calibration_id ?? null);
const currentActions = computed(() => calibrationGroups.value[0]?.actions ?? []);
const historyGroups = computed(() => calibrationGroups.value.slice(1));

function nowClock() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

async function loadBase() {
  try {
    const [s, t, a, c] = await Promise.all([
      api.getState(),
      api.getTools(),
      api.getActions(),
      api.getCalibrations()
    ]);
    state.value = s;
    tools.value = t.tools ?? [];
    actions.value = a.actions ?? [];
    calibrations.value = c;
    connected.value = true;
    error.value = '';
    lastUpdated.value = nowClock();

    if (!activeId.value && actions.value.length) {
      await select(actions.value[0].action_id);
    }
  } catch (e) {
    connected.value = false;
    error.value = e.message;
  }
}

async function loadAgents() {
  try {
    const data = await api.getAgents();
    hubConnected.value = Boolean(data.hub_connected);
    agents.value = data.agents ?? [];
  } catch {
    hubConnected.value = false;
    agents.value = [];
  }
  lastUpdated.value = nowClock();
}

async function select(id) {
  activeId.value = id;
  actionEvents.value = [];
  try {
    activeAction.value = await api.getAction(id);
  } catch {
    activeAction.value = null;
  }
  startEventsPolling(id);
}

function startEventsPolling(id) {
  clearInterval(eventsTimer);
  let stop = false;
  const poll = async () => {
    if (stop) return;
    try {
      const data = await api.getActionEvents(id);
      actionEvents.value = data.events ?? [];
      const stages = actionEvents.value.map((e) => e.stage);
      if (stages.includes('completed') || stages.includes('failed')) {
        stop = true;
        clearInterval(eventsTimer);
      }
    } catch {
      stop = true;
      clearInterval(eventsTimer);
    }
  };
  eventsTimer = setInterval(poll, 800);
  poll();
}

onMounted(() => {
  loadBase();
  loadAgents();
  agentsTimer = setInterval(loadAgents, 1500);
});

onBeforeUnmount(() => {
  clearInterval(agentsTimer);
  clearInterval(eventsTimer);
});
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark">Q</div>
        <div>
          <h1>QCal 校准监控</h1>
          <span class="subtitle">只读监控 · 实验由 Agent 经 Star 发起</span>
        </div>
      </div>

      <span class="status-pill">
        <i class="dot" :class="{ ok: connected, err: !connected }"></i>
        <span class="status-text">{{ statusText }}</span>
      </span>

      <span class="auto-pill">
        <span class="spin"></span>自动刷新 · 最后更新 {{ lastUpdated }}
      </span>

      <AgentPanel :hub-connected="hubConnected" :agents="agents" />
    </header>

    <main>
      <StepTimeline :calibration-id="currentCalibrationId" :actions="currentActions" />

      <div class="grid">
        <aside class="col col-left">
          <h2 class="col-title">Action 历史</h2>
          <div class="card list-card">
            <ActionList
              :current-actions="currentActions"
              :history-groups="historyGroups"
              :current-calibration-id="currentCalibrationId"
              :active-id="activeId"
              @select="select"
            />
          </div>
        </aside>

        <div class="col col-main">
          <ActionDetail :action="activeAction" />
        </div>

        <aside class="col col-right">
          <EventTimeline :events="actionEvents" />
        </aside>
      </div>

      <div class="bottom-row">
        <ToolPanel :tools="tools" />
        <ConfirmedCalibrations :active="calibrations.active" />
        <CandidateCalibrations :candidates="calibrations.candidates" />
      </div>
    </main>
  </div>
</template>

<style>
:root {
  --bg: #f5f6fa;
  --card: #ffffff;
  --ink: #171c2e;
  --ink-2: #5a6072;
  --ink-3: #9aa1b2;
  --line: #eef0f6;
  --line-2: #e3e6f0;
  --accent: #4f6ef7;
  --accent-2: #8b5cf6;
  --grad: linear-gradient(135deg, #4f6ef7, #8b5cf6);
  --ok: #16a34a;
  --err: #e11d48;
  --warn: #d97706;
  --shadow: 0 1px 2px rgba(23, 28, 46, 0.04), 0 6px 16px rgba(23, 28, 46, 0.05);
}
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  -webkit-font-smoothing: antialiased;
}
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── 顶栏 ── */
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 32px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
  box-shadow: 0 1px 0 rgba(23, 28, 46, 0.02);
  position: sticky;
  top: 0;
  z-index: 10;
}
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: var(--grad);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  box-shadow: 0 4px 10px rgba(79, 110, 247, 0.35);
}
.brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.01em;
}
.subtitle {
  display: block;
  margin-top: 3px;
  color: var(--ink-3);
  font-size: 12px;
}

.status-pill {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  background: #fff;
  border: 1px solid var(--line-2);
  border-radius: 999px;
  color: var(--ink-2);
  font-size: 13px;
  box-shadow: var(--shadow);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ink-3);
  flex-shrink: 0;
  display: inline-block;
}
.dot.ok {
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.15);
}
.dot.err {
  background: var(--err);
  box-shadow: 0 0 0 3px rgba(225, 29, 72, 0.12);
}
.dot.warn {
  background: var(--warn);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.15);
}

.auto-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  background: #fff;
  border: 1px solid var(--line-2);
  border-radius: 999px;
  color: var(--ink-3);
  font-size: 12px;
  box-shadow: var(--shadow);
  white-space: nowrap;
}
.auto-pill .spin {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid var(--line-2);
  border-top-color: var(--accent);
  animation: spin 1.2s linear infinite;
  flex-shrink: 0;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ── 主区 ── */
main {
  flex: 1;
  max-width: 1560px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 32px 48px;
  display: grid;
  gap: 24px;
  align-items: start;
}
.grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 320px;
  gap: 24px;
  align-items: start;
}
.col {
  min-width: 0;
  display: grid;
  gap: 24px;
}
.col-left,
.col-right {
  position: sticky;
  top: 78px;
}
.col-title {
  margin: 4px 0 0;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-3);
}

/* ── 卡片 ── */
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 20px;
}
.card.list-card {
  padding: 12px;
}
.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16px;
}
.sec-title {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-2);
}
.sec-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 11px;
  border-radius: 2px;
  background: var(--grad);
  margin-right: 8px;
  vertical-align: -1px;
}
.sec-title.mb {
  margin-bottom: 16px;
}
.hint {
  color: var(--ink-3);
  font-size: 12px;
}
.empty {
  color: var(--ink-3);
  font-size: 13px;
  padding: 8px 0;
}

/* ── 状态徽章 ── */
.chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
  white-space: nowrap;
  background: #f1f2f7;
  color: var(--ink-2);
}
.chip .dot {
  width: 6px;
  height: 6px;
  box-shadow: none;
}
.chip.ok {
  background: #e8f7ef;
  color: #15803d;
}
.chip.err {
  background: #fdecef;
  color: #be123c;
}
.chip.warn {
  background: #fdf1e3;
  color: #b45309;
}
.chip.warn .dot {
  animation: pulse 1.4s ease-in-out infinite;
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

/* ── 可折叠面板（右侧）── */
.panel {
  padding: 0;
  overflow: hidden;
}
.panel > summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 18px;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-2);
  user-select: none;
  transition: background 0.15s;
}
.panel > summary:hover {
  background: #fafbfe;
}
.panel > summary::-webkit-details-marker {
  display: none;
}
.panel > summary::before {
  content: '';
  width: 4px;
  height: 12px;
  border-radius: 2px;
  background: var(--grad);
  flex-shrink: 0;
}
.panel > summary .panel-title {
  flex: 1;
}
.panel > summary .chev {
  color: var(--ink-3);
  transition: transform 0.15s;
  font-size: 10px;
  flex-shrink: 0;
}
.panel[open] > summary .chev {
  transform: rotate(90deg);
}
.panel-count {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: #f1f2f7;
  color: var(--ink-2);
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.panel-body {
  padding: 4px 18px 16px;
}

/* ── 底部三栏（工具 / 已确认标定 / 候选值）── */
.bottom-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 24px;
  align-items: start;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .col-left,
  .col-right {
    position: static;
  }
  .bottom-row {
    grid-template-columns: 1fr;
  }
}
</style>
