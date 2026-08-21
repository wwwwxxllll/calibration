<script setup>
import { computed } from 'vue';

const props = defineProps({
  calibrationId: { type: String, default: null },
  actions: { type: Array, default: () => [] }
});

// 校准流程固定步骤（与后端 qcal-env 的 Step1~Step7 对齐，Step6 拆为 Ramsey/Echo 两段）。
const STEPS = [
  { key: 'Step1', label: '读取频扫' },
  { key: 'Step2', label: 'Qubit 频扫' },
  { key: 'Step3', label: 'π 脉冲幅度' },
  { key: 'Step4', label: '激发态读取' },
  { key: 'Step5', label: 'T1 测量' },
  { key: 'Step6.1', label: 'Ramsey T2*' },
  { key: 'Step6.2', label: 'Echo T2' },
  { key: 'Step7', label: '读取保真度' }
];

const stepNodes = computed(() =>
  STEPS.map((s, i) => {
    const acts = props.actions.filter((a) => a.step === s.key);
    let status = 'pending';
    if (acts.length) {
      const ss = acts.map((a) => a.status);
      if (ss.includes('running')) status = 'running';
      else if (ss.includes('failed')) status = 'failed';
      else if (ss.some((x) => x === 'succeeded' || x === 'completed')) status = 'done';
    }
    return { ...s, index: i + 1, status };
  })
);

const running = computed(() => stepNodes.value.find((s) => s.status === 'running'));
const doneCount = computed(() => stepNodes.value.filter((s) => s.status === 'done').length);

const statusText = { done: '✓ 完成', running: '进行中', failed: '失败', pending: '待执行' };
</script>

<template>
  <section class="steps-card">
    <div class="steps-head">
      <h2>校准流程 <code v-if="calibrationId">{{ calibrationId }}</code></h2>
      <span class="hint">
        {{ running ? `第 ${running.index} / ${stepNodes.length} 步 · ${running.label} 进行中` : `${doneCount} / ${stepNodes.length} 步完成` }}
      </span>
    </div>
    <div class="steps-h">
      <div v-for="s in stepNodes" :key="s.key" class="step-node" :class="s.status">
        <div class="step-circle">{{ s.index }}</div>
        <div class="step-label">{{ s.label }}</div>
        <div class="step-status">{{ statusText[s.status] }}</div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.steps-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: var(--radius, 14px);
  box-shadow: var(--shadow);
  padding: 18px 20px 20px;
}
.steps-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}
.steps-head h2 {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--ink-2);
  display: flex;
  align-items: center;
  gap: 8px;
}
.steps-head h2::before {
  content: '';
  width: 4px;
  height: 12px;
  border-radius: 2px;
  background: var(--grad);
}
.steps-head code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11.5px;
  background: #f1f2f7;
  padding: 2px 6px;
  border-radius: 5px;
  color: var(--ink-2);
  text-transform: none;
  letter-spacing: 0;
}
.hint {
  color: var(--ink-3);
  font-size: 12px;
  white-space: nowrap;
}
.steps-h {
  display: flex;
  align-items: flex-start;
}
.step-node {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}
.step-node:not(:last-child)::after {
  content: '';
  position: absolute;
  top: 15px;
  left: calc(50% + 16px);
  width: calc(100% - 32px);
  height: 2px;
  background: var(--line-2);
  border-radius: 1px;
}
.step-node.done:not(:last-child)::after {
  background: linear-gradient(90deg, var(--ok), #86d3a5);
}
.step-circle {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12.5px;
  font-weight: 700;
  background: #fff;
  border: 2px solid var(--line-2);
  color: var(--ink-3);
}
.step-node.done .step-circle {
  background: var(--ok);
  border-color: var(--ok);
  color: #fff;
}
.step-node.running .step-circle {
  background: #fff;
  border-color: var(--accent);
  color: var(--accent);
  box-shadow: 0 0 0 4px rgba(79, 110, 247, 0.14);
}
.step-node.failed .step-circle {
  background: var(--err);
  border-color: var(--err);
  color: #fff;
}
.step-label {
  margin-top: 9px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
}
.step-node.running .step-label {
  color: var(--accent);
}
.step-status {
  margin-top: 5px;
  font-size: 11px;
  font-weight: 600;
}
.step-node.done .step-status {
  color: var(--ok);
}
.step-node.running .step-status {
  color: var(--accent);
}
.step-node.failed .step-status {
  color: var(--err);
}
.step-node.pending .step-status {
  color: var(--ink-3);
}
</style>
