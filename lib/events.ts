import { fabricConfig } from "./config";
import { liveEventSchema, type LiveEvent } from "./contracts";

export class EventGuard {
  private readonly ids = new Set<string>();
  private readonly sequences = new Map<string, number>();
  validate(input: unknown): LiveEvent {
    const size = new TextEncoder().encode(JSON.stringify(input)).byteLength;
    if (size > fabricConfig.maxEventBytes) throw new Error("event payload exceeds configured limit");
    const event = liveEventSchema.parse(input);
    if (!fabricConfig.knownSources.has(event.source)) throw new Error("unknown event source");
    if (this.ids.has(event.id)) throw new Error("duplicate event");
    const scope = `${event.source}:${event.tenantId ?? "public"}:${event.type}`;
    const previous = this.sequences.get(scope);
    if (previous !== undefined && event.sequence <= previous) throw new Error("replayed or out-of-order event");
    this.ids.add(event.id); this.sequences.set(scope, event.sequence);
    if (this.ids.size > 10_000) this.ids.delete(this.ids.values().next().value as string);
    return event;
  }
}

export function encodeSse(event: LiveEvent): string {
  return `id: ${event.id}\nevent: ${event.type}\nretry: 5000\ndata: ${JSON.stringify(event)}\n\n`;
}
