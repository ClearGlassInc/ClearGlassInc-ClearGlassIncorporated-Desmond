import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = fileURLToPath(new URL("../", import.meta.url));

function projectConfig(directory: string) {
  const config = ts.readConfigFile(path.join(directory, "tsconfig.json"), ts.sys.readFile);
  assert.equal(config.error, undefined);
  const parsed = ts.parseJsonConfigFileContent(
    config.config, ts.sys, directory, undefined, path.join(directory, "tsconfig.json")
  );
  assert.deepEqual(parsed.errors, []);
  return parsed;
}

test("root compilation keeps the Chualar API and respects the standalone Delos project", () => {
  const rootConfig = projectConfig(root);
  const delosRoot = path.join(root, "delos-os");
  const delosPage = path.join(delosRoot, "app/page.tsx");

  assert.ok(rootConfig.fileNames.includes(path.join(root, "app/api/live/ops/route.ts")));
  assert.equal(rootConfig.fileNames.includes(delosPage), false,
    "Delos must use its own Next.js dependencies and compiler configuration");
  assert.ok(projectConfig(delosRoot).fileNames.includes(delosPage),
    "the Delos page must remain covered by its own TypeScript project");
});

test("the Chualar response error map compiles with the root TypeScript project", () => {
  const config = projectConfig(root);
  const program = ts.createProgram(config.fileNames, config.options);
  const route = program.getSourceFile(path.join(root, "app/api/live/ops/route.ts"));
  assert.ok(route, "the API route must remain part of root validation");
  const diagnostics = ts.getPreEmitDiagnostics(program, route);
  assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCurrentDirectory: () => root,
    getCanonicalFileName: fileName => fileName,
    getNewLine: () => "\n"
  }));
});
