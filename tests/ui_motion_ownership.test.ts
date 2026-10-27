/* Regression: site navigation and cinematic CTAs must have one motion owner.
 * Runs the actual ui.js in a minimal DOM event harness (no extra dependencies). */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { runInNewContext } from "node:vm";

function setup() {
  const events = new Map<string, (event: unknown) => void>();
  const document = {
    readyState: "loading",
    addEventListener(event: string, callback: (event: unknown) => void) {
      events.set(event, callback);
    },
  };
  const window = {
    addEventListener() {},
    matchMedia(query: string) {
      return { matches: query.includes("(hover: hover)") };
    },
  };
  const source = readFileSync(join(process.cwd(), "ui.js"), "utf8");
  runInNewContext(source, { document, window }, { filename: "ui.js" });
  const pointerover = events.get("pointerover");
  assert.ok(pointerover, "fine-pointer controls should register the interaction handler");
  return pointerover;
}

function control(kind: "nav" | "cinematic" | "future" | "regular") {
  const classes = new Set(kind === "future" ? ["future-glass-primary"] : []);
  const listeners: string[] = [];
  const element = {
    disabled: false,
    getAttribute() { return null; },
    closest(selector: string) {
      if (selector.startsWith("button,.btn")) return element;
      return kind === "nav" && selector.includes("#navbar") ? element : null;
    },
    matches(selector: string) {
      return kind === "cinematic" && selector === ".cgm-btn[data-cgm-magnetic]";
    },
    classList: {
      contains(name: string) { return classes.has(name); },
      add(name: string) { classes.add(name); },
    },
    addEventListener(name: string) { listeners.push(name); },
  };
  return { element, classes, listeners };
}

test("homepage navbar remains controlled by its own navigation script", () => {
  const pointerover = setup();
  const nav = control("nav");
  pointerover({ target: nav.element });
  assert.equal(nav.classes.has("cg-magnetic"), false);
  assert.deepEqual(nav.listeners, []);
});

test("cinematic CTA receives no second magnetic transform", () => {
  const pointerover = setup();
  const cinematic = control("cinematic");
  pointerover({ target: cinematic.element });
  assert.equal(cinematic.classes.has("cg-magnetic"), false);
  assert.deepEqual(cinematic.listeners, []);
});

test("future-glass controls retain their separate motion owner", () => {
  const pointerover = setup();
  const future = control("future");
  pointerover({ target: future.element });
  assert.deepEqual(future.listeners, []);
});

test("ordinary buttons still receive the existing magnetic enhancement", () => {
  const pointerover = setup();
  const ordinary = control("regular");
  pointerover({ target: ordinary.element });
  assert.equal(ordinary.classes.has("cg-magnetic"), true);
  assert.deepEqual(ordinary.listeners, ["pointermove", "pointerleave"]);
});
