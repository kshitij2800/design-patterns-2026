// Phase 11 stub. Phase 12 replaces this body with the dashboard WebSocket
// (which fans out events from the backend EventBus). Until then nothing is pushed:
// the event feed polls GET /api/alerts and sensor cards keep the Phase 5 readings poll.

export type RealtimeEvent = { type: string; payload: unknown };

export function subscribeRealtime(_onEvent: (event: RealtimeEvent) => void): () => void {
  // no-op: nothing to connect to yet
  return () => {};
}