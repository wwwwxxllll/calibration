// 后端 WebUI 只读接口客户端。
// 所有路径经 Vite proxy 转发到 FastAPI（默认 http://127.0.0.1:8000）。

const API_BASE = '';

async function getJson(path) {
  const res = await fetch(API_BASE + path);
  if (!res.ok) {
    const err = new Error(`${path} 返回 ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const api = {
  /** GET /state → Env 状态 */
  getState: () => getJson('/state'),

  /** GET /agents → 在线 Agent（轮询） */
  getAgents: () => getJson('/agents'),

  /** GET /tools → 工具清单 */
  getTools: () => getJson('/tools'),

  /** GET /actions → Action 历史（完整记录） */
  getActions: () => getJson('/actions'),

  /** GET /actions/{id} → 单个 Action 详情 */
  getAction: (id) => getJson(`/actions/${encodeURIComponent(id)}`),

  /** GET /actions/{id}/events → 执行事件时间线（轮询） */
  getActionEvents: (id) => getJson(`/actions/${encodeURIComponent(id)}/events`),

  /** GET /calibrations → 候选值 + 已确认标定 */
  getCalibrations: () => getJson('/calibrations')
};
