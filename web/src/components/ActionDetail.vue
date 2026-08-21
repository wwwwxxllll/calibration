<script setup>
import { computed } from 'vue';
import { formatValue, formatCalibration } from '../utils/format';

const props = defineProps({
  action: { type: Object, default: null }
});

const candidate = computed(() => props.action?.candidate ?? null);
const fit = computed(() => props.action?.fit ?? {});
const artifacts = computed(() => props.action?.artifacts ?? {});
const raw = computed(() => props.action?.raw ?? {});
const inputs = computed(() => props.action?.inputs ?? {});

const paramRows = computed(() => Object.entries(inputs.value));

const rSquared = computed(() =>
  fit.value.r_squared != null ? Number(fit.value.r_squared).toFixed(4) : '-'
);

const plotUrl = computed(() => (artifacts.value.plot ? artifacts.value.plot : null));
const reportUrl = computed(() => (artifacts.value.report ? artifacts.value.report : null));
const dataUrl = computed(() => (artifacts.value.data ? artifacts.value.data : null));
</script>

<template>
  <div v-if="!action" class="card empty-card">请选择一个 Action 查看详情</div>

  <template v-else>
    <!-- 候选校准值 + R² -->
    <div class="two-col">
      <div class="card">
        <h3 class="sec-title mb">候选校准值</h3>
        <div v-if="candidate" class="big-value">{{ formatCalibration(candidate.value, candidate.unit) }}</div>
        <div v-else class="empty">暂无候选值</div>
      </div>

      <div class="card">
        <h3 class="sec-title mb">R²</h3>
        <div class="big-value">{{ rSquared }}</div>
      </div>
    </div>

    <!-- 图片 -->
    <div class="card">
      <h3 class="sec-title mb">图片</h3>
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

    <!-- 实验参数 -->
    <div class="card">
      <h3 class="sec-title mb">实验参数</h3>
      <div v-if="paramRows.length" class="param-grid">
        <div v-for="[name, value] in paramRows" :key="name" class="param-box">
          <span class="param-name mono">{{ name }}</span>
          <span class="param-value mono">{{ formatValue(value) }}</span>
        </div>
      </div>
      <div v-else class="empty">暂无参数</div>
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
.big-value {
  font-size: 18px;
  font-weight: 700;
  word-break: break-all;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
.param-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.param-box {
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: #fafbfe;
}
.param-name {
  font-size: 11px;
  color: var(--ink-3);
  word-break: break-all;
}
.param-value {
  font-size: 13px;
  font-weight: 600;
  word-break: break-all;
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
</style>
