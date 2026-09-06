#!/usr/bin/env node
// Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
// Proprietary and confidential. See LICENSE for terms.
/**
 * Test entry point for `npm test`.
 *
 * Type-checks first, then compiles to `dist/` and runs the compiled suite with
 * node's built-in test runner. Compiling rather than transpiling on the fly
 * means `npm test` also proves the TypeScript is sound, so a type error cannot
 * reach CI green.
 *
 * Extra CLI arguments are ignored on purpose: callers in this repository invoke
 * it as `npm test -- --ci`, and a stray flag must not be mistaken for a file.
 */
import { spawnSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function step(command, args) {
  const result = spawnSync(command, args, { cwd: ROOT, stdio: "inherit", shell: process.platform === "win32" });
  if (result.error) {
    console.error(`failed to run ${command}: ${result.error.message}`);
    process.exit(1);
  }
  if (result.status !== 0) process.exit(result.status ?? 1);
}

const tsc = path.join(ROOT, "node_modules", ".bin", "tsc");
if (!existsSync(tsc)) {
  console.error(
    "TypeScript is not installed. Run `npm ci` first (this package keeps tsc in dependencies, " +
      "not devDependencies, so an NODE_ENV=production install still gets it).",
  );
  process.exit(1);
}

step(tsc, ["-p", "tsconfig.json"]);

const testDir = path.join(ROOT, "dist", "scripts", "stripe-sync", "tests");
const files = readdirSync(testDir)
  .filter((name) => name.endsWith(".test.js"))
  .map((name) => path.join(testDir, name))
  .sort();

if (files.length === 0) {
  console.error(`no compiled tests found in ${testDir}`);
  process.exit(1);
}

step(process.execPath, ["--test", ...files]);
