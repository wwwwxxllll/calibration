<script setup>
import { computed } from 'vue';
import { formatHz, formatValue } from '../utils/format';

const props = defineProps({
  action: { type: Object, default: null }
});

const fit = computed(() => props.action?.fit ?? {});
const result = computed(() => props.action?.result ?? {});
const candidate = computed(() => props.action?.candidate ?? null);
const artifacts = computed(() => props.action?.artifacts ?? {});
const outcome = computed(() => props.action?.outcome ?? {});
const raw = computed(() => props.action?.raw ?? {});
const inputs = computed(() => props.action?.inputs ?? {});

const fitItems = computed(() => [
  { label: '拟合模型', value: fit.value.model ?? '-' },
  { label: '中心频率', value: formatHz(fit.value.center_hz) },
  { label: '半高宽', value: formatHz(fit.value.half_width_hz) },
  { label: 'R²', value: fit.value.r_squared != null ? Number(fit.value.r_squared).toFixed(4) : '-' }
]);

const paramRows = computed(() => Object.entries(inputs.value));

const plotUrl = computed(() => (artifacts.value.plot ? artifacts.value.plot : null));
const reportUrl = computed(() => (artifacts.value.report ? artifacts.value.report : null));
const dataUrl = computed(() => (artifacts.value.data ? artifacts.value.data : null));
</script>

<template>
  <div v-if="!action" class="card empty-card">请选择一个 Action 查看详情</div>

  <template v-else>
    <!-- 拟合结果 + 候选校准值（同一列） | 实验参数 -->
    <div class="two-col">
      <div class="card">
        <h3 class="sec-title mb">拟合结果</h3>
        <div class="kv">
          <div v-for="item in fitItems" :key="item.label" class="kv-row">
            <span class="kv-label">{{ item.label }}</span>
            <span class="kv-value">{{ item.value }}</span>
          </div>
        </div>
        <div v-if="result.parameter" class="result-line">
          {{ result.parameter }} = {{ formatHz(result.value) }} {{ result.unit }}
        </div>

        <hr class="section-divider" />
        <h4 class="sub-sec-title">候选校准值</h4>
        <div v-if="candidate" class="kv">
          <div class="kv-row">
            <span class="kv-label">{{ candidate.key }}</span>
            <span class="kv-value">{{ formatHz(candidate.value) }} {{ candidate.unit }}</span>
          </div>
        </div>
        <div v-else class="empty">暂无候选值</div>
      </div>

      <div class="card">
        <h3 class="sec-title mb">实验参数</h3>
        <div v-if="paramRows.length" class="kv">
          <div v-for="[name, value] in paramRows" :key="name" class="kv-row">
            <span class="kv-label mono">{{ name }}</span>
            <span class="kv-value mono">{{ formatValue(value) }}</span>
          </div>
        </div>
        <div v-else class="empty">暂无参数</div>
      </div>
    </div>

    <!-- 产物 -->
    <div class="card">
      <h3 class="sec-title mb">产物</h3>
      <div class="artifacts">
        <a v-if="dataUrl" :href="dataUrl" download class="link">⬇ data.csv</a>
        <a v-if="reportUrl" :href="reportUrl" download class="link">⬇ report.md</a>
        <span v-if="!dataUrl && !reportUrl && !plotUrl" class="empty">暂无产物</span>
      </div>
      <img v-if="plotUrl" :src="plotUrl" alt="拟合曲线" class="plot" />
      <div class="raw-meta">
        扫描轴 {{ raw.sweep_name ?? '-' }} · {{ raw.point_count ?? '-' }} 点 · 有效 {{ raw.valid_point_count ?? '-' }}
      </div>
    </div>

    <!-- Outcome -->
    <div v-if="outcome.content || outcome.isError" class="card">
      <h3 class="sec-title mb">Outcome</h3>
      <div class="outcome" :class="{ error: outcome.isError }">{{ outcome.content }}</div>
    </div>
  </template>
</template>

<style scoped>
.empty-card {
  padding: 24px 20px;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
@media (max-width: 900px) {
  .two-col {
    grid-template-columns: 1fr;
  }
}
.kv {
  display: grid;
}
.kv-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px dashed var(--line);
}
.kv-row:last-child {
  border-bottom: none;
}
.kv-label {
  color: var(--ink-2);
  font-size: 13px;
  flex-shrink: 0;
}
.kv-value {
  font-size: 13px;
  font-weight: 500;
  text-align: right;
  word-break: break-all;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.result-line {
  margin-top: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
}
.section-divider {
  border: none;
  border-top: 1px dashed var(--line-2);
  margin: 16px 0 2px;
}
.sub-sec-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-3);
  margin: 0 0 4px;
}
.artifacts {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 13px;
  border-radius: 8px;
  background: #f1f4ff;
  color: var(--accent);
  font-size: 12.5px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.15s;
}
.link:hover {
  background: var(--accent);
  color: #fff;
}
.plot {
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  border: 1px solid var(--line);
}
.raw-meta {
  margin-top: 12px;
  color: var(--ink-3);
  font-size: 12px;
}
.outcome {
  font-size: 13px;
  color: var(--ink-2);
  line-height: 1.7;
  background: #f8f9fd;
  border: 1px solid var(--line);
  border-left: 3px solid var(--ok);
  border-radius: 10px;
  padding: 12px 14px;
}
.outcome.error {
  background: #fdf6f7;
  border-left-color: var(--err);
  color: #be123c;
}
</style>
