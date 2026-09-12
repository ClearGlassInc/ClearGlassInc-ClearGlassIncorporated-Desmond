/* ClearGlass Visual Engine · render backend abstraction.
 *
 * Feature-detected graceful chain:  WebGPU -> WebGL2 -> Canvas2D -> static.
 * Every backend implements the SAME small interface so scenes are backend-
 * agnostic:
 *     resize(cssW, cssH, dpr)
 *     begin(alpha)                 // clear / start frame
 *     points(px, py, hot, count, {size, r,g,b})
 *     lines(segments, {r,g,b,a,width})   segments: [x1,y1,x2,y2,hot,...]
 *     end()
 *     dispose()
 *     kind
 *
 * Coordinates handed to the backend are normalised [0,1]; the backend maps to
 * device pixels. Buffers/pipelines are cached and only rebuilt on resize.
 * NO backend failure is allowed to reach the app: selectBackend() always
 * resolves to *something* (static as the floor). No eval, no remote code. */

const CRIMSON = { r: 0.918, g: 0.275, b: 0.282 };

/* ─────────────────────────── Canvas2D (always available fallback) ─────── */
export function createCanvas2DBackend(canvas) {
  let ctx;
  try { ctx = canvas.getContext('2d'); } catch (e) { ctx = null; }
  if (!ctx) return null;
  let w = 1, h = 1, s = 1;
  return {
    kind: 'canvas2d',
    resize(cssW, cssH, dpr) {
      s = dpr || 1; w = Math.max(1, cssW); h = Math.max(1, cssH);
      canvas.width = Math.round(w * s); canvas.height = Math.round(h * s);
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    },
    begin() { ctx.setTransform(s, 0, 0, s, 0, 0); ctx.clearRect(0, 0, w, h); },
    points(px, py, hot, count, opts) {
      const o = opts || {}; const size = o.size || 1.6;
      const base = 'rgba(' + Math.round((o.r ?? CRIMSON.r) * 255) + ',' + Math.round((o.g ?? CRIMSON.g) * 255) + ',' + Math.round((o.b ?? CRIMSON.b) * 255) + ',';
      for (let i = 0; i < count; i++) {
        const a = 0.28 + 0.55 * (hot ? hot[i] : 0.4);
        ctx.fillStyle = base + a.toFixed(3) + ')';
        ctx.beginPath();
        ctx.arc(px[i] * w, py[i] * h, size * (0.6 + (hot ? hot[i] : 0.4)), 0, 6.2832);
        ctx.fill();
      }
    },
    lines(seg, opts) {
      const o = opts || {};
      ctx.lineWidth = o.width || 1; ctx.lineCap = 'round';
      const col = 'rgba(' + Math.round((o.r ?? CRIMSON.r) * 255) + ',' + Math.round((o.g ?? CRIMSON.g) * 255) + ',' + Math.round((o.b ?? CRIMSON.b) * 255) + ',';
      for (let i = 0; i < seg.length; i += 5) {
        ctx.strokeStyle = col + ((o.a || 0.2) * (0.5 + seg[i + 4])).toFixed(3) + ')';
        ctx.beginPath(); ctx.moveTo(seg[i] * w, seg[i + 1] * h); ctx.lineTo(seg[i + 2] * w, seg[i + 3] * h); ctx.stroke();
      }
    },
    end() {},
    dispose() { try { ctx.clearRect(0, 0, w, h); } catch (e) {} canvas.width = canvas.height = 0; },
  };
}

