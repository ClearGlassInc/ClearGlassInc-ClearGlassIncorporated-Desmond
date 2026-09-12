/* ClearGlass Visual Engine · Playwright headless-Chromium smoke test.
 *
 * Standalone (NOT a *.test.mjs) so the repo's `node --test` glob never requires
 * playwright-core in environments that don't have it. Run it explicitly:
 *
 *   CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
 *   NODE_PATH=<dir-with-playwright-core> \
 *   node assets/cg-visual/tests/browser-smoke.mjs
 *
 * It boots a tiny static server rooted at the repo, loads the wired homepage,
 * and asserts: content renders first; forced Canvas2D fallback works; the
 * reduced-motion profile activates (static, loop stopped); a simulated GPU
 * context-loss recovers; and an event flood does not crash the page. */

import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const CHROME = process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.ico': 'image/x-icon' };

function serve() {
  return new Promise((resolve) => {
    const srv = http.createServer((req, res) => {
      try {
        let p = decodeURIComponent(req.url.split('?')[0]);
        if (p === '/' ) p = '/index.html';
        const fp = path.join(ROOT, p);
        if (!fp.startsWith(ROOT) || !fs.existsSync(fp) || fs.statSync(fp).isDirectory()) { res.writeHead(404); res.end('nf'); return; }
        res.writeHead(200, { 'Content-Type': MIME[path.extname(fp)] || 'application/octet-stream' });
        fs.createReadStream(fp).pipe(res);
      } catch (e) { res.writeHead(500); res.end(String(e)); }
    });
    srv.listen(0, '127.0.0.1', () => resolve({ srv, port: srv.address().port }));
  });
}

const results = [];
function check(name, cond, detail) {
  results.push({ name, ok: !!cond, detail: detail || '' });
  console.log((cond ? 'PASS' : 'FAIL') + '  ' + name + (detail ? '  · ' + detail : ''));
}

async function main() {
  // ESM ignores NODE_PATH for bare specifiers, so allow an explicit path.
  const spec = process.env.CG_PW_CORE || 'playwright-core';
  const mod = await import(spec);
  const chromium = (mod.chromium) || (mod.default && mod.default.chromium);
  const { srv, port } = await serve();
  const base = `http://127.0.0.1:${port}`;
  const browser = await chromium.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--use-gl=swiftshader', '--enable-unsafe-swangle'] });

  try {
    // ── A: content renders first; engine self-initialises ──────────────────
    {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.goto(base + '/index.html?cgdebug=1', { waitUntil: 'domcontentloaded' });
      const hero = await page.locator('.cgm-display, h1, h2').first().innerText().catch(() => '');
      check('A1 homepage content renders (hero text present)', hero && hero.length > 4, JSON.stringify(hero.slice(0, 40)));
      await page.waitForFunction(() => window.__cgVisual && window.__cgVisual.engine && window.__cgVisual.engine.backend, null, { timeout: 8000 });
      const info = await page.evaluate(() => ({
        kind: window.__cgVisual.engine.backend.kind,
        canvas: !!document.querySelector('.cg-visual-stage .cg-visual-canvas'),
        detected: window.__cgVisual.detected,
      }));
      check('A2 backend initialised from the fallback chain', !!info.kind, 'backend=' + info.kind);
      check('A3 decorative canvas mounted beneath content', info.canvas);
      check('A4 no uncaught page errors on load', errors.length === 0, errors.join(' | '));
      await page.close();
    }

    // ── B: forced Canvas2D fallback ────────────────────────────────────────
    {
      const page = await browser.newPage();
      await page.goto(base + '/index.html?cgdebug=1&cgfault=forceCanvas', { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => window.__cgVisual && window.__cgVisual.engine && window.__cgVisual.engine.backend, null, { timeout: 8000 });
      const kind = await page.evaluate(() => window.__cgVisual.engine.backend.kind);
      check('B1 forced Canvas2D fallback active', kind === 'canvas2d', 'backend=' + kind);
      await page.close();
    }

    // ── C: reduced-motion profile ──────────────────────────────────────────
    {
      const ctx = await browser.newContext({ reducedMotion: 'reduce' });
      const page = await ctx.newPage();
      await page.goto(base + '/index.html?cgdebug=1', { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => window.__cgVisual && window.__cgVisual.engine && window.__cgVisual.engine.backend, null, { timeout: 8000 });
      const st = await page.evaluate(() => ({ reduced: window.__cgVisual.engine.reduced, running: window.__cgVisual.engine.running, frame: window.__cgVisual.engine.sim.world.frame }));
      check('C1 reduced-motion profile active', st.reduced === true);
      check('C2 animation loop stopped under reduced motion', st.running === false);
      check('C3 static profile still populated the world (info available)', st.frame > 0, 'frames=' + st.frame);
      await ctx.close();
    }

    // ── D: GPU context-loss recovery ───────────────────────────────────────
    {
      const page = await browser.newPage();
      await page.goto(base + '/index.html?cgdebug=1', { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => window.__cgVisual && window.__cgVisual.faults, null, { timeout: 8000 });
      const before = await page.evaluate(() => window.__cgVisual.engine.backend.kind);
      const recovered = await page.evaluate(async () => {
        await window.__cgVisual.faults.contextLoss();
        return { kind: window.__cgVisual.engine.backend && window.__cgVisual.engine.backend.kind, disposed: window.__cgVisual.engine._disposed };
      });
      check('D1 backend recovered after simulated context loss', !!recovered.kind && !recovered.disposed, 'before=' + before + ' after=' + recovered.kind);
      const alive = await page.evaluate(() => document.querySelector('.cgm-display, h1, h2') != null);
      check('D2 page content intact after recovery', alive);
      await page.close();
    }

    // ── E: event flood does not crash the page ─────────────────────────────
    {
      const page = await browser.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(String(e)));
      await page.goto(base + '/index.html?cgdebug=1&cgfault=floodEvents', { waitUntil: 'domcontentloaded' });
      await page.waitForFunction(() => window.__cgVisual && window.__cgVisual.engine, null, { timeout: 8000 });
      await page.waitForTimeout(1500); // let the flood run across many frames
      const st = await page.evaluate(() => ({
        queue: window.__cgVisual.engine.sim.queue.size,
        active: window.__cgVisual.engine.sim.pool.activeCount,
        cap: window.__cgVisual.engine.sim.pool.capacity,
        frame: window.__cgVisual.engine.sim.world.frame,
      }));
      check('E1 event queue stayed within its hard limit under flood', st.queue <= 256, 'queue=' + st.queue);
      check('E2 particle pool stayed within capacity under flood', st.active <= st.cap, st.active + '/' + st.cap);
      check('E3 render loop kept advancing under flood', st.frame > 10, 'frames=' + st.frame);
      check('E4 no uncaught page errors during flood', errors.length === 0, errors.join(' | '));
      await page.close();
    }
  } finally {
    await browser.close();
    srv.close();
  }

  const failed = results.filter((r) => !r.ok);
  console.log('\n' + (results.length - failed.length) + '/' + results.length + ' checks passed.');
  process.exit(failed.length ? 1 : 0);
}

main().catch((e) => { console.error('SMOKE HARNESS ERROR:', e); process.exit(2); });
