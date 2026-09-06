import { fabricConfig } from "./config";
import { snapshotSchema, type Snapshot, type StreamName } from "./contracts";
import { DisabledDevelopmentSource } from "./sources";

export async function getSnapshot(stream: StreamName): Promise<Snapshot> {
  const endpoint = process.env.LIVE_FABRIC_SNAPSHOT_URL;
  if (!fabricConfig.enabled || !endpoint) return new DisabledDevelopmentSource().fetchSnapshot({ stream });
  const response = await fetch(`${endpoint.replace(/\/$/, "")}/${stream}`, { headers: { Authorization: `Bearer ${process.env.LIVE_FABRIC_SNAPSHOT_TOKEN ?? ""}` }, cache: "no-store", signal: AbortSignal.timeout(5_000) });
  if (!response.ok) throw new Error("configured snapshot source unavailable");
  return snapshotSchema.parse(await response.json());
}