/* ─────────────────────────── WebGL2 (instanced-ish point sprites) ─────── */
export function createWebGL2Backend(canvas) {
  let gl;
  try { gl = canvas.getContext('webgl2', { alpha: true, antialias: false, premultipliedAlpha: true, powerPreference: 'low-power' }); }
  catch (e) { gl = null; }
  if (!gl) return null;

  const vs = '#version 300 es\nlayout(location=0) in vec2 p;layout(location=1) in float hot;uniform float ps;out float vh;' +
    'void main(){vh=hot;gl_Position=vec4(p*2.0-1.0,0.0,1.0);gl_PointSize=ps*(0.6+hot);}';
  const fs = '#version 300 es\nprecision mediump float;in float vh;uniform vec3 col;out vec4 o;' +
    'void main(){vec2 d=gl_PointCoord-0.5;float m=smoothstep(0.5,0.0,length(d));o=vec4(col,(0.28+0.55*vh)*m);}';
  const lvs = '#version 300 es\nlayout(location=0) in vec2 p;layout(location=1) in float hot;out float vh;void main(){vh=hot;gl_Position=vec4(p*2.0-1.0,0.0,1.0);}';
  const lfs = '#version 300 es\nprecision mediump float;in float vh;uniform vec3 col;uniform float a;out vec4 o;void main(){o=vec4(col,a*(0.5+vh));}';

  function sh(t, src) { const s = gl.createShader(t); gl.shaderSource(s, src); gl.compileShader(s); return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null; }
  function prog(v, f) { const p = gl.createProgram(); const a = sh(gl.VERTEX_SHADER, v), b = sh(gl.FRAGMENT_SHADER, f); if (!a || !b) return null; gl.attachShader(p, a); gl.attachShader(p, b); gl.linkProgram(p); return gl.getProgramParameter(p, gl.LINK_STATUS) ? p : null; }

  const pPoints = prog(vs, fs), pLines = prog(lvs, lfs);
  if (!pPoints || !pLines) return null;

  // Reused dynamic buffers (grown once to a ceiling, never per-frame).
  const CAP = 6000;
  const pointData = new Float32Array(CAP * 3);   // x,y,hot interleaved
  const lineData = new Float32Array(CAP * 3);
  const vboP = gl.createBuffer(), vboL = gl.createBuffer();
  let w = 1, h = 1, s = 1, ps = 3;

  function bindInterleaved(vbo, data, n) {
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, data.subarray(0, n * 3), gl.DYNAMIC_DRAW);
    gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 12, 0);
    gl.enableVertexAttribArray(1); gl.vertexAttribPointer(1, 1, gl.FLOAT, false, 12, 8);
  }

  return {
    kind: 'webgl2',
    gl,
    resize(cssW, cssH, dpr) {
      s = dpr || 1; w = Math.max(1, cssW); h = Math.max(1, cssH);
      canvas.width = Math.round(w * s); canvas.height = Math.round(h * s);
      canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
      gl.viewport(0, 0, canvas.width, canvas.height);
      ps = Math.max(2, canvas.height * 0.004);
    },
    begin() {
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    },
    points(px, py, hot, count, opts) {
      const o = opts || {}; const n = Math.min(count, CAP);
      for (let i = 0; i < n; i++) { pointData[i * 3] = px[i]; pointData[i * 3 + 1] = 1 - py[i]; pointData[i * 3 + 2] = hot ? hot[i] : 0.4; }
      gl.useProgram(pPoints);
      bindInterleaved(vboP, pointData, n);
      gl.uniform1f(gl.getUniformLocation(pPoints, 'ps'), ps);
      gl.uniform3f(gl.getUniformLocation(pPoints, 'col'), o.r ?? CRIMSON.r, o.g ?? CRIMSON.g, o.b ?? CRIMSON.b);
      gl.drawArrays(gl.POINTS, 0, n);
    },
    lines(seg, opts) {
      const o = opts || {}; const pairs = Math.min((seg.length / 5) | 0, CAP / 2);
      let j = 0;
      for (let i = 0; i < pairs; i++) {
        const b = i * 5;
        lineData[j++] = seg[b]; lineData[j++] = 1 - seg[b + 1]; lineData[j++] = seg[b + 4];
        lineData[j++] = seg[b + 2]; lineData[j++] = 1 - seg[b + 3]; lineData[j++] = seg[b + 4];
      }
      gl.useProgram(pLines);
      bindInterleaved(vboL, lineData, pairs * 2);
      gl.uniform3f(gl.getUniformLocation(pLines, 'col'), o.r ?? CRIMSON.r, o.g ?? CRIMSON.g, o.b ?? CRIMSON.b);
      gl.uniform1f(gl.getUniformLocation(pLines, 'a'), o.a || 0.2);
      gl.drawArrays(gl.LINES, 0, pairs * 2);
    },
    end() {},
    dispose() {
      try {
        gl.deleteBuffer(vboP); gl.deleteBuffer(vboL);
        gl.deleteProgram(pPoints); gl.deleteProgram(pLines);
        const lose = gl.getExtension('WEBGL_lose_context'); if (lose) lose.loseContext();
      } catch (e) {}
    },
  };
}

/* ─────────────────────────── WebGPU (best-effort progressive enhancement) ─
   Real device validation/timing needs GPU hardware not present in CI, so this
   path is guarded end-to-end and is documented as NOT VERIFIED. Any failure
   at any step returns null and the chain falls through to WebGL2. */
