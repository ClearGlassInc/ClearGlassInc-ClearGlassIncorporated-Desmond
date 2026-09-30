/* ClearGlass Truth Forensics — analysis worker.
 *
 * Hashing and parsing run here so a large file never blocks the page. The
 * worker receives bytes the page already holds, runs the same engine, and
 * returns the record and analysis. It makes no network request.
 */
/* global importScripts, ClearGlassTruthForensics */
importScripts('/assets/js/truth-forensics-engine.js');

var E = self.ClearGlassTruthForensics;

self.onmessage = async function (ev) {
  var m = ev.data || {};
  var t0 = self.performance ? self.performance.now() : Date.now();
  try {
    var bytes = new Uint8Array(m.buffer);
    var record = await E.acquireBytes(bytes, m.options);
    var analysable = bytes.length <= m.maxAnalysis;
    if (!analysable) record.processing_boundary = 'HASH_ONLY';
    var analysis = await E.analyzeItem(record, analysable ? bytes : null);
    self.postMessage({ id: m.id, ok: true, record: record, analysis: analysis,
      duration_ms: Math.round((self.performance ? self.performance.now() : Date.now()) - t0) });
  } catch (e) {
    self.postMessage({ id: m.id, ok: false, error: String((e && e.message) || e) });
  }
};
