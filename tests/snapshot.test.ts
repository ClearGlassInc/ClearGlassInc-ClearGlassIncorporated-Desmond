import assert from "node:assert/strict";
import test from "node:test";
import { DisabledDevelopmentSource } from "../lib/sources";

test("development adapter returns an explicit empty disabled snapshot", async () => { const snapshot = await new DisabledDevelopmentSource().fetchSnapshot({ stream: "public" }); assert.equal(snapshot.sourceConfigured, false); assert.deepEqual(snapshot.signals, []); assert.equal(snapshot.sequence, 0); });
test("development adapter never fabricates events", async () => { const source = new DisabledDevelopmentSource(); let count = 0; for await (const _event of source.subscribe({ stream: "public" })) count += 1; assert.equal(count, 0); });