export async function createWebGPUBackend(canvas) {
  try {
    if (typeof navigator === 'undefined' || !navigator.gpu) return null;
    const adapter = await navigator.gpu.requestAdapter({ powerPreference: 'low-power' });
    if (!adapter) return null;
    const device = await adapter.requestDevice();
    if (!device) return null;
    const ctx = canvas.getContext('webgpu');
    if (!ctx) return null;
    const format = navigator.gpu.getPreferredCanvasFormat();
    ctx.configure({ device, format, alphaMode: 'premultiplied' });

    const shader = device.createShaderModule({
      code: `
        struct VOut { @builtin(position) pos: vec4f, @location(0) hot: f32 };
        @vertex fn vmain(@location(0) p: vec2f, @location(1) hot: f32) -> VOut {
          var o: VOut; o.pos = vec4f(p * 2.0 - 1.0, 0.0, 1.0); o.hot = hot; return o;
        }
        @fragment fn fmain(in: VOut) -> @location(0) vec4f {
          return vec4f(0.918, 0.275, 0.282, 0.4 + 0.5 * in.hot);
        }`,
    });
    const pipeline = device.createRenderPipeline({
      layout: 'auto',
      vertex: { module: shader, entryPoint: 'vmain', buffers: [{ arrayStride: 12, attributes: [{ shaderLocation: 0, offset: 0, format: 'float32x2' }, { shaderLocation: 1, offset: 8, format: 'float32' }] }] },
      fragment: { module: shader, entryPoint: 'fmain', targets: [{ format, blend: { color: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' }, alpha: { srcFactor: 'one', dstFactor: 'one-minus-src-alpha' } } }] },
      primitive: { topology: 'point-list' },
    });

    const CAP = 6000;
    const staging = new Float32Array(CAP * 3);
    const vbuf = device.createBuffer({ size: staging.byteLength, usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST });
    let s = 1;

    return {
      kind: 'webgpu',
      device,
      resize(cssW, cssH, dpr) {
        s = dpr || 1;
        canvas.width = Math.max(1, Math.round(cssW * s));
        canvas.height = Math.max(1, Math.round(cssH * s));
        canvas.style.width = cssW + 'px'; canvas.style.height = cssH + 'px';
      },
      begin() { this._enc = device.createCommandEncoder(); this._view = ctx.getCurrentTexture().createView(); this._n = 0; },
      points(px, py, hot, count) {
        const n = Math.min(count, CAP);
        for (let i = 0; i < n; i++) { staging[i * 3] = px[i]; staging[i * 3 + 1] = 1 - py[i]; staging[i * 3 + 2] = hot ? hot[i] : 0.4; }
        device.queue.writeBuffer(vbuf, 0, staging, 0, n * 3);
        this._n = n;
      },
      lines() { /* WebGPU path draws points only in this progressive tier */ },
      end() {
        const pass = this._enc.beginRenderPass({ colorAttachments: [{ view: this._view, clearValue: { r: 0, g: 0, b: 0, a: 0 }, loadOp: 'clear', storeOp: 'store' }] });
        if (this._n > 0) { pass.setPipeline(pipeline); pass.setVertexBuffer(0, vbuf); pass.draw(this._n); }
        pass.end();
        device.queue.submit([this._enc.finish()]);
      },
      dispose() { try { vbuf.destroy(); device.destroy(); } catch (e) {} },
    };
  } catch (e) { return null; }
}

/* ─────────────────────────── static (the floor — one paint, no animation) ─ */
export function createStaticBackend(canvas) {
  let ctx; try { ctx = canvas.getContext('2d'); } catch (e) { ctx = null; }
  let w = 1, h = 1;
  return {
    kind: 'static',
    resize(cssW, cssH, dpr) { const s = dpr || 1; w = cssW; h = cssH; if (ctx) { canvas.width = cssW * s; canvas.height = cssH * s; canvas.style.width = cssW + 'px'; canvas.style.height = cssH + 'px'; ctx.setTransform(s, 0, 0, s, 0, 0); } },
    begin() { if (ctx) { ctx.clearRect(0, 0, w, h); const g = ctx.createLinearGradient(0, 0, w, h); g.addColorStop(0, 'rgba(234,70,72,0.06)'); g.addColorStop(1, 'rgba(234,70,72,0.0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h); } },
    points() {}, lines() {}, end() {}, dispose() {},
  };
}

/** Detect available backends without instantiating heavy contexts. */
export function detectBackends() {
  const out = { webgpu: false, webgl2: false, canvas2d: false };
  try { out.webgpu = typeof navigator !== 'undefined' && !!navigator.gpu; } catch (e) {}
  try {
    if (typeof document !== 'undefined') {
      const c = document.createElement('canvas');
      out.webgl2 = !!c.getContext('webgl2');
      out.canvas2d = !!c.getContext('2d');
    }
  } catch (e) {}
  return out;
}

/**
 * Walk the fallback chain and return the first backend that initialises.
 * @param {HTMLCanvasElement} canvas
 * @param {object} opts {forced:'webgl2'|'canvas2d'|'static', allowWebGPU:boolean}
 */
export async function selectBackend(canvas, opts = {}) {
  const forced = opts.forced;
  const tryOrder = forced ? [forced] : ['webgpu', 'webgl2', 'canvas2d', 'static'];
  for (const kind of tryOrder) {
    let be = null;
    try {
      if (kind === 'webgpu') { if (opts.allowWebGPU === false) continue; be = await createWebGPUBackend(canvas); }
      else if (kind === 'webgl2') be = createWebGL2Backend(canvas);
      else if (kind === 'canvas2d') be = createCanvas2DBackend(canvas);
      else if (kind === 'static') be = createStaticBackend(canvas);
    } catch (e) { be = null; }
    if (be) return be;
  }
  // Absolute floor: static is constructed even if 2d context is missing.
  return createStaticBackend(canvas);
}
