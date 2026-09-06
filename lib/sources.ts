import type { LiveEvent, Snapshot, StreamName } from "./contracts";
export type SourceHealth = { healthy: boolean; checkedAt: string; detail: "configured" | "disabled" | "unavailable" };
export type SnapshotInput = { stream: StreamName; tenantId?: string; signal?: AbortSignal };
export type SubscriptionInput = SnapshotInput & { afterEventId?: string };
export interface LiveDataSource<T> { name: string; healthCheck(): Promise<SourceHealth>; fetchSnapshot(input: SnapshotInput): Promise<T>; subscribe(input: SubscriptionInput): AsyncIterable<LiveEvent>; }

/** Development-only adapter: exposes no fabricated values and never runs in production. */
export class DisabledDevelopmentSource implements LiveDataSource<Snapshot> {
  name = "development-disabled-source";
  async healthCheck(): Promise<SourceHealth> { return { healthy: false, checkedAt: new Date().toISOString(), detail: "disabled" }; }
  async fetchSnapshot(input: SnapshotInput): Promise<Snapshot> { return { stream: input.stream, generatedAt: new Date().toISOString(), sequence: 0, signals: [], sourceConfigured: false }; }
  async *subscribe(): AsyncIterable<LiveEvent> { return; }
}
