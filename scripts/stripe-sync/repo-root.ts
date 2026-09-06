// Copyright (c) 2024-2026 ClearGlass Inc. All Rights Reserved.
// Proprietary and confidential. See LICENSE for terms.
/**
 * Locate the repository root from wherever this module happens to be running.
 *
 * The same code runs from two places: `scripts/…` under tsx, and
 * `dist/scripts/…` after compilation. A fixed number of `..` hops is correct in
 * exactly one of them, so the root is found by walking up to the nearest
 * directory holding `package.json` instead.
 */
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export function findRepoRoot(startUrl: string): string {
  let directory = path.dirname(fileURLToPath(startUrl));
  for (;;) {
    if (existsSync(path.join(directory, "package.json"))) return directory;
    const parent = path.dirname(directory);
    if (parent === directory) {
      throw new Error(`could not locate the repository root above ${fileURLToPath(startUrl)}`);
    }
    directory = parent;
  }
}
