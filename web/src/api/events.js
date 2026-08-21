// 订阅后端 /events 的 Server-Sent Events 变更流。
// EventSource 断线后会自动重连；onOpen 在首次连接与每次重连成功后触发，
// 用于重新同步全量状态（避免错过断线期间的变更）。
export function subscribeEvents({ onOpen, onMessage, onError } = {}) {
  const source = new EventSource('/events');
  source.onopen = () => onOpen?.();
  source.onmessage = (event) => onMessage?.(event);
  source.onerror = () => onError?.();
  return source;
}
