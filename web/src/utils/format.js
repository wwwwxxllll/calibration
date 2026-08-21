// 格式化工具函数

/** 频率格式化：Hz → GHz / MHz / kHz（保留 4 位小数） */
export function formatHz(value) {
  if (value == null || !Number.isFinite(value)) return '-';
  const abs = Math.abs(value);
  if (abs >= 1e9) return `${(value / 1e9).toFixed(4)} GHz`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(4)} MHz`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(4)} kHz`;
  return `${value.toFixed(4)} Hz`;
}

/** 通用数值格式化（非频率数值 → 整数） */
export function formatValue(value) {
  if (value == null) return '-';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return String(value);
    return String(Math.round(value));
  }
  if (Array.isArray(value)) return `${value.length} 项`;
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** 标定值格式化：按单位区分（Hz → GHz/MHz；s → µs/ms/s；其余保留 4 位小数并带单位） */
export function formatCalibration(value, unit) {
  if (value == null || !Number.isFinite(value)) return '-';
  if (unit === 'Hz') return formatHz(value);
  if (unit === 's') {
    const abs = Math.abs(value);
    if (abs >= 1) return `${value.toFixed(3)} s`;
    if (abs >= 1e-3) return `${(value * 1e3).toFixed(3)} ms`;
    return `${(value * 1e6).toFixed(3)} µs`;
  }
  const v = Number(value.toFixed(4));
  return unit ? `${v} ${unit}` : `${v}`;
}

/** ISO 时间 → 可读格式（精确到秒，去除毫秒与时区后缀） */
export function formatTime(value) {
  if (!value) return '-';
  return String(value)
    .replace('T', ' ')
    .replace(/\.\d+/, '')
    .replace(/Z$/, '');
}

/** ISO 时间 → HH:MM:SS（窄栏时间线用） */
export function formatClock(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/** 状态 → Element Plus tag 类型 */
export function statusTagType(status) {
  if (status === 'succeeded' || status === 'completed') return 'success';
  if (status === 'failed') return 'danger';
  if (status === 'running') return 'primary';
  if (status === 'received') return 'info';
  return 'warning';
}

/** 状态 → 中文 */
export function statusLabel(status) {
  return (
    {
      succeeded: '成功',
      completed: '已完成',
      running: '进行中',
      received: '已接收',
      failed: '失败',
      pending_agent_review: '待确认',
      confirmed: '已确认',
      rejected: '已拒绝'
    }[status] ?? status ?? '-'
  );
}

/** 状态 → 极简圆点类名（ok / err / warn，其余返回空串走默认灰） */
export function statusDotClass(status) {
  if (status === 'succeeded' || status === 'completed' || status === 'confirmed') return 'ok';
  if (status === 'failed' || status === 'rejected') return 'err';
  if (status === 'running' || status === 'pending_agent_review') return 'warn';
  return '';
}
