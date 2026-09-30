/* ClearGlass Truth Forensics — browser engine.
 *
 * A function-for-function port of the Python reference engine in
 * truth_forensics/. It is pure (no DOM), runs in any modern browser and in
 * Node 18+, and never makes a network request: evidence stays on the device
 * that opened the page.
 *
 * Parity: tests/test_truth_forensics_parity.py runs this file in Node against
 * the demonstration corpus and requires byte-identical canonical JSON with
 * the Python engine (telemetry aside). Change one engine, change both.
 *
 * Output never contains floats and never claims more than the rules show.
 * It provides analytical indicators and provenance analysis; it does not
 * establish the truth of real-world events.
 */
(function (root, factory) {
  'use strict';
  var api = factory();
  if (typeof module === 'object' && module.exports) { module.exports = api; }
  else { root.ClearGlassTruthForensics = api; }
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ------------------------------------------------------------------
  // vocabulary (truth_forensics/vocab.py)
  // ------------------------------------------------------------------
  var V = {
    ENGINE_NAME: 'clearglass-truth-forensics',
    ENGINE_VERSION: '1.0.0',
    CASE_SCHEMA: 'clearglass.truth-forensics.case/1',
    RESULT_SCHEMA: 'clearglass.truth-forensics.result/1',
    VERIFIED: 'VERIFIED', SUPPORTED: 'SUPPORTED', INCONCLUSIVE: 'INCONCLUSIVE',
    UNVERIFIED: 'UNVERIFIED', SIMULATED: 'SIMULATED',
    PARTIALLY_SUPPORTED: 'PARTIALLY_SUPPORTED', CONTRADICTED: 'CONTRADICTED',
    NORMAL: 'NORMAL', REVIEW_REQUIRED: 'REVIEW_REQUIRED', ANOMALY_DETECTED: 'ANOMALY_DETECTED',
    CORROBORATION_CONFLICT: 'CORROBORATION_CONFLICT', PROVENANCE_GAP: 'PROVENANCE_GAP',
    CRYPTOGRAPHICALLY_VERIFIED: 'CRYPTOGRAPHICALLY_VERIFIED',
    ORIGINAL: 'ORIGINAL', DERIVATIVE: 'DERIVATIVE', ANALYSIS_RESULT: 'ANALYSIS_RESULT',
    FACTUAL: 'FACTUAL', INFERENCE: 'INFERENCE'
  };
  V.EVIDENCE_STATUSES = [V.VERIFIED, V.SUPPORTED, V.INCONCLUSIVE, V.UNVERIFIED, V.SIMULATED];
  V.CLAIM_VERDICTS = [V.SUPPORTED, V.PARTIALLY_SUPPORTED, V.CONTRADICTED, V.INCONCLUSIVE, V.UNVERIFIED];
  V.STATES = [V.NORMAL, V.REVIEW_REQUIRED, V.ANOMALY_DETECTED, V.CORROBORATION_CONFLICT,
    V.PROVENANCE_GAP, V.INCONCLUSIVE, V.CRYPTOGRAPHICALLY_VERIFIED];
  V.JOB_STATES = ['QUEUED', 'PROCESSING', 'ANALYZING', 'REVIEW_REQUIRED', 'COMPLETE', 'FAILED'];
  V.CONFIDENCE = ['NONE', 'LOW', 'MODERATE', 'HIGH'];
  V.CATEGORIES = ['SPATIAL', 'TEMPORAL', 'SYNTHETIC', 'AUDIO', 'METADATA', 'CONTAINER', 'PROVENANCE'];
  V.STATEMENT_KINDS = ['OBSERVATION', 'INTERPRETATION', 'CONCLUSION'];
  V.PIPELINE = ['SOURCE', 'ACQUISITION', 'HASH', 'PROVENANCE', 'METADATA', 'CONTENT_ANALYSIS',
    'TEMPORAL_ANALYSIS', 'CROSS_SOURCE_CORRELATION', 'MANIPULATION_INDICATORS',
    'CONFIDENCE_ASSESSMENT', 'EVIDENCE_GRAPH', 'AUDIT_RECORD', 'HUMAN_REVIEW'];
  V.DISCLAIMER = 'The ClearGlass Truth Forensics system provides analytical indicators and provenance ' +
    'analysis. It does not independently establish the truth of real-world events and should ' +
    'not replace qualified forensic, legal, investigative, or evidentiary review.';
  V.BIFOCAL_DISCLAIMER = 'This score is an analytical heuristic and is not proof of authenticity.';
  V.CRYPTO_NOTE = 'Cryptographic verification proves integrity relative to a known hash or signature. ' +
    'It does not prove that the content depicts what it claims to depict.';
  V.INDICATORS_FOUND = 'Manipulation indicators detected; human review required.';
  V.NO_INDICATORS = 'No manipulation indicators detected by the available analyzers. Authenticity ' +
    'cannot be established solely from this analysis.';
  V.DEMO_LABEL = 'DEMONSTRATION DATA — NOT REAL EVIDENCE';
  var VER = V.ENGINE_VERSION;

  // ------------------------------------------------------------------
  // Python-compatible helpers
  // ------------------------------------------------------------------
  function StructError() { this.name = 'StructError'; this.message = 'structure truncated'; }
  StructError.prototype = Object.create(Error.prototype);
  function ParseError(msg) { this.name = 'ParseError'; this.message = msg; }
  ParseError.prototype = Object.create(Error.prototype);
  function IntakeError(msg) { this.name = 'IntakeError'; this.message = msg; }
  IntakeError.prototype = Object.create(Error.prototype);
  function CaseError(msg) { this.name = 'CaseError'; this.message = msg; }
  CaseError.prototype = Object.create(Error.prototype);
  function ReviewError(msg) { this.name = 'ReviewError'; this.message = msg; }
  ReviewError.prototype = Object.create(Error.prototype);
  function LanguageError(msg) { this.name = 'LanguageError'; this.message = msg; }
  LanguageError.prototype = Object.create(Error.prototype);

  function parseMessage(e) { return (e && e.name === 'ParseError') ? e.message : 'structure truncated'; }

  // Python's str.strip()/split() whitespace set.
  var PY_WS = '\\t\\n\\x0b\\x0c\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
  var RE_LSTRIP = new RegExp('^[' + PY_WS + ']+');
  var RE_RSTRIP = new RegExp('[' + PY_WS + ']+$');
  var RE_WS_SPLIT = new RegExp('[' + PY_WS + ']+');
  function pyStrip(s) { return String(s).replace(RE_LSTRIP, '').replace(RE_RSTRIP, ''); }
  function pyLstrip(s) { return String(s).replace(RE_LSTRIP, ''); }
  function pySplitWs(s) { return String(s).split(RE_WS_SPLIT).filter(function (x) { return x !== ''; }); }
  function stripChars(s, chars) {
    var a = 0, b = s.length;
    while (a < b && chars.indexOf(s[a]) >= 0) a++;
    while (b > a && chars.indexOf(s[b - 1]) >= 0) b--;
    return s.slice(a, b);
  }
  var SURROGATE = /[\ud800-\udfff]/;
  function pySlice(s, n) { return SURROGATE.test(s) ? Array.from(s).slice(0, n).join('') : s.slice(0, n); }
  function pyLen(s) { return SURROGATE.test(s) ? Array.from(s).length : s.length; }
  function pyStr(v) {
    if (v === null || v === undefined) return 'None';
    if (v === true) return 'True';
    if (v === false) return 'False';
    if (Array.isArray(v)) return '[' + v.map(pyStr).join(', ') + ']';
    return String(v);
  }
  function pad(n, w) { var s = String(Math.abs(n)); while (s.length < w) s = '0' + s; return (n < 0 ? '-' : '') + s; }
  function fdiv(a, b) { return Math.floor(a / b); }
  function quote(v) { return "'" + String(v).replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'"; }
  function latin1(u8, a, b) {
    var s = '';
    a = a || 0; b = (b === undefined) ? u8.length : Math.min(b, u8.length);
    for (var i = a; i < b; i += 8192) {
      s += String.fromCharCode.apply(null, u8.subarray(i, Math.min(b, i + 8192)));
    }
    return s;
  }
  function utf8(u8) { return new TextDecoder('utf-8').decode(u8); }
  function utf8Strict(u8) { return new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(u8); }
  function indexOfByte(u8, byte, from) { return u8.indexOf(byte, from); }
  function startsWith(u8, arr) {
    if (u8.length < arr.length) return false;
    for (var i = 0; i < arr.length; i++) if (u8[i] !== arr[i]) return false;
    return true;
  }
  function bytesOf(str) { var a = new Uint8Array(str.length); for (var i = 0; i < str.length; i++) a[i] = str.charCodeAt(i) & 0xff; return a; }
  function eqBytes(u8, off, str) {
    if (off + str.length > u8.length) return false;
    for (var i = 0; i < str.length; i++) if (u8[off + i] !== str.charCodeAt(i)) return false;
    return true;
  }
  function concat(chunks, total) {
    var out = new Uint8Array(total), p = 0;
    for (var i = 0; i < chunks.length; i++) { out.set(chunks[i], p); p += chunks[i].length; }
    return out;
  }
  function sortedKeys(o) { return Object.keys(o).sort(); }
  function strCmp(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function tupleCmp(a, b) {
    for (var i = 0; i < a.length; i++) { var c = a[i] < b[i] ? -1 : a[i] > b[i] ? 1 : 0; if (c) return c; }
    return 0;
  }
  function uniqSorted(arr) { return Array.from(new Set(arr)).sort(strCmp); }

  // Bounds-checked reader over a byte view: a short read throws StructError,
  // the same class of failure as Python's struct.error.
  function Reader(u8) { this.b = u8; this.n = u8.length; this.dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength); }
  Reader.prototype.need = function (o, k) { if (o < 0 || o + k > this.n) throw new StructError(); };
  Reader.prototype.u8 = function (o) { this.need(o, 1); return this.b[o]; };
  Reader.prototype.u16 = function (o, le) { this.need(o, 2); return this.dv.getUint16(o, !!le); };
  Reader.prototype.i16 = function (o, le) { this.need(o, 2); return this.dv.getInt16(o, !!le); };
  Reader.prototype.u32 = function (o, le) { this.need(o, 4); return this.dv.getUint32(o, !!le); };
  Reader.prototype.i32 = function (o, le) { this.need(o, 4); return this.dv.getInt32(o, !!le); };
  Reader.prototype.f32 = function (o, le) { this.need(o, 4); return this.dv.getFloat32(o, !!le); };
  Reader.prototype.u64 = function (o) { this.need(o, 8); return Number(this.dv.getBigUint64(o, false)); };
  Reader.prototype.i64 = function (o) { this.need(o, 8); return Number(this.dv.getBigInt64(o, false)); };

  // CRC-32 (IEEE), as zlib.crc32.
  var CRC_TABLE = (function () {
    var t = new Uint32Array(256);
    for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1); t[n] = c >>> 0; }
    return t;
  })();
  function crc32(parts) {
    var c = 0xFFFFFFFF;
    for (var p = 0; p < parts.length; p++) {
      var u8 = parts[p];
      for (var i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 0xff] ^ (c >>> 8);
    }
    return (c ^ 0xFFFFFFFF) >>> 0;
  }

  // Canonical JSON: sorted keys, no whitespace, ASCII-escaped — identical to
  // json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=True).
  function jsonStr(s) {
    return JSON.stringify(s).replace(/[\u0080-￿]/g, function (c) {
      return '\\u' + ('000' + c.charCodeAt(0).toString(16)).slice(-4);
    });
  }
  function canonicalJson(v) {
    if (v === null || v === undefined) return 'null';
    if (v === true) return 'true';
    if (v === false) return 'false';
    if (typeof v === 'number') {
      if (!isFinite(v)) throw new Error('non-finite number in canonical JSON');
      return Number.isInteger(v) ? String(v) : JSON.stringify(v);
    }
    if (typeof v === 'string') return jsonStr(v);
    if (Array.isArray(v)) return '[' + v.map(canonicalJson).join(',') + ']';
    var keys = sortedKeys(v).filter(function (k) { return v[k] !== undefined; });
    return '{' + keys.map(function (k) { return jsonStr(k) + ':' + canonicalJson(v[k]); }).join(',') + '}';
  }
  function hex(buf) {
    var u8 = new Uint8Array(buf), s = '';
    for (var i = 0; i < u8.length; i++) s += (u8[i] < 16 ? '0' : '') + u8[i].toString(16);
    return s;
  }
  function subtle() {
    var c = (typeof globalThis !== 'undefined' && globalThis.crypto) || null;
    if (!c || !c.subtle) throw new Error('WebCrypto (crypto.subtle) is unavailable; open this page over HTTPS');
    return c.subtle;
  }
  async function sha256Bytes(u8) { return hex(await subtle().digest('SHA-256', u8)); }
  async function sha256Text(s) { return sha256Bytes(new TextEncoder().encode(s)); }
  async function digest(o) { return sha256Text(canonicalJson(o)); }
  function pct(n, d) { return d <= 0 ? null : fdiv(200 * n + d, 2 * d); }
  var GENESIS_HASH = '0000000000000000000000000000000000000000000000000000000000000000';

  // zlib inflate with an output cap (a decompression-bomb guard).
  async function inflate(u8, cap) {
    if (typeof DecompressionStream === 'undefined') return { data: new Uint8Array(0), more: false, error: true };
    var ds = new DecompressionStream('deflate');
    var writer = ds.writable.getWriter();
    var reader = ds.readable.getReader();
    writer.write(u8).then(function () { return writer.close(); }).catch(function () {});
    var chunks = [], total = 0, more = false, error = false;
    try {
      for (;;) {
        var r = await reader.read();
        if (r.done) break;
        chunks.push(r.value); total += r.value.length;
        if (total > cap) { more = true; reader.cancel().catch(function () {}); break; }
      }
    } catch (e) { error = true; }
    var all = concat(chunks, total);
    return { data: all.subarray(0, Math.min(total, cap)), total: total, more: more, error: error };
  }

  // ------------------------------------------------------------------
  // indicators (truth_forensics/indicators.py)
  // ------------------------------------------------------------------
  var EDITOR_NAMES = ['photoshop', 'lightroom', 'gimp', 'affinity', 'pixelmator', 'snapseed', 'facetune',
    'canva', 'picsart', 'paint.net', 'darktable', 'capture one', 'luminar', 'photopea',
    'premiere', 'after effects', 'davinci', 'final cut', 'imovie', 'capcut', 'handbrake',
    'lavf', 'ffmpeg', 'audacity', 'adobe audition'];
  var GENERATOR_NAMES = ['dall-e', 'dall·e', 'midjourney', 'stable diffusion', 'firefly', 'imagen',
    'novelai', 'comfyui', 'automatic1111', 'sora', 'runway', 'elevenlabs'];

  function Indicator(f) {
    var need = ['code', 'title', 'evidence', 'method', 'limitation', 'analyzer'];
    for (var i = 0; i < need.length; i++) {
      if (!pyStrip(f[need[i]] || '')) throw new Error('indicator ' + (f.code || '?') + ' has no ' + need[i]);
    }
    if (!f.alternatives || !f.alternatives.length) throw new Error('indicator ' + f.code + ' lists no alternative explanation');
    if (V.CATEGORIES.indexOf(f.category) < 0) throw new Error('unknown category ' + f.category);
    if (['LOW', 'MODERATE', 'HIGH'].indexOf(f.confidence) < 0) throw new Error('indicator confidence must be LOW, MODERATE or HIGH: ' + f.confidence);
    if (V.STATES.indexOf(f.state) < 0) throw new Error('unknown state ' + f.state);
    return {
      finding_id: f.finding_id || '', code: f.code, category: f.category, title: f.title,
      evidence: f.evidence, method: f.method, confidence: f.confidence, limitation: f.limitation,
      alternatives: f.alternatives.slice(), state: f.state, analyzer: f.analyzer, location: f.location || ''
    };
  }
  function matchNames(text, names) {
    var low = String(text).toLowerCase();
    return names.filter(function (n) { return low.indexOf(n) >= 0; });
  }
  function softwareIndicators(field, value, analyzer) {
    var out = [];
    var gens = matchNames(value, GENERATOR_NAMES);
    if (gens.length) {
      out.push(Indicator({
        code: 'SYNTHETIC.GENERATOR_TAG', category: 'SYNTHETIC',
        title: 'Metadata names a generative-media tool',
        evidence: field + ' = ' + quote(value) + ' (matched: ' + gens.join(', ') + ')',
        method: 'Case-insensitive match of software metadata against a list of generator names.',
        confidence: 'MODERATE',
        limitation: 'Metadata can be written, copied or removed by anyone. A tag is not proof of ' +
          'generation, and its absence is not evidence of capture.',
        alternatives: ['A captured file re-saved through the named tool', 'Metadata copied from another file'],
        state: V.REVIEW_REQUIRED, analyzer: analyzer
      }));
    }
    var eds = matchNames(value, EDITOR_NAMES);
    if (eds.length) {
      out.push(Indicator({
        code: 'METADATA.EDITING_SOFTWARE', category: 'METADATA',
        title: 'File was last written by editing or transcoding software',
        evidence: field + ' = ' + quote(value) + ' (matched: ' + eds.join(', ') + ')',
        method: 'Case-insensitive match of software metadata against a list of editor names.',
        confidence: 'MODERATE',
        limitation: 'Shows which program wrote the file, not what it changed. Routine export, ' +
          'resizing and platform transcoding produce the same tag.',
        alternatives: ['Routine export or colour correction', 'Platform or messaging-app transcoding',
          'Format conversion for storage'],
        state: V.REVIEW_REQUIRED, analyzer: analyzer
      }));
    }
    return out;
  }
  function trailingDataIndicator(extra, marker, analyzer) {
    return Indicator({
      code: 'CONTAINER.TRAILING_DATA', category: 'CONTAINER',
      title: 'Data present after the ' + marker + ' end marker',
      evidence: extra + ' byte(s) follow the ' + marker + ' marker',
      method: 'Structural parse of the container to its end-of-image marker.',
      confidence: 'HIGH',
      limitation: 'The trailing bytes are counted, not analysed. Their content and origin are unknown.',
      alternatives: ['Vendor trailer (for example a motion-photo video or depth map)',
        'Appended data from a later tool', 'Incomplete overwrite of a longer file'],
      state: V.REVIEW_REQUIRED, analyzer: analyzer
    });
  }
  function parseErrorIndicator(detail, analyzer) {
    return Indicator({
      code: 'CONTAINER.PARSE_ERROR', category: 'CONTAINER',
      title: 'Container could not be fully parsed', evidence: detail,
      method: 'Bounds-checked structural parse; parsing stopped at the first inconsistency.',
      confidence: 'HIGH',
      limitation: 'Analysis after the failure point did not run. Results are incomplete.',
      alternatives: ['Truncated transfer or storage corruption',
        'A format variant this analyzer does not support', 'Deliberately malformed input'],
      state: V.INCONCLUSIVE, analyzer: analyzer
    });
  }
  function assignFindingIds(eid, inds) {
    var seen = {};
    return inds.map(function (ind) {
      seen[ind.code] = (seen[ind.code] || 0) + 1;
      var suffix = seen[ind.code] === 1 ? '' : '~' + seen[ind.code];
      var out = Object.assign({}, ind);
      out.finding_id = eid + '#' + ind.code + suffix;
      return out;
    });
  }

  // ------------------------------------------------------------------
  // intake (truth_forensics/intake.py)
  // ------------------------------------------------------------------
  var MAX_EVIDENCE_BYTES = 512 * 1024 * 1024;
  var HASH_ONLY_TYPES = ['application/x-executable', 'application/x-dosexec', 'application/x-mach-binary',
    'application/zip', 'application/gzip', 'application/x-7z-compressed',
    'application/x-rar-compressed', 'application/x-sh'];

  function sniffMime(head) {
    if (startsWith(head, [0xFF, 0xD8, 0xFF])) return 'image/jpeg';
    if (startsWith(head, [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])) return 'image/png';
    if (eqBytes(head, 0, 'GIF87a') || eqBytes(head, 0, 'GIF89a')) return 'image/gif';
    if (eqBytes(head, 0, 'RIFF') && head.length >= 12) {
      if (eqBytes(head, 8, 'WEBP')) return 'image/webp';
      if (eqBytes(head, 8, 'WAVE')) return 'audio/wav';
      if (eqBytes(head, 8, 'AVI ')) return 'video/x-msvideo';
    }
    if (head.length >= 12 && eqBytes(head, 4, 'ftyp')) {
      if (eqBytes(head, 8, 'qt  ')) return 'video/quicktime';
      if (eqBytes(head, 8, 'M4A ') || eqBytes(head, 8, 'M4B ')) return 'audio/mp4';
      return 'video/mp4';
    }
    if (startsWith(head, [0x1A, 0x45, 0xDF, 0xA3])) return 'video/webm';
    if (eqBytes(head, 0, 'ID3') || (head.length >= 2 && head[0] === 0xFF && (head[1] & 0xE0) === 0xE0 && (head[1] & 0x06) !== 0)) return 'audio/mpeg';
    if (eqBytes(head, 0, 'fLaC')) return 'audio/flac';
    if (eqBytes(head, 0, 'OggS')) return 'application/ogg';
    if (eqBytes(head, 0, '%PDF-')) return 'application/pdf';
    if (startsWith(head, [0x50, 0x4B, 0x03, 0x04])) return 'application/zip';
    if (startsWith(head, [0x1F, 0x8B])) return 'application/gzip';
    if (startsWith(head, [0x37, 0x7A, 0xBC, 0xAF, 0x27, 0x1C])) return 'application/x-7z-compressed';
    if (startsWith(head, [0x52, 0x61, 0x72, 0x21, 0x1A, 0x07])) return 'application/x-rar-compressed';
    if (startsWith(head, [0x7F, 0x45, 0x4C, 0x46])) return 'application/x-executable';
    if (eqBytes(head, 0, 'MZ')) return 'application/x-dosexec';
    var m4 = latin1(head, 0, 4);
    if (['\xfe\xed\xfa\xce', '\xfe\xed\xfa\xcf', '\xce\xfa\xed\xfe', '\xcf\xfa\xed\xfe'].indexOf(m4) >= 0) return 'application/x-mach-binary';
    if (eqBytes(head, 0, '#!')) return 'application/x-sh';
    var h4 = head.subarray(0, 4096);
    if (head.length && h4.indexOf(0) < 0) {
      var text;
      try { text = utf8Strict(h4); } catch (e) {
        try { text = utf8Strict(head.subarray(0, 4093)); } catch (e2) { return 'application/octet-stream'; }
      }
      var st = pyLstrip(text);
      if (st[0] === '{' || st[0] === '[') {
        try { JSON.parse(utf8Strict(head)); return 'application/json'; } catch (e3) { /* not JSON */ }
      }
      return 'text/plain';
    }
    return 'application/octet-stream';
  }
  function sourceTypeFor(mime) {
    if (mime.indexOf('image/') === 0) return 'image';
    if (mime.indexOf('video/') === 0) return 'video';
    if (mime.indexOf('audio/') === 0 || mime === 'application/ogg') return 'audio';
    if (mime === 'application/json') return 'event';
    if (mime === 'text/plain') return 'text';
    return 'document';
  }
  function processingBoundary(mime) { return HASH_ONLY_TYPES.indexOf(mime) >= 0 ? 'HASH_ONLY' : 'PARSE'; }
  function displayName(name) {
    if (!name) return '';
    name = String(name).normalize('NFC').replace(/\\/g, '/');
    name = name.slice(name.lastIndexOf('/') + 1);
    name = pyStrip(name.replace(/[\x00-\x1f\x7f]/g, ''));
    if (name === '.' || name === '..') return '';
    return pySlice(name, 120);
  }

  // SSRF guard for a future fetch adapter. Nothing in this engine fetches URLs.
  function ipv4Parts(host) {
    var m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host);
    if (!m) return null;
    var p = m.slice(1).map(Number);
    return p.every(function (x) { return x <= 255; }) ? p : null;
  }
  function ipv4Public(p) {
    var a = p[0], b = p[1];
    if (a === 0 || a === 10 || a === 127 || a >= 224) return false;
    if (a === 100 && b >= 64 && b <= 127) return false;
    if (a === 169 && b === 254) return false;
    if (a === 172 && b >= 16 && b <= 31) return false;
    if (a === 192 && b === 168) return false;
    if (a === 192 && b === 0 && (p[2] === 0 || p[2] === 2)) return false;
    if (a === 198 && (b === 18 || b === 19)) return false;
    if (a === 198 && b === 51 && p[2] === 100) return false;
    if (a === 203 && b === 0 && p[2] === 113) return false;
    return true;
  }
  function validateUrl(url) {
    var reasons = [];
    if (typeof url !== 'string' || !url || url.length > 2048) return [false, ['URL is empty or longer than 2048 characters']];
    if (/[\x00-\x1f\x7f ]/.test(url)) return [false, ['URL contains whitespace or control characters']];
    var m = /^([a-zA-Z][a-zA-Z0-9+.-]*):\/\/(?:([^@\/?#]*)@)?(\[[^\]]*\]|[^:\/?#]*)(?::([^\/?#]*))?/.exec(url);
    if (!m) {
      var sm = /^([a-zA-Z][a-zA-Z0-9+.-]*):/.exec(url);
      reasons.push('scheme ' + quote(sm ? sm[1] : '(none)') + ' is not https');
      reasons.push('URL has no host');
      return [false, reasons];
    }
    if (m[1].toLowerCase() !== 'https') reasons.push('scheme ' + quote(m[1]) + ' is not https');
    if (m[2] !== undefined) reasons.push('credentials in the URL are refused');
    var host = m[3].replace(/\.+$/, '').toLowerCase();
    if (!host) { reasons.push('URL has no host'); return [false, reasons]; }
    if (m[4] !== undefined && m[4] !== '') {
      if (!/^\d+$/.test(m[4])) reasons.push('port is not a number');
      else if (Number(m[4]) !== 443) reasons.push('port ' + Number(m[4]) + ' is not 443');
    }
    var suffixes = ['.localhost', '.local', '.internal', '.lan', '.home.arpa', '.corp'];
    if (host === 'localhost' || suffixes.some(function (s) { return host.slice(-s.length) === s; })) {
      reasons.push('host ' + quote(host) + ' is an internal name');
    }
    if (host[0] === '[') {
      var v6 = host.slice(1, -1);
      var mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/.exec(v6);
      var pub = mapped ? (ipv4Parts(mapped[1]) && ipv4Public(ipv4Parts(mapped[1]))) :
        !(v6 === '::1' || v6 === '::' || /^f[cd]/.test(v6) || /^fe[89ab]/.test(v6) || /^ff/.test(v6));
      if (!pub) reasons.push('address ' + v6 + ' is not publicly routable');
    } else if (ipv4Parts(host)) {
      if (!ipv4Public(ipv4Parts(host))) reasons.push('address ' + host + ' is not publicly routable');
    } else if (/^(0x[0-9a-f]+|[0-9]+)(\.(0x[0-9a-f]+|[0-9]+))*$/i.test(host)) {
      reasons.push('numeric or hex host encodings are refused');
    }
    return [reasons.length === 0, reasons];
  }

  async function evidenceIdFor(sha, at, label) {
    return 'EV-' + (await digest({ sha256: sha, at: at, label: label })).slice(0, 12).toUpperCase();
  }
  async function acquireBytes(data, o) {
    if (!(data instanceof Uint8Array)) throw new IntakeError('evidence content must be bytes');
    if (data.length > MAX_EVIDENCE_BYTES) throw new IntakeError('evidence exceeds the ' + MAX_EVIDENCE_BYTES + '-byte limit');
    if (!pyStrip(o.acquired_by || '')) throw new IntakeError('acquired_by is required for chain of custody');
    var sha = await sha256Bytes(data);
    var mime = sniffMime(data.subarray(0, 4096));
    var kind = o.object_kind || V.ORIGINAL;
    if (kind === V.DERIVATIVE && !o.parent_id) throw new IntakeError('a derivative must name its parent evidence');
    return {
      evidence_id: o.evidence_id || await evidenceIdFor(sha, o.acquired_at, o.label),
      label: o.label, source_type: sourceTypeFor(mime), object_kind: kind,
      content_sha256: sha, size_bytes: data.length, mime_sniffed: mime,
      mime_declared: pySlice(o.declared_mime || '', 100), declared_name: displayName(o.declared_name),
      acquired_at: o.acquired_at, acquired_by: o.acquired_by, acquisition_method: o.method || 'upload',
      processing_boundary: processingBoundary(mime),
      provenance_state: o.parent_id ? 'DECLARED_DERIVATIVE' : 'ACQUIRED',
      parent_id: o.parent_id || '', transformation: o.transformation || '',
      upstream_source: o.upstream_source || '', demonstration: !!o.demonstration
    };
  }
  function declaredMimeIndicator(rec) {
    var declared = pyStrip((rec.mime_declared || '').split(';')[0]).toLowerCase();
    if (!declared || declared === rec.mime_sniffed) return null;
    if (declared === 'image/jpg' && rec.mime_sniffed === 'image/jpeg') return null;
    return Indicator({
      code: 'CONTAINER.TYPE_MISMATCH', category: 'CONTAINER',
      title: "Declared file type disagrees with the file's bytes",
      evidence: 'declared ' + quote(declared) + '; content signature is ' + quote(rec.mime_sniffed),
      method: 'Magic-number signature comparison against the declared media type.',
      confidence: 'HIGH', limitation: 'Shows a labelling inconsistency, not how or why it arose.',
      alternatives: ['Renamed file extension', 'Misconfigured upload client'],
      state: V.REVIEW_REQUIRED, analyzer: 'intake@' + VER
    });
  }

  // ------------------------------------------------------------------
  // image (truth_forensics/image.py)
  // ------------------------------------------------------------------
  var IMG = 'image@' + VER;
  var MAX_TEXT_INFLATE = 64 * 1024, MAX_PIXELS = 16000000, PIXEL_ANALYSIS_BUDGET = 600000;
  var CLONE_BLOCK = 8, CLONE_MIN_BLOCKS = 32, CLONE_MIN_SHIFT = 16, CLONE_MAX_BUCKET = 8, CLONE_MIN_VARIANCE = 25;
  var IMG_NOT_PERFORMED = [
    'Lighting and shadow consistency analysis (not implemented)',
    'Edge and compositing-boundary analysis (not implemented)',
    'Double-JPEG-compression statistics (not implemented)',
    'C2PA / Content Credentials signature validation (not implemented; presence only)',
    'Generative-model classifier (not implemented; no model is bundled or called)'];
  var IJG_LUMA = [16, 11, 10, 16, 24, 40, 51, 61, 12, 12, 14, 19, 26, 58, 60, 55,
    14, 13, 16, 24, 40, 57, 69, 56, 14, 17, 22, 29, 51, 87, 80, 62,
    18, 22, 37, 56, 68, 109, 103, 77, 24, 35, 55, 64, 81, 104, 113, 92,
    49, 64, 78, 87, 103, 121, 120, 101, 72, 92, 95, 98, 112, 100, 103, 99];
  var ZIGZAG = [0, 1, 8, 16, 9, 2, 3, 10, 17, 24, 32, 25, 18, 11, 4, 5, 12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28, 35, 42, 49, 56, 57, 50, 43, 36, 29, 22, 15, 23, 30, 37,
    44, 51, 58, 59, 52, 45, 38, 31, 39, 46, 53, 60, 61, 54, 47, 55, 62, 63];
  var SOF_MARKERS = [0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF];
  var EXIF_TAGS = { 0x010F: 'Make', 0x0110: 'Model', 0x0112: 'Orientation', 0x0131: 'Software',
    0x0132: 'DateTime', 0x9003: 'DateTimeOriginal', 0x9004: 'DateTimeDigitized',
    0x9010: 'OffsetTime', 0x9011: 'OffsetTimeOriginal', 0xA002: 'PixelXDimension', 0xA003: 'PixelYDimension' };
  var GPS_TAGS = { 1: 'GPSLatitudeRef', 2: 'GPSLatitude', 3: 'GPSLongitudeRef', 4: 'GPSLongitude' };
  var TYPE_SIZES = { 1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8 };

  function parseExif(tiff) {
    if (tiff.length < 8) throw new ParseError('EXIF block shorter than a TIFF header');
    var le;
    if (eqBytes(tiff, 0, 'II')) le = true;
    else if (eqBytes(tiff, 0, 'MM')) le = false;
    else throw new ParseError('EXIF block has no TIFF byte-order mark');
    var R = new Reader(tiff);
    if (R.u16(2, le) !== 42) throw new ParseError('EXIF TIFF magic is not 42');
    var out = {}, visited = {};
    function readIfd(offset, names) {
      var ptrs = {};
      if (visited[offset]) throw new ParseError('EXIF IFD loop');
      visited[offset] = true;
      if (offset + 2 > tiff.length) throw new ParseError('EXIF IFD offset out of range');
      var count = R.u16(offset, le);
      if (count > 512) throw new ParseError('EXIF IFD has an implausible entry count');
      for (var i = 0; i < count; i++) {
        var pos = offset + 2 + 12 * i;
        if (pos + 12 > tiff.length) throw new ParseError('EXIF IFD entry out of range');
        var tag = R.u16(pos, le), typ = R.u16(pos + 2, le), n = R.u32(pos + 4, le);
        var size = (TYPE_SIZES[typ] || 0) * n;
        if (size === 0) continue;
        var raw;
        if (size <= 4) raw = tiff.subarray(pos + 8, pos + 8 + size);
        else {
          var ptr = R.u32(pos + 8, le);
          if (ptr + size > tiff.length) throw new ParseError('EXIF value out of range');
          raw = tiff.subarray(ptr, ptr + size);
        }
        if ((tag === 0x8769 || tag === 0x8825) && typ === 4) { ptrs[tag] = new Reader(raw).u32(0, le); continue; }
        var name = names[tag];
        if (name === undefined) continue;
        out[name] = exifValue(raw, typ, n, le);
      }
      return ptrs;
    }
    var ifd0 = R.u32(4, le);
    var p = readIfd(ifd0, EXIF_TAGS);
    if (p[0x8769] !== undefined) readIfd(p[0x8769], EXIF_TAGS);
    if (p[0x8825] !== undefined) readIfd(p[0x8825], GPS_TAGS);
    return out;
  }
  function exifValue(raw, typ, n, le) {
    var R = new Reader(raw), vals = [], i;
    if (typ === 2) { var z = raw.indexOf(0); return pyStrip(latin1(raw, 0, z < 0 ? raw.length : z)); }
    if (typ === 3) { for (i = 0; i < n; i++) vals.push(R.u16(2 * i, le)); return n === 1 ? vals[0] : vals; }
    if (typ === 4 || typ === 9) { for (i = 0; i < n; i++) vals.push(typ === 4 ? R.u32(4 * i, le) : R.i32(4 * i, le)); return n === 1 ? vals[0] : vals; }
    if (typ === 5 || typ === 10) {
      for (i = 0; i < n; i++) {
        vals.push(typ === 5 ? [R.u32(8 * i, le), R.u32(8 * i + 4, le)] : [R.i32(8 * i, le), R.i32(8 * i + 4, le)]);
      }
      return vals;
    }
    return null;
  }
  function gpsDecimal(exif) {
    function coord(key, refKey, neg) {
      var parts = exif[key];
      if (!Array.isArray(parts) || parts.length !== 3) return null;
      if (parts.some(function (p) { return !Array.isArray(p) || p[1] === 0; })) return null;
      // sum(n/d / div) as an exact rational, then half-up at 1e-5 degrees.
      var divs = [1n, 60n, 3600n], N = 0n, D = 1n;
      for (var i = 0; i < 3; i++) {
        var n = BigInt(parts[i][0]), d = BigInt(parts[i][1]) * divs[i];
        N = N * d + n * D; D = D * d;
      }
      var num = N * 200000n + D, den = 2n * D;
      if (den < 0n) { num = -num; den = -den; }
      var q = num / den; if ((num % den !== 0n) && ((num < 0n) !== (den < 0n))) q -= 1n;
      var units = Number(q);
      var sign = exif[refKey] === neg ? '-' : '';
      return sign + fdiv(units, 100000) + '.' + pad(((units % 100000) + 100000) % 100000, 5);
    }
    var lat = coord('GPSLatitude', 'GPSLatitudeRef', 'S'), lon = coord('GPSLongitude', 'GPSLongitudeRef', 'W');
    return lat && lon ? lat + ',' + lon : '';
  }
  function exifTimeIso(value) {
    var m = /^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})$/.exec(value || '');
    return m ? m[1] + '-' + m[2] + '-' + m[3] + 'T' + m[4] + ':' + m[5] + ':' + m[6] : '';
  }
  function ijgQuality(zz) {
    var natural = new Array(64).fill(0);
    for (var k = 0; k < zz.length; k++) natural[ZIGZAG[k]] = zz[k];
    var bestQ = 0, bestDiff = null;
    for (var q = 1; q <= 100; q++) {
      var scale = q < 50 ? fdiv(5000, q) : 200 - 2 * q, diff = 0;
      for (var i = 0; i < 64; i++) {
        var t = fdiv(IJG_LUMA[i] * scale + 50, 100);
        t = t < 1 ? 1 : t > 255 ? 255 : t;
        diff += Math.abs(t - natural[i]);
      }
      if (bestDiff === null || diff < bestDiff) { bestQ = q; bestDiff = diff; }
    }
    return { quality: bestQ, abs_deviation: bestDiff, exact: bestDiff === 0 };
  }
  function hex2(m) { return '0x' + ('0' + m.toString(16).toUpperCase()).slice(-2); }
  function parseJpeg(data) {
    var n = data.length, R = new Reader(data);
    var info = { format: 'jpeg', segments: [], exif: {}, xmp_creator_tool: '', quant_tables: {},
      c2pa_manifest: false, frames: [], eoi_offset: null, trailing_bytes: 0, app13_photoshop: false, parse_error: '' };
    var pos = 2;
    try {
      while (pos + 2 <= n) {
        if (data[pos] !== 0xFF) throw new ParseError('expected a marker at offset ' + pos);
        var marker = data[pos + 1];
        if (marker === 0xFF) { pos += 1; continue; }
        if (marker === 0xD9) { info.eoi_offset = pos; break; }
        if ((marker >= 0xD0 && marker <= 0xD7) || marker === 0x01) { pos += 2; continue; }
        if (pos + 4 > n) throw new ParseError('segment header truncated');
        var length = R.u16(pos + 2);
        if (length < 2 || pos + 2 + length > n) throw new ParseError('segment ' + hex2(marker) + ' length out of range');
        var payload = data.subarray(pos + 4, pos + 2 + length);
        info.segments.push({ marker: hex2(marker), length: length });
        jpegSegment(marker, payload, info);
        pos += 2 + length;
        if (marker === 0xDA) {
          for (;;) {
            var nxt = indexOfByte(data, 0xFF, pos);
            if (nxt < 0 || nxt + 1 >= n) { pos = n; break; }
            var follow = data[nxt + 1];
            if (follow === 0x00 || (follow >= 0xD0 && follow <= 0xD7)) { pos = nxt + 2; continue; }
            pos = nxt; break;
          }
        }
      }
      if (info.eoi_offset === null) throw new ParseError('no end-of-image marker');
      info.trailing_bytes = n - (info.eoi_offset + 2);
    } catch (e) {
      if (!(e instanceof ParseError || e instanceof StructError)) throw e;
      info.parse_error = parseMessage(e);
    }
    return info;
  }
  function jpegSegment(marker, payload, info) {
    if (marker === 0xE1 && eqBytes(payload, 0, 'Exif\x00\x00')) {
      try { info.exif = parseExif(payload.subarray(6)); } catch (e) {
        if (!(e instanceof ParseError || e instanceof StructError)) throw e;
        info.exif_error = e.message;
      }
    } else if (marker === 0xE1 && eqBytes(payload, 0, 'http://ns.adobe.com/xap/1.0/\x00')) {
      var text = utf8(payload.subarray(29));
      var m = /CreatorTool="([^"]{1,200})"/.exec(text) || /<xmp:CreatorTool>([^<]{1,200})<\/xmp:CreatorTool>/.exec(text);
      if (m) info.xmp_creator_tool = m[1];
    } else if (marker === 0xEB && latin1(payload).indexOf('c2pa') >= 0) {
      info.c2pa_manifest = true;
    } else if (marker === 0xED && eqBytes(payload, 0, 'Photoshop 3.0')) {
      info.app13_photoshop = true;
    } else if (marker === 0xDB) {
      var i = 0, R = new Reader(payload);
      while (i < payload.length) {
        var pq = payload[i] >> 4, tq = payload[i] & 0x0F, width = pq ? 2 : 1, end = i + 1 + 64 * width;
        if (end > payload.length) throw new ParseError('DQT table truncated');
        var vals = [];
        for (var k = 0; k < 64; k++) vals.push(width === 1 ? payload[i + 1 + k] : R.u16(i + 1 + 2 * k));
        info.quant_tables[String(tq)] = vals;
        i = end;
      }
    } else if (SOF_MARKERS.indexOf(marker) >= 0) {
      if (payload.length < 6) throw new ParseError('SOF segment truncated');
      var S = new Reader(payload);
      info.frames.push({ sof: hex2(marker), width: S.u16(3), height: S.u16(1), components: payload[5] });
    }
  }
  async function parsePng(data) {
    var info = { format: 'png', chunks: [], ihdr: {}, text: {}, exif: {}, time: '', c2pa_manifest: false,
      crc_errors: [], trailing_bytes: 0, idat: new Uint8Array(0), parse_error: '' };
    var pos = 8, n = data.length, R = new Reader(data), idat = [], idatLen = 0, seenIend = false;
    try {
      while (pos + 12 <= n) {
        var length = R.u32(pos);
        var ctype = data.subarray(pos + 4, pos + 8), name = latin1(ctype);
        if (pos + 12 + length > n) throw new ParseError('chunk ' + quote(name) + ' runs past the end of the file');
        var body = data.subarray(pos + 8, pos + 8 + length);
        var crc = R.u32(pos + 8 + length);
        if (crc32([ctype, body]) !== crc) info.crc_errors.push(name);
        info.chunks.push({ type: name, length: length });
        if (info.chunks.length > 100000) throw new ParseError('implausible chunk count');
        if (name === 'IDAT') { idat.push(body); idatLen += body.length; }
        else await pngChunk(name, body, info);
        pos += 12 + length;
        if (name === 'IEND') { seenIend = true; break; }
      }
      if (!seenIend) throw new ParseError('no IEND chunk');
      info.trailing_bytes = n - pos;
    } catch (e) {
      if (!(e instanceof ParseError || e instanceof StructError)) throw e;
      info.parse_error = parseMessage(e);
    }
    info.idat = concat(idat, idatLen);
    return info;
  }
  async function inflateText(blob) {
    var r = await inflate(blob, MAX_TEXT_INFLATE);
    if (r.error && !r.data.length) return ['', false];
    return [latin1(r.data), r.more];
  }
  async function pngChunk(name, body, info) {
    var z;
    if (name === 'IHDR') {
      if (body.length !== 13) throw new ParseError('IHDR is not 13 bytes');
      var R = new Reader(body);
      info.ihdr = { width: R.u32(0), height: R.u32(4), bit_depth: body[8], color_type: body[9], interlace: body[12] };
    } else if (name === 'tEXt' && (z = body.indexOf(0)) >= 0) {
      info.text[latin1(body, 0, z).slice(0, 79)] = latin1(body, z + 1).slice(0, 4000);
    } else if (name === 'zTXt' && (z = body.indexOf(0)) >= 0) {
      var key = latin1(body, 0, z).slice(0, 79);
      var t = await inflateText(body.subarray(z + 2));
      info.text[key] = t[0].slice(0, 4000);
      if (t[1]) (info.inflate_capped = info.inflate_capped || []).push(key);
    } else if (name === 'iTXt' && (z = body.indexOf(0)) >= 0) {
      var k2 = latin1(body, 0, z).slice(0, 79), rest = body.subarray(z + 1);
      if (rest.length >= 2) {
        var flag = rest[0], tail = rest.subarray(2);
        var a = tail.indexOf(0), b = a < 0 ? -1 : tail.indexOf(0, a + 1);
        if (a >= 0 && b >= 0) {
          var raw = tail.subarray(b + 1);
          var text = flag ? (await inflateText(raw))[0] : utf8(raw);
          info.text[k2] = pySlice(text, 4000);
        }
      }
    } else if (name === 'eXIf') {
      try { info.exif = parseExif(body); } catch (e) {
        if (!(e instanceof ParseError || e instanceof StructError)) throw e;
        info.exif_error = e.message;
      }
    } else if (name === 'tIME' && body.length === 7) {
      var T = new Reader(body);
      info.time = pad(T.u16(0), 4) + '-' + pad(body[2], 2) + '-' + pad(body[3], 2) + 'T' +
        pad(body[4], 2) + ':' + pad(body[5], 2) + ':' + pad(body[6], 2) + 'Z';
    } else if (name === 'caBX') {
      info.c2pa_manifest = true;
    }
  }
  async function decodePngGray(info) {
    var ihdr = info.ihdr || {}, w = ihdr.width || 0, h = ihdr.height || 0;
    var channels = { 0: 1, 2: 3, 4: 2, 6: 4 }[ihdr.color_type];
    if (!channels || ihdr.bit_depth !== 8) return [null, null, 'pixel analysis supports 8-bit gray, gray+alpha, RGB and RGBA PNG'];
    if (ihdr.interlace) return [null, null, 'interlaced PNG is not decoded'];
    if (w <= 0 || h <= 0 || w * h > MAX_PIXELS) return [null, null, 'image dimensions exceed the ' + MAX_PIXELS + '-pixel decode limit'];
    var stride = w * channels, expected = (stride + 1) * h;
    var r = await inflate(info.idat, expected + 1);
    // Python's decompressobj ignores bytes after the zlib stream; the browser's
    // DecompressionStream reports them. A full-size result is a success in both.
    if (r.error && r.total < expected) return [null, null, 'IDAT inflate failed'];
    if (r.total > expected) return [null, null, 'IDAT inflates past the declared image size (decompression bomb guard)'];
    if (r.total < expected) return [null, null, 'IDAT is shorter than the declared image size'];
    var raw = r.data, out = new Uint8Array(w * h), prev = new Uint8Array(stride);
    for (var y = 0; y < h; y++) {
      var base = y * (stride + 1), ftype = raw[base];
      var line = raw.slice(base + 1, base + 1 + stride);
      unfilter(ftype, line, prev, channels);
      var row = y * w, x, i;
      if (channels === 1 || channels === 2) { for (x = 0; x < w; x++) out[row + x] = line[x * channels]; }
      else { for (x = 0; x < w; x++) { i = x * channels; out[row + x] = fdiv(299 * line[i] + 587 * line[i + 1] + 114 * line[i + 2], 1000); } }
      prev = line;
    }
    return [w, h, out];
  }
  function unfilter(ftype, line, prev, bpp) {
    var n = line.length, i;
    if (ftype === 0) return;
    if (ftype === 1) { for (i = bpp; i < n; i++) line[i] = (line[i] + line[i - bpp]) & 0xFF; }
    else if (ftype === 2) { for (i = 0; i < n; i++) line[i] = (line[i] + prev[i]) & 0xFF; }
    else if (ftype === 3) { for (i = 0; i < n; i++) line[i] = (line[i] + (((i >= bpp ? line[i - bpp] : 0) + prev[i]) >> 1)) & 0xFF; }
    else if (ftype === 4) {
      for (i = 0; i < n; i++) {
        var a = i >= bpp ? line[i - bpp] : 0, b = prev[i], c = i >= bpp ? prev[i - bpp] : 0;
        var p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
        line[i] = (line[i] + (pa <= pb && pa <= pc ? a : pb <= pc ? b : c)) & 0xFF;
      }
    } else throw new ParseError('unknown PNG filter type ' + ftype);
  }
  function copyMove(width, height, gray) {
    var b = CLONE_BLOCK;
    if (width < 2 * b || height < 2 * b) return { clusters: [], blocks_examined: 0, note: 'image too small' };
    var q = new Uint8Array(gray.length), x, y, i;
    for (i = 0; i < gray.length; i++) q[i] = gray[i] >> 2;
    var iw = width + 1, s1 = new Float64Array(iw * (height + 1)), s2 = new Float64Array(iw * (height + 1));
    for (y = 0; y < height; y++) {
      var r1 = 0, r2 = 0, row = y * width;
      for (x = 0; x < width; x++) {
        var v = q[row + x]; r1 += v; r2 += v * v;
        s1[(y + 1) * iw + x + 1] = s1[y * iw + x + 1] + r1;
        s2[(y + 1) * iw + x + 1] = s2[y * iw + x + 1] + r2;
      }
    }
    var n = b * b, minVar = CLONE_MIN_VARIANCE >> 4, buckets = new Map(), examined = 0, codes = new Array(n);
    for (y = 0; y + b <= height; y++) {
      var y2 = y + b;
      for (x = 0; x + b <= width; x++) {
        var x2 = x + b;
        var t1 = s1[y2 * iw + x2] - s1[y * iw + x2] - s1[y2 * iw + x] + s1[y * iw + x];
        var t2 = s2[y2 * iw + x2] - s2[y * iw + x2] - s2[y2 * iw + x] + s2[y * iw + x];
        if (n * t2 - t1 * t1 < minVar * n * n) continue;
        examined++;
        for (var r = 0, k = 0; r < b; r++) { var base = (y + r) * width + x; for (var c = 0; c < b; c++) codes[k++] = q[base + c]; }
        var key = String.fromCharCode.apply(null, codes);
        var list = buckets.get(key);
        if (list) list.push([x, y]); else buckets.set(key, [[x, y]]);
      }
    }
    var shifts = new Map();
    buckets.forEach(function (pos) {
      if (pos.length < 2 || pos.length > CLONE_MAX_BUCKET) return;
      for (var a = 0; a < pos.length; a++) {
        for (var bb = a + 1; bb < pos.length; bb++) {
          var ax = pos[a][0], ay = pos[a][1], bx = pos[bb][0], by = pos[bb][1];
          var dx = bx - ax, dy = by - ay;
          if (dx < 0 || (dx === 0 && dy < 0)) { dx = -dx; dy = -dy; ax = bx; ay = by; }
          if (Math.abs(dx) + Math.abs(dy) < CLONE_MIN_SHIFT) continue;
          var sk = dx + ',' + dy, l = shifts.get(sk);
          if (l) l.push([ax, ay]); else shifts.set(sk, [[ax, ay]]);
        }
      }
    });
    var clusters = [];
    shifts.forEach(function (src, sk) {
      if (src.length < CLONE_MIN_BLOCKS) return;
      var d = sk.split(',').map(Number), mnx = Infinity, mny = Infinity, mxx = -Infinity, mxy = -Infinity;
      src.forEach(function (p) { mnx = Math.min(mnx, p[0]); mny = Math.min(mny, p[1]); mxx = Math.max(mxx, p[0]); mxy = Math.max(mxy, p[1]); });
      var ra = [mnx, mny, mxx + b, mxy + b];
      clusters.push({ shift: [d[0], d[1]], matched_blocks: src.length, region_a: ra,
        region_b: [ra[0] + d[0], ra[1] + d[1], ra[2] + d[0], ra[3] + d[1]] });
    });
    clusters.sort(function (p, q2) { return tupleCmp([-p.matched_blocks, p.shift[0], p.shift[1]], [-q2.matched_blocks, q2.shift[0], q2.shift[1]]); });
    return { clusters: clusters.slice(0, 8), blocks_examined: examined, note: '' };
  }
  function dhash(width, height, gray) {
    if (width < 9 || height < 8) return '';
    var bits = 0n;
    for (var cy = 0; cy < 8; cy++) {
      var y0 = fdiv(cy * height, 8), y1 = fdiv((cy + 1) * height, 8), row = [];
      for (var cx = 0; cx < 9; cx++) {
        var x0 = fdiv(cx * width, 9), x1 = fdiv((cx + 1) * width, 9), total = 0;
        for (var y = y0; y < y1; y++) { var base = y * width; for (var x = x0; x < x1; x++) total += gray[base + x]; }
        row.push(fdiv(total, (y1 - y0) * (x1 - x0)));
      }
      for (var k = 0; k < 8; k++) bits = (bits << 1n) | (row[k] < row[k + 1] ? 1n : 0n);
    }
    return ('0000000000000000' + bits.toString(16)).slice(-16);
  }
  function hammingHex(a, b) {
    var x = BigInt('0x' + a) ^ BigInt('0x' + b), c = 0;
    while (x) { c += Number(x & 1n); x >>= 1n; }
    return c;
  }
  function downscaleGray(width, height, gray) {
    var f = 1;
    while (fdiv(width, f) * fdiv(height, f) > PIXEL_ANALYSIS_BUDGET) f++;
    if (f === 1) return [width, height, gray, 1];
    var w2 = fdiv(width, f), h2 = fdiv(height, f), out = new Uint8Array(w2 * h2), area = f * f;
    for (var y = 0; y < h2; y++) {
      for (var x = 0; x < w2; x++) {
        var t = 0;
        for (var yy = y * f; yy < y * f + f; yy++) { var base = yy * width + x * f; for (var k = 0; k < f; k++) t += gray[base + k]; }
        out[y * w2 + x] = fdiv(t, area);
      }
    }
    return [w2, h2, out, f];
  }
  function metadataIndicators(exif, dims, fields) {
    var out = [];
    fields.forEach(function (f) { if (f[1]) Array.prototype.push.apply(out, softwareIndicators(f[0], f[1], IMG)); });
    var modified = exif.DateTime || '', original = exif.DateTimeOriginal || '';
    if (modified && original && modified !== original) {
      out.push(Indicator({
        code: 'METADATA.TIMESTAMP_MISMATCH', category: 'METADATA',
        title: 'Modification time differs from capture time',
        evidence: 'EXIF DateTime = ' + quote(modified) + '; DateTimeOriginal = ' + quote(original),
        method: 'Comparison of EXIF IFD0 DateTime with Exif IFD DateTimeOriginal.', confidence: 'MODERATE',
        limitation: 'Both values are unsigned metadata that any tool can rewrite. The gap shows the ' +
          'file was written after capture, not what changed.',
        alternatives: ['In-camera or phone-gallery edit', 'Export or re-save by photo-management software',
          'Camera clock or time-zone adjustment'],
        state: V.REVIEW_REQUIRED, analyzer: IMG
      }));
    }
    var px = exif.PixelXDimension, py = exif.PixelYDimension;
    if (dims && Number.isInteger(px) && Number.isInteger(py) && px && py) {
      var w = dims[0], h = dims[1];
      if (!((px === w && py === h) || (px === h && py === w))) {
        out.push(Indicator({
          code: 'METADATA.DIMENSION_MISMATCH', category: 'METADATA',
          title: "Recorded pixel dimensions differ from the image's actual dimensions",
          evidence: 'EXIF says ' + px + 'x' + py + '; the encoded image is ' + w + 'x' + h,
          method: 'Comparison of Exif PixelX/YDimension with the frame header.', confidence: 'MODERATE',
          limitation: 'Consistent with resizing or cropping; says nothing about content.',
          alternatives: ['Resize or crop after capture', 'Metadata copied from a different rendition'],
          state: V.REVIEW_REQUIRED, analyzer: IMG
        }));
      }
    }
    if (!Object.keys(exif).length) {
      out.push(Indicator({
        code: 'PROVENANCE.NO_CAPTURE_METADATA', category: 'PROVENANCE', title: 'No camera metadata present',
        evidence: 'No EXIF block was found in the file',
        method: 'Container parse for EXIF (APP1 in JPEG, eXIf in PNG).', confidence: 'HIGH',
        limitation: 'Most social and messaging platforms strip EXIF. Absence is a provenance gap, ' +
          'not a sign of manipulation.',
        alternatives: ['Platform metadata stripping', 'Screenshot or screen recording', 'Privacy tool or deliberate removal'],
        state: V.PROVENANCE_GAP, analyzer: IMG
      }));
    }
    return out;
  }
  function c2paIndicator(where) {
    return Indicator({
      code: 'PROVENANCE.C2PA_MANIFEST_PRESENT', category: 'PROVENANCE',
      title: 'Content Credentials (C2PA) manifest data detected — not validated',
      evidence: 'C2PA manifest store bytes found in ' + where,
      method: 'Container scan for the C2PA JUMBF label.', confidence: 'HIGH',
      limitation: 'This engine has no C2PA validator. The signature, signer and assertions were not ' +
        'checked, so the manifest supports nothing until a validator confirms it.',
      alternatives: ['A valid manifest from a capture device or editor',
        'A manifest copied from another file (would fail hash binding)'],
      state: V.INCONCLUSIVE, analyzer: IMG
    });
  }
  function cloneIndicator(cl, factor) {
    var scale = factor > 1 ? ' (analysed at 1/' + factor + ' scale)' : '';
    return Indicator({
      code: 'SPATIAL.COPY_MOVE', category: 'SPATIAL', title: 'Duplicated image region (possible copy-move)',
      evidence: cl.matched_blocks + ' identical non-flat 8x8 blocks shifted by (' + cl.shift[0] + ', ' +
        cl.shift[1] + ') px; region ' + pyStr(cl.region_a) + ' matches region ' + pyStr(cl.region_b) + scale,
      method: 'Exact block matching on 6-bit luminance with flat-block and texture filters.', confidence: 'MODERATE',
      limitation: 'Cannot tell which region is the source. Misses scaled, rotated or recompressed ' +
        'clones, and lossy JPEG usually defeats exact matching.',
      alternatives: ['Genuinely repetitive content (tiles, windows, printed patterns)',
        'Synthetic or graphic imagery', 'Panorama or HDR stitching'],
      state: V.ANOMALY_DETECTED, analyzer: IMG, location: pyStr(cl.region_a) + ' -> ' + pyStr(cl.region_b)
    });
  }
  function pixelBlock(w, h, gray) {
    var ds = downscaleGray(w, h, gray), cm = copyMove(ds[0], ds[1], ds[2]);
    return { pixels: { width: w, height: h, analysis_scale: ds[3], blocks_examined: cm.blocks_examined,
      clone_clusters: cm.clusters, dhash: dhash(w, h, gray) }, factor: ds[3] };
  }
  async function analyzeImage(data, mime) {
    var result = { analyzer: IMG, metadata: {}, indicators: [], observations: [], not_performed: IMG_NOT_PERFORMED.slice(), pixels: null };
    var inds = result.indicators, exif, info, dims;
    if (mime === 'image/jpeg') {
      info = parseJpeg(data);
      var frame = info.frames.length ? info.frames[0] : null;
      dims = frame ? [frame.width, frame.height] : null;
      var q0 = info.quant_tables['0'];
      result.metadata = { format: 'jpeg', dimensions: dims, exif: info.exif, xmp_creator_tool: info.xmp_creator_tool,
        segments: info.segments.length, quantization: q0 && q0.length === 64 ? ijgQuality(q0) : null,
        c2pa_manifest: info.c2pa_manifest, trailing_bytes: info.trailing_bytes };
      if (info.parse_error) inds.push(parseErrorIndicator(info.parse_error, IMG));
      Array.prototype.push.apply(inds, metadataIndicators(info.exif, dims,
        [['EXIF Software', pyStr(info.exif.Software === undefined ? '' : info.exif.Software)], ['XMP CreatorTool', info.xmp_creator_tool]]));
      if (info.c2pa_manifest) inds.push(c2paIndicator('an APP11 segment'));
      if (info.trailing_bytes > 0) inds.push(trailingDataIndicator(info.trailing_bytes, 'JPEG EOI', IMG));
      result.not_performed.push('Copy-move pixel analysis of JPEG (browser console only; needs a JPEG decoder)');
      exif = info.exif;
    } else if (mime === 'image/png') {
      info = await parsePng(data);
      var ih = info.ihdr;
      dims = Object.keys(ih).length ? [ih.width, ih.height] : null;
      result.metadata = { format: 'png', dimensions: dims, exif: info.exif, text: info.text, png_time: info.time,
        chunks: info.chunks.length, crc_errors: info.crc_errors, c2pa_manifest: info.c2pa_manifest,
        trailing_bytes: info.trailing_bytes };
      if (info.parse_error) inds.push(parseErrorIndicator(info.parse_error, IMG));
      if (info.crc_errors.length) {
        inds.push(Indicator({
          code: 'CONTAINER.CRC_MISMATCH', category: 'CONTAINER', title: 'PNG chunk checksum does not match its contents',
          evidence: 'CRC-32 mismatch in chunk(s): ' + info.crc_errors.join(', '),
          method: 'CRC-32 recomputed over each chunk type and body.', confidence: 'HIGH',
          limitation: 'Proves the bytes changed after the chunk was written, or were corrupted. ' +
            'Does not show whether the change was deliberate.',
          alternatives: ['Storage or transfer corruption', 'Byte-level editing'],
          state: V.ANOMALY_DETECTED, analyzer: IMG
        }));
      }
      var fields = [['EXIF Software', pyStr(info.exif.Software === undefined ? '' : info.exif.Software)]];
      sortedKeys(info.text).forEach(function (k) {
        if (['software', 'comment', 'description', 'source'].indexOf(k.toLowerCase()) >= 0) fields.push(["PNG text '" + k + "'", info.text[k]]);
      });
      Array.prototype.push.apply(inds, metadataIndicators(info.exif, dims, fields));
      if (Object.prototype.hasOwnProperty.call(info.text, 'parameters')) {
        inds.push(Indicator({
          code: 'SYNTHETIC.GENERATION_PARAMETERS', category: 'SYNTHETIC', title: "Text chunk named 'parameters' present",
          evidence: "PNG text chunk 'parameters' (" + pyLen(info.text.parameters) + ' chars)',
          method: 'PNG text-chunk keyword inspection.', confidence: 'MODERATE',
          limitation: 'Some diffusion front-ends store generation settings under this keyword. ' +
            'Any tool can write it, and it is lost on re-save.',
          alternatives: ['An unrelated tool using the same keyword'], state: V.REVIEW_REQUIRED, analyzer: IMG
        }));
      }
      if (info.c2pa_manifest) inds.push(c2paIndicator('a caBX chunk'));
      if (info.trailing_bytes > 0) inds.push(trailingDataIndicator(info.trailing_bytes, 'PNG IEND', IMG));
      if (!info.parse_error) {
        var dec;
        try { dec = await decodePngGray(info); } catch (e) {
          if (!(e instanceof ParseError)) throw e;
          dec = [null, null, e.message];
        }
        if (dec[0] === null) result.not_performed.push('Copy-move pixel analysis (' + dec[2] + ')');
        else {
          var pb = pixelBlock(dec[0], dec[1], dec[2]);
          result.pixels = pb.pixels;
          pb.pixels.clone_clusters.forEach(function (cl) { inds.push(cloneIndicator(cl, pb.factor)); });
        }
      }
      exif = info.exif;
    } else {
      exif = {};
      result.metadata = { format: mime.split('/').pop() };
      result.not_performed.push('Structural analysis of ' + mime + ' (not implemented)');
    }
    var when = exifTimeIso(pyStr(exif.DateTimeOriginal === undefined ? '' : exif.DateTimeOriginal));
    if (when) result.observations.push({ dimension: 'time', value: when, basis: 'EXIF DateTimeOriginal (unsigned metadata)' });
    var device = pyStrip(['Make', 'Model'].map(function (k) { return pyStrip(pyStr(exif[k] === undefined ? '' : exif[k])); }).join(' '));
    if (device) result.observations.push({ dimension: 'device', value: device, basis: 'EXIF Make/Model (unsigned metadata)' });
    var gps = gpsDecimal(exif);
    if (gps) result.observations.push({ dimension: 'location', value: gps, basis: 'EXIF GPS (unsigned metadata)' });
    return result;
  }

  // ------------------------------------------------------------------
  // audio (truth_forensics/audio.py)
  // ------------------------------------------------------------------
  var AUD = 'audio@' + VER, FULL_SCALE = 32768, MAX_ANALYSIS_FRAMES = 48000 * 600, STEP_WINDOW = 32, MAX_EVENTS = 20;
  var AUD_NOT_PERFORMED = [
    'Speaker-consistency analysis (adapter boundary; not implemented)',
    'Synthetic-speech / voice-clone classifier (adapter boundary; no model bundled)',
    'Electrical network frequency (ENF) analysis (not implemented)'];
  function parseWav(data) {
    if (data.length < 12 || !eqBytes(data, 0, 'RIFF') || !eqBytes(data, 8, 'WAVE')) throw new ParseError('not a RIFF/WAVE file');
    var R = new Reader(data);
    var info = { riff_size: R.u32(4, true), file_size: data.length, fmt: null, data_offset: null, data_size: 0, chunks: [], info_tags: {} };
    var pos = 12;
    while (pos + 8 <= data.length) {
      var cid = latin1(data, pos, pos + 4), size = R.u32(pos + 4, true), bs = pos + 8;
      info.chunks.push({ id: cid, size: size });
      if (info.chunks.length > 10000) throw new ParseError('implausible chunk count');
      if (cid === 'data') {
        info.data_offset = bs; info.data_size = Math.min(size, data.length - bs);
        info.data_truncated = size > data.length - bs;
      } else if (bs + size > data.length) {
        throw new ParseError('chunk ' + quote(cid) + ' runs past the end of the file');
      } else if (cid === 'fmt ') {
        if (size < 16) throw new ParseError('fmt chunk too short');
        var tag = R.u16(bs, true);
        if (tag === 0xFFFE && size >= 40) tag = R.u16(bs + 24, true);
        info.fmt = { format: tag, channels: R.u16(bs + 2, true), sample_rate: R.u32(bs + 4, true),
          block_align: R.u16(bs + 12, true), bits: R.u16(bs + 14, true) };
      } else if (cid === 'LIST' && eqBytes(data, bs, 'INFO')) {
        var p = bs + 4, end = bs + size;
        while (p + 8 <= end) {
          var t = latin1(data, p, p + 4), ln = R.u32(p + 4, true);
          if (p + 8 + ln > end) break;
          var val = data.subarray(p + 8, p + 8 + ln), z = val.indexOf(0);
          info.info_tags[t] = latin1(val, 0, z < 0 ? val.length : z).slice(0, 400);
          p += 8 + ln + (ln & 1);
        }
      }
      pos = bs + size + (size & 1);
    }
    if (info.fmt === null || info.data_offset === null) throw new ParseError('fmt or data chunk missing');
    return info;
  }
  function decodeSamples(data, info) {
    var f = info.fmt, ch = f.channels, bits = f.bits, tag = f.format;
    if (ch < 1 || ch > 8) throw new ParseError('unsupported channel count ' + ch);
    var width = fdiv(bits, 8);
    if (!((tag === 1 && [8, 16, 24, 32].indexOf(bits) >= 0) || (tag === 3 && bits === 32))) {
      throw new ParseError('unsupported sample format (tag ' + tag + ', ' + bits + '-bit)');
    }
    var frame = width * ch, raw = data.subarray(info.data_offset, info.data_offset + info.data_size);
    var frames = fdiv(raw.length, frame), note = '';
    if (frames > MAX_ANALYSIS_FRAMES) { frames = MAX_ANALYSIS_FRAMES; note = 'analysis limited to the first 10 minutes'; }
    var R = new Reader(raw), out = [], c, i;
    for (c = 0; c < ch; c++) out.push(new Array(frames));
    for (i = 0; i < frames; i++) {
      for (c = 0; c < ch; c++) {
        var o = (i * ch + c) * width, v;
        if (tag === 3) {
          var x = R.f32(o, true);
          x = x !== x ? 0 : x > 1 ? 1 : x < -1 ? -1 : x;
          v = Math.floor(x * 32767 + 0.5);
        } else if (bits === 8) v = (raw[o] - 128) << 8;
        else if (bits === 16) v = R.i16(o, true);
        else if (bits === 24) { v = raw[o] | (raw[o + 1] << 8) | (raw[o + 2] << 16); if (v & 0x800000) v -= 0x1000000; v = v >> 8; }
        else v = R.i32(o, true) >> 16;
        out[c][i] = v;
      }
    }
    return [out, note];
  }
  function isqrt(n) {
    var r = Math.floor(Math.sqrt(n));
    while (r * r > n) r--;
    while ((r + 1) * (r + 1) <= n) r++;
    return r;
  }
  function analyzePcm(channels, rate) {
    var n = channels.length ? channels[0].length : 0, nch = channels.length, i, j, k, c;
    var out = { frames: n, duration_ms: rate ? fdiv(n * 1000, rate) : 0, digital_silence: [], discontinuities: [],
      noise_floor_shifts: [], clipped_samples: 0, peak: 0, channel_relation: 'mono' };
    if (n === 0 || rate <= 0) return out;
    var mix;
    if (nch === 1) mix = channels[0];
    else { mix = new Array(n); for (i = 0; i < n; i++) { var s = 0; for (c = 0; c < nch; c++) s += channels[c][i]; mix[i] = fdiv(s, nch); } }
    var peak = 0, clipped = 0;
    for (c = 0; c < nch; c++) for (i = 0; i < n; i++) { var a = Math.abs(channels[c][i]); if (a > peak) peak = a; if (a >= 32767) clipped++; }
    out.peak = peak; out.clipped_samples = clipped;
    if (nch === 2) {
      var L = channels[0], Rr = channels[1], same = true, inv = true;
      for (i = 0; i < n; i++) { if (L[i] !== Rr[i]) same = false; if (L[i] !== -Rr[i]) inv = false; }
      out.channel_relation = same ? 'identical' : inv ? 'inverted' : 'independent';
    } else if (nch > 2) out.channel_relation = 'multichannel';
    function silentAt(x) { for (var q = 0; q < nch; q++) if (channels[q][x] !== 0) return false; return true; }
    var minRun = Math.max(1, fdiv(rate * 10, 1000)), runs = [];
    i = 0;
    while (i < n) {
      if (silentAt(i)) { j = i; while (j < n && silentAt(j)) j++; if (j - i >= minRun && i > 0 && j < n) runs.push([i, j]); i = j; }
      else i++;
    }
    out.digital_silence = runs.slice(0, MAX_EVENTS).map(function (r) { return [fdiv(r[0] * 1000, rate), fdiv(r[1] * 1000, rate)]; });
    var steps = new Array(n).fill(0);
    for (k = 1; k < n; k++) steps[k] = Math.abs(mix[k] - mix[k - 1]);
    var prefix = new Array(n + 1); prefix[0] = 0;
    for (k = 0; k < n; k++) prefix[k + 1] = prefix[k] + steps[k];
    var edges = new Set();
    runs.forEach(function (r) { [r[0], r[0] + 1, r[1], r[1] + 1].forEach(function (e) { edges.add(e); }); });
    var hits = [], thr = fdiv(FULL_SCALE, 4);
    for (k = 1; k < n; k++) {
      var st = steps[k];
      if (st < thr || edges.has(k)) continue;
      var lo = Math.max(1, k - STEP_WINDOW), hi = Math.min(n, k + STEP_WINDOW + 1);
      var nb = (prefix[hi] - prefix[lo]) - st, cnt = (hi - lo) - 1;
      if (cnt > 0 && st * cnt > 8 * nb) hits.push(k);
    }
    var grouped = [], gap = Math.max(1, fdiv(rate, 100));
    hits.forEach(function (h) { if (!grouped.length || h - grouped[grouped.length - 1] > gap) grouped.push(h); });
    out.discontinuities = grouped.slice(0, MAX_EVENTS).map(function (h) { return fdiv(h * 1000, rate); });
    var win = Math.max(1, fdiv(rate, 10)), rms = [];
    for (var start = 0; start + win <= n; start += win) {
      var acc = 0;
      for (k = start; k < start + win; k++) acc += mix[k] * mix[k];
      rms.push(isqrt(fdiv(acc, win)));
    }
    if (rms.length >= 20) {
      var ordered = rms.slice().sort(function (x, y) { return x - y; });
      var ceil = ordered[fdiv(3 * ordered.length, 4)], floors = [];
      for (var s2 = 0; s2 + 9 < rms.length; s2 += 10) floors.push(Math.min.apply(null, rms.slice(s2, s2 + 10)));
      for (k = 0; k + 1 < floors.length; k++) {
        var fa = floors[k], fb = floors[k + 1];
        if (fa === 0 || fb === 0) continue;
        var hiF = Math.max(fa, fb), loF = Math.min(fa, fb);
        if (hiF >= 4 * loF && hiF <= ceil) out.noise_floor_shifts.push({ at_ms: (k + 1) * 1000, from: fa, to: fb });
      }
    }
    return out;
  }
  function audioIndicators(m) {
    var out = [], spans, spots;
    if (m.digital_silence.length) {
      spans = m.digital_silence.map(function (r) { return r[0] + '-' + r[1] + ' ms'; }).join(', ');
      out.push(Indicator({
        code: 'AUDIO.DIGITAL_SILENCE', category: 'AUDIO', title: 'Exact digital silence inside the recording',
        evidence: 'all channels exactly zero for: ' + spans,
        method: 'Run-length scan for exact-zero samples lasting 10 ms or more, excluding the start and end of the file.',
        confidence: 'MODERATE',
        limitation: 'A live microphone almost never outputs exact zeros, but gating, muting and ' +
          'some codecs do. Shows where to listen, not what was removed.',
        alternatives: ['Noise gate or hardware mute', 'Codec silence suppression', 'Deliberate muting of a passage'],
        state: V.REVIEW_REQUIRED, analyzer: AUD, location: spans
      }));
    }
    if (m.discontinuities.length) {
      spots = m.discontinuities.map(function (t) { return t + ' ms'; }).join(', ');
      out.push(Indicator({
        code: 'AUDIO.DISCONTINUITY', category: 'AUDIO', title: 'Abrupt waveform discontinuity (possible splice point)',
        evidence: 'step of at least 1/4 full scale, over 8x the local mean step, at: ' + spots,
        method: 'Sample-to-sample step compared with the mean step of 32 samples either side.', confidence: 'LOW',
        limitation: 'Sharp transients such as clicks, knocks and plosives produce the same step. ' +
          'Needs listening and spectral review at each point.',
        alternatives: ['Percussive transient', 'Microphone bump or cable click', 'Recovery from clipping', 'Dropout during capture'],
        state: V.REVIEW_REQUIRED, analyzer: AUD, location: spots
      }));
    }
    if (m.noise_floor_shifts.length) {
      spots = m.noise_floor_shifts.map(function (s) { return s.at_ms + ' ms'; }).join(', ');
      out.push(Indicator({
        code: 'AUDIO.NOISE_FLOOR_SHIFT', category: 'AUDIO', title: 'Background-noise level changes abruptly',
        evidence: 'quietest-100-ms level changes 4x or more between adjacent seconds at: ' + spots,
        method: 'Per-second minimum of 100 ms RMS windows, compared across adjacent seconds.', confidence: 'LOW',
        limitation: 'Room-tone changes can come from real events. The test cannot tell a join ' +
          'between two recordings from a change in the room.',
        alternatives: ['HVAC, traffic or machinery switching on or off', 'Automatic gain control',
          'Speaker moving relative to the microphone'],
        state: V.REVIEW_REQUIRED, analyzer: AUD, location: spots
      }));
    }
    var total = m.frames * Math.max(1, m.channels === undefined ? 1 : m.channels);
    if (total && m.clipped_samples * 1000 > total) {
      out.push(Indicator({
        code: 'AUDIO.CLIPPING', category: 'AUDIO', title: 'Clipping above 0.1% of samples',
        evidence: m.clipped_samples + ' of ' + total + ' samples at full scale',
        method: 'Count of samples at digital full scale.', confidence: 'HIGH',
        limitation: 'A recording-quality issue, not a manipulation signal. It degrades the discontinuity test.',
        alternatives: ['Input gain set too high'], state: V.NORMAL, analyzer: AUD
      }));
    }
    return out;
  }
  function analyzeAudio(data, mime) {
    var result = { analyzer: AUD, metadata: {}, indicators: [], observations: [], not_performed: AUD_NOT_PERFORMED.slice(), metrics: null };
    if (mime !== 'audio/wav') {
      result.not_performed.push('Sample analysis of ' + mime + ' (no decoder in the reference engine; the browser ' +
        'console decodes it with the Web Audio API)');
      return result;
    }
    var info, dec;
    try { info = parseWav(data); dec = decodeSamples(data, info); } catch (e) {
      if (!(e instanceof ParseError || e instanceof StructError)) throw e;
      result.indicators.push(parseErrorIndicator(parseMessage(e), AUD));
      return result;
    }
    var f = info.fmt, m = analyzePcm(dec[0], f.sample_rate);
    m.channels = f.channels;
    result.metrics = m;
    result.metadata = { format: 'wav', codec: f.format === 3 ? 'float32' : 'pcm' + f.bits, sample_rate: f.sample_rate,
      channels: f.channels, bits: f.bits, duration_ms: m.duration_ms, info_tags: info.info_tags,
      chunks: info.chunks.map(function (c) { return c.id; }), note: dec[1] };
    var inds = result.indicators;
    if (info.riff_size + 8 !== info.file_size || info.data_truncated) {
      inds.push(Indicator({
        code: 'CONTAINER.SIZE_MISMATCH', category: 'CONTAINER', title: 'RIFF size fields disagree with the file length',
        evidence: 'RIFF declares ' + (info.riff_size + 8) + ' bytes; file is ' + info.file_size +
          (info.data_truncated ? '; data chunk is truncated' : ''),
        method: 'RIFF header and chunk-size consistency check.', confidence: 'HIGH',
        limitation: 'Shows the file was truncated, extended or rewritten without fixing headers; not what changed.',
        alternatives: ['Interrupted recording or transfer', 'Tool that appends data'],
        state: V.REVIEW_REQUIRED, analyzer: AUD
      }));
    }
    Array.prototype.push.apply(inds, softwareIndicators('RIFF INFO ISFT', info.info_tags.ISFT || '', AUD));
    Array.prototype.push.apply(inds, audioIndicators(m));
    var created = pyStrip(info.info_tags.ICRD || '');
    var mm = /^(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2}(?::\d{2})?))?$/.exec(created);
    if (mm) result.observations.push({ dimension: 'time', value: mm[1] + (mm[2] ? 'T' + mm[2] : ''), basis: 'RIFF INFO ICRD (unsigned metadata)' });
    return result;
  }

  // ------------------------------------------------------------------
  // timeline (truth_forensics/timeline.py)
  // ------------------------------------------------------------------
  var TL_LABELS = { NORMAL: 'NORMAL', REVIEW_REQUIRED: 'REVIEW', ANOMALY_DETECTED: 'ANOMALY', SUPPORTED: 'SUPPORTED' };
  function runsFromTimestamps(st) {
    var runs = [];
    for (var i = 0; i + 1 < st.length; i++) {
      var d = st[i + 1] - st[i];
      if (runs.length && runs[runs.length - 1][1] === d) runs[runs.length - 1][0]++;
      else runs.push([1, d]);
    }
    return runs;
  }
  function nominalDelta(runs) {
    var totals = new Map();
    runs.forEach(function (r) { if (r[1] > 0) totals.set(r[1], (totals.get(r[1]) || 0) + r[0]); });
    var best = 0, bestT = -1;
    totals.forEach(function (t, d) { if (t > bestT || (t === bestT && d < best)) { best = d; bestT = t; } });
    return best;
  }
  function classify(delta, nominal) {
    if (delta < 0) return [V.ANOMALY_DETECTED, 'time runs backwards (non-monotonic)'];
    if (delta === 0) return [V.ANOMALY_DETECTED, 'duplicate timestamp'];
    if (2 * delta >= 3 * nominal) return [V.ANOMALY_DETECTED, 'gap of about ' + (fdiv(delta + fdiv(nominal, 2), nominal) - 1) + ' frame interval(s)'];
    if (Math.abs(delta - nominal) * 10 <= nominal) return [V.NORMAL, 'nominal interval'];
    return [V.REVIEW_REQUIRED, 'irregular frame interval'];
  }
  function buildTimeline(runs, timescale, supported) {
    var nominal = nominalDelta(runs);
    var out = { timescale: timescale, nominal_delta: nominal, fps_x100: 0,
      intervals: runs.reduce(function (s, r) { return s + r[0]; }, 0), segments: [], gaps: 0, duplicates: 0, backwards: 0, irregular: 0 };
    if (!runs.length || timescale <= 0 || nominal <= 0) return out;
    out.fps_x100 = fdiv(timescale * 100 * 2 + nominal, 2 * nominal);
    var raw = [], t = 0;
    runs.forEach(function (r) {
      var count = r[0], delta = r[1], cr = classify(delta, nominal), state = cr[0], reason = cr[1];
      if (state === V.ANOMALY_DETECTED) out[delta > 0 ? 'gaps' : delta === 0 ? 'duplicates' : 'backwards'] += count;
      else if (state === V.REVIEW_REQUIRED) out.irregular += count;
      var start = t; t += count * delta;
      var lo = t >= start ? start : t, hi = t >= start ? t : start;
      var a = fdiv(lo * 1000, timescale), b = fdiv(hi * 1000, timescale), last = raw[raw.length - 1];
      if (last && last.state === state && last.reason === reason && last.end_ms === a) last.end_ms = b;
      else raw.push({ start_ms: a, end_ms: b, state: state, reason: reason });
    });
    var wins = (supported || []).slice().sort(tupleCmp);
    var segs = overlay(raw, wins);
    segs.forEach(function (s) { s.label = TL_LABELS[s.state]; });
    out.segments = segs;
    return out;
  }
  function overlay(segments, windows) {
    if (!windows.length) return segments;
    var out = [];
    segments.forEach(function (seg) {
      if (seg.state !== V.NORMAL) { out.push(seg); return; }
      var cuts = new Set([seg.start_ms, seg.end_ms]);
      windows.forEach(function (w) { w.forEach(function (edge) { if (seg.start_ms < edge && edge < seg.end_ms) cuts.add(edge); }); });
      var pts = Array.from(cuts).sort(function (x, y) { return x - y; });
      for (var i = 0; i + 1 < pts.length; i++) {
        var a = pts[i], b = pts[i + 1];
        var covered = windows.some(function (w) { return w[0] <= a && b <= w[1]; });
        var piece = { start_ms: a, end_ms: b, state: covered ? V.SUPPORTED : V.NORMAL,
          reason: covered ? 'nominal interval; covered by an independent channel' : seg.reason };
        var last = out[out.length - 1];
        if (last && last.state === piece.state && last.end_ms === a && last.reason === piece.reason) last.end_ms = b;
        else out.push(piece);
      }
    });
    return out;
  }
  function fmtMs(ms) {
    var sign = ms < 0 ? '-' : ''; ms = Math.abs(ms);
    return sign + pad(fdiv(ms, 60000), 2) + ':' + pad(fdiv(ms, 1000) % 60, 2) + '.' + pad(ms % 1000, 3);
  }

  // ------------------------------------------------------------------
  // video (truth_forensics/video.py)
  // ------------------------------------------------------------------
  var VID = 'video@' + VER, EPOCH_1904 = 2082844800, MAX_BOXES = 200000, MAX_DEPTH = 16, MAX_STTS = 2000000;
  var CONTAINERS = ['moov', 'trak', 'mdia', 'minf', 'stbl', 'edts', 'udta', 'dinf', 'ilst', 'moof', 'traf', 'mvex'];
  var TEXT_TAGS = [['©too', 'encoder'], ['©swr', 'encoder'], ['©day', 'date'], ['©xyz', 'location']];
  var TEXT_TAG_NAMES = TEXT_TAGS.map(function (t) { return t[0]; });
  var VID_NOT_PERFORMED = [
    'Optical-flow and motion-consistency analysis (not implemented)',
    'Face / identity and object-persistence tracking (not implemented)',
    'Lighting-consistency analysis (not implemented)',
    'Frame decoding in the reference engine (container timing only)'];
  function macTime(v) {
    if (!v) return '';
    var d = new Date((v - EPOCH_1904) * 1000);
    var y = d.getUTCFullYear();
    if (!isFinite(y) || y < 1 || y > 9999) return '';
    return pad(y, 4) + '-' + pad(d.getUTCMonth() + 1, 2) + '-' + pad(d.getUTCDate(), 2) + 'T' +
      pad(d.getUTCHours(), 2) + ':' + pad(d.getUTCMinutes(), 2) + ':' + pad(d.getUTCSeconds(), 2);
  }
  function walk(data, start, end, depth, counter) {
    var boxes = [], pos = start, R = new Reader(data);
    while (pos + 8 <= end) {
      counter[0]++;
      if (counter[0] > MAX_BOXES) throw new ParseError('implausible box count');
      var size = R.u32(pos), btype = latin1(data, pos + 4, pos + 8), header = 8;
      if (size === 1) {
        if (pos + 16 > end) throw new ParseError('64-bit box size truncated');
        size = R.u64(pos + 8); header = 16;
      } else if (size === 0) size = end - pos;
      if (size < header || pos + size > end) throw new ParseError('box ' + quote(btype) + ' at offset ' + pos + ' overruns its parent');
      var box = { type: btype, offset: pos, size: size, header: header, children: [] }, body = pos + header;
      if (depth < MAX_DEPTH) {
        if (CONTAINERS.indexOf(btype) >= 0) box.children = walk(data, body, pos + size, depth + 1, counter);
        else if (btype === 'meta' && pos + size - body >= 4) box.children = walk(data, body + 4, pos + size, depth + 1, counter);
        else if (TEXT_TAG_NAMES.indexOf(btype) >= 0 && pos + size - body >= 16 && eqBytes(data, body + 4, 'data')) {
          box.children = walk(data, body, pos + size, depth + 1, counter);
        }
      }
      boxes.push(box);
      pos += size;
    }
    return boxes;
  }
  function findBox(boxes, t) { for (var i = 0; i < boxes.length; i++) if (boxes[i].type === t) return boxes[i]; return null; }
  function allBoxes(boxes, t) {
    var out = [];
    boxes.forEach(function (b) { if (b.type === t) out.push(b); Array.prototype.push.apply(out, allBoxes(b.children, t)); });
    return out;
  }
  function boxBody(data, b) { return data.subarray(b.offset + b.header, b.offset + b.size); }
  function fullHeader(body) { if (body.length < 4) throw new ParseError('full box too short'); return body[0]; }
  function parseMvhd(body) {
    var v = fullHeader(body), R = new Reader(body.subarray(4));
    if (v === 1) return { creation: R.u64(0), modification: R.u64(8), timescale: R.u32(16), duration: R.u64(20) };
    return { creation: R.u32(0), modification: R.u32(4), timescale: R.u32(8), duration: R.u32(12) };
  }
  function parseMdhd(body) { var m = parseMvhd(body); return { timescale: m.timescale, duration: m.duration }; }
  function parseTkhd(body) {
    var v = fullHeader(body), R = new Reader(body), id, tail;
    if (v === 1) { id = new Reader(body.subarray(20, 24)).u32(0); tail = 4 + 8 + 8 + 4 + 4 + 8 + 8 + 2 + 2 + 2 + 2 + 36; }
    else { id = new Reader(body.subarray(12, 16)).u32(0); tail = 4 + 4 + 4 + 4 + 4 + 4 + 8 + 2 + 2 + 2 + 2 + 36; }
    var w = 0, h = 0;
    if (body.length >= tail + 8) { w = R.u32(tail); h = R.u32(tail + 4); }
    return { track_id: id, width: w >>> 16, height: h >>> 16 };
  }
  function parseStts(body) {
    fullHeader(body);
    var R = new Reader(body), count = new Reader(body.subarray(4, 8)).u32(0);
    if (count > MAX_STTS || 8 + 8 * count > body.length) throw new ParseError('stts entry table out of range');
    var out = [];
    for (var i = 0; i < count; i++) out.push([R.u32(8 + 8 * i), R.u32(12 + 8 * i)]);
    return out;
  }
  function parseElst(body) {
    var v = fullHeader(body), R = new Reader(body), count = new Reader(body.subarray(4, 8)).u32(0), size = v === 1 ? 20 : 12;
    if (count > 10000 || 8 + size * count > body.length) throw new ParseError('elst entry table out of range');
    var out = [];
    for (var i = 0; i < count; i++) {
      var p = 8 + size * i;
      out.push(v === 1 ? { segment_duration: R.u64(p), media_time: R.i64(p + 8) } : { segment_duration: R.u32(p), media_time: R.i32(p + 4) });
    }
    return out;
  }
  function tagText(data, box) {
    var body = boxBody(data, box);
    if (box.children.length) { var d = findBox(box.children, 'data'); if (d) return pySlice(utf8(boxBody(data, d).subarray(8)), 400); }
    if (body.length >= 4) { var ln = new Reader(body).u16(0); return pySlice(utf8(body.subarray(4, 4 + ln)), 400); }
    return '';
  }
  function iso6709(value) {
    var m = /^([+-]\d{1,3}(?:\.\d+)?)([+-]\d{1,3}(?:\.\d+)?)/.exec(pyStrip(value));
    if (!m) return '';
    function five(s) {
      var sign = s[0] === '-' ? '-' : '', body = s.replace(/^[+-]+/, ''), dot = body.indexOf('.');
      var whole = dot < 0 ? body : body.slice(0, dot), frac = dot < 0 ? '' : body.slice(dot + 1);
      return sign + parseInt(whole, 10) + '.' + (frac + '00000').slice(0, 5);
    }
    return five(m[1]) + ',' + five(m[2]);
  }
  function parseBmff(data) {
    var info = { brands: [], movie: null, tracks: [], tags: {}, fragmented: false, top_level: [], parse_error: '' }, boxes;
    try { boxes = walk(data, 0, data.length, 0, [0]); } catch (e) {
      if (!(e instanceof ParseError || e instanceof StructError)) throw e;
      info.parse_error = parseMessage(e); return info;
    }
    info.top_level = boxes.map(function (b) { return b.type; });
    try {
      var ftyp = findBox(boxes, 'ftyp');
      if (ftyp) {
        var fb = boxBody(data, ftyp), brands = [latin1(fb, 0, 4)];
        for (var i = 8; i < fb.length - 3; i += 4) brands.push(latin1(fb, i, i + 4));
        info.brands = brands;
      }
      var moov = findBox(boxes, 'moov');
      info.fragmented = boxes.some(function (b) { return b.type === 'moof'; });
      if (!moov) throw new ParseError('no moov box');
      var mvhd = findBox(moov.children, 'mvhd');
      if (mvhd) info.movie = parseMvhd(boxBody(data, mvhd));
      moov.children.filter(function (b) { return b.type === 'trak'; }).forEach(function (trak) {
        var t = { handler: '', timescale: 0, duration: 0, stts: [], sync_samples: null, ctts: false, edits: [], width: 0, height: 0, track_id: 0 };
        var tk = findBox(trak.children, 'tkhd');
        if (tk) Object.assign(t, parseTkhd(boxBody(data, tk)));
        allBoxes(trak.children, 'mdhd').forEach(function (b) { Object.assign(t, parseMdhd(boxBody(data, b))); });
        allBoxes(trak.children, 'hdlr').forEach(function (b) { t.handler = latin1(boxBody(data, b), 8, 12); });
        allBoxes(trak.children, 'stts').forEach(function (b) { t.stts = parseStts(boxBody(data, b)); });
        allBoxes(trak.children, 'stss').forEach(function (b) { t.sync_samples = new Reader(boxBody(data, b).subarray(4, 8)).u32(0); });
        t.ctts = allBoxes(trak.children, 'ctts').length > 0;
        allBoxes(trak.children, 'elst').forEach(function (b) { t.edits = parseElst(boxBody(data, b)); });
        info.tracks.push(t);
      });
      TEXT_TAGS.forEach(function (tt) {
        // Parsed even when the key is already set: Python's setdefault evaluates it too.
        allBoxes(boxes, tt[0]).forEach(function (b) { var txt = tagText(data, b); if (!(tt[1] in info.tags)) info.tags[tt[1]] = txt; });
      });
    } catch (e2) {
      if (!(e2 instanceof ParseError || e2 instanceof StructError)) throw e2;
      info.parse_error = parseMessage(e2);
    }
    return info;
  }
  function analyzeVideo(data, mime) {
    var result = { analyzer: VID, metadata: {}, indicators: [], observations: [], not_performed: VID_NOT_PERFORMED.slice(), timeline: null };
    if (['video/mp4', 'video/quicktime', 'audio/mp4'].indexOf(mime) < 0) {
      result.not_performed.push('Container analysis of ' + mime + ' (not implemented)'); return result;
    }
    var info = parseBmff(data), inds = result.indicators;
    if (info.parse_error) inds.push(parseErrorIndicator(info.parse_error, VID));
    var movie = info.movie || {};
    var created = macTime(movie.creation || 0), modified = macTime(movie.modification || 0);
    var durationMs = movie.timescale ? fdiv((movie.duration || 0) * 1000, movie.timescale) : 0;
    var video = info.tracks.filter(function (t) { return t.handler === 'vide'; })[0] || null;
    var audio = info.tracks.filter(function (t) { return t.handler === 'soun'; })[0] || null;
    function trackMs(t) { return (!t || !t.timescale) ? null : fdiv(t.duration * 1000, t.timescale); }
    result.metadata = { format: 'iso-bmff', brands: info.brands, created: created, modified: modified, duration_ms: durationMs,
      tracks: info.tracks.map(function (t) { return { handler: t.handler, timescale: t.timescale, duration_ms: trackMs(t),
        width: t.width, height: t.height, edits: t.edits.length, sync_samples: t.sync_samples }; }),
      tags: info.tags, fragmented: info.fragmented };
    if (video && video.stts.length) {
      var tl = buildTimeline(video.stts, video.timescale, null);
      result.timeline = tl;
      result.frame_runs = video.stts.map(function (r) { return [r[0], r[1]]; });
      Array.prototype.push.apply(inds, timelineIndicators(tl));
    } else if (video === null && !info.parse_error) result.not_performed.push('Frame-timing analysis (no video track)');
    var vMs = trackMs(video), aMs = trackMs(audio);
    if (vMs !== null && aMs !== null && Math.abs(vMs - aMs) > 200) {
      var diff = Math.abs(vMs - aMs);
      inds.push(Indicator({
        code: 'TEMPORAL.TRACK_DURATION_MISMATCH', category: 'TEMPORAL', title: 'Audio and video tracks differ in length',
        evidence: 'video track ' + vMs + ' ms; audio track ' + aMs + ' ms (difference ' + diff + ' ms)',
        method: 'Comparison of media-header durations for the video and sound tracks.',
        confidence: diff > 1000 ? 'MODERATE' : 'LOW',
        limitation: 'Edit lists can realign tracks at playback, and some devices start audio ' +
          'early. Shows a structural difference, not a sync error in what is heard.',
        alternatives: ['Recorder started one track before the other', 'Trim applied to one track only', 'Audio replaced or dubbed'],
        state: V.REVIEW_REQUIRED, analyzer: VID
      }));
    }
    if (video && (video.edits.length > 1 || video.edits.some(function (e) { return e.media_time === -1; }))) {
      inds.push(Indicator({
        code: 'TEMPORAL.EDIT_LIST', category: 'TEMPORAL', title: 'Video track has a non-trivial edit list',
        evidence: video.edits.length + ' edit-list entries; empty edits: ' + video.edits.filter(function (e) { return e.media_time === -1; }).length,
        method: "Parse of the video track's elst box.", confidence: 'LOW',
        limitation: 'Edit lists change what plays without changing stored frames. Their purpose is not recorded.',
        alternatives: ['Encoder start offset', 'Non-destructive trim in an editor'], state: V.REVIEW_REQUIRED, analyzer: VID
      }));
    }
    var c = movie.creation || 0, m = movie.modification || 0;
    if (info.movie && c === 0) {
      inds.push(Indicator({
        code: 'PROVENANCE.NO_CREATION_TIME', category: 'PROVENANCE', title: 'Container creation time is unset',
        evidence: 'mvhd creation_time = 0', method: 'Parse of the movie header.', confidence: 'HIGH',
        limitation: 'Many export tools zero this field. It is a provenance gap only.',
        alternatives: ['Export or remux tool default'], state: V.PROVENANCE_GAP, analyzer: VID
      }));
    } else if (c && m && m - c > 60) {
      inds.push(Indicator({
        code: 'METADATA.MODIFIED_AFTER_CREATION', category: 'METADATA', title: 'Container modified after it was created',
        evidence: 'mvhd creation ' + created + '; modification ' + modified,
        method: 'Comparison of movie-header creation and modification times.', confidence: 'LOW',
        limitation: 'Both fields are unsigned and rewritable. Remuxing or trimming updates the modification time without touching content.',
        alternatives: ['Trim, remux or export', 'Metadata edit'], state: V.REVIEW_REQUIRED, analyzer: VID
      }));
    }
    if (info.tags.encoder) Array.prototype.push.apply(inds, softwareIndicators('encoder tag', info.tags.encoder, VID));
    if (info.fragmented) {
      inds.push(Indicator({
        code: 'CONTAINER.FRAGMENTED', category: 'CONTAINER', title: 'Fragmented MP4: frame timing not fully analysed',
        evidence: 'moof boxes present', method: 'Top-level box inventory.', confidence: 'HIGH',
        limitation: 'Per-fragment timing (trun) is not read, so the timeline is incomplete.',
        alternatives: ['Streaming or live-recording format'], state: V.INCONCLUSIVE, analyzer: VID
      }));
    }
    if (created) {
      result.observations.push({ dimension: 'time', value: created,
        basis: 'MP4 mvhd creation_time (unsigned metadata; UTC by specification, often local time in practice)' });
      if (durationMs) {
        var end = macTime(movie.creation + fdiv(movie.duration, movie.timescale));
        result.observations.push({ dimension: 'time_window', value: created + '/' + end, basis: 'mvhd creation_time plus movie duration' });
      }
    }
    var loc = iso6709(info.tags.location || '');
    if (loc) result.observations.push({ dimension: 'location', value: loc, basis: 'MP4 ©xyz tag (unsigned metadata)' });
    return result;
  }
  function timelineIndicators(tl) {
    var out = [], fps = fdiv(tl.fps_x100, 100) + '.' + pad(tl.fps_x100 % 100, 2);
    var an = tl.segments.filter(function (s) { return s.state === V.ANOMALY_DETECTED; });
    var ir = tl.segments.filter(function (s) { return s.state === V.REVIEW_REQUIRED; });
    if (an.length) {
      var where = an.slice(0, 10).map(function (s) { return fmtMs(s.start_ms) + '-' + fmtMs(s.end_ms) + ' ' + s.reason; }).join('; ');
      out.push(Indicator({
        code: 'TEMPORAL.FRAME_TIMING_ANOMALY', category: 'TEMPORAL', title: 'Frame-timing discontinuity',
        evidence: 'nominal ' + fps + ' fps; ' + where,
        method: 'Frame-interval table compared with the nominal interval (gap >= 1.5x, zero or negative interval).',
        confidence: 'MODERATE',
        limitation: 'Timing tables are rewritten on every remux. A gap estimates missing frames; it ' +
          'cannot distinguish encoder drops from deletion.',
        alternatives: ['Encoder or storage frame drops under load', 'Recording paused and resumed', 'Frames removed in editing'],
        state: V.ANOMALY_DETECTED, analyzer: VID, location: where
      }));
    }
    if (ir.length) {
      var w2 = ir.slice(0, 10).map(function (s) { return fmtMs(s.start_ms) + '-' + fmtMs(s.end_ms); }).join('; ');
      out.push(Indicator({
        code: 'TEMPORAL.IRREGULAR_INTERVALS', category: 'TEMPORAL', title: 'Irregular frame intervals',
        evidence: 'nominal ' + fps + ' fps; intervals more than 10% off nominal at ' + w2,
        method: 'Frame-interval table compared with the nominal interval.', confidence: 'LOW',
        limitation: 'Variable-frame-rate capture is normal on phones; this marks where to look.',
        alternatives: ['Variable-frame-rate capture', 'Frame-rate conversion'], state: V.REVIEW_REQUIRED, analyzer: VID, location: w2
      }));
    }
    return out;
  }

  // ------------------------------------------------------------------
  // events and text (truth_forensics/events.py)
  // ------------------------------------------------------------------
  function isPyInt(v) { return typeof v === 'number' && Number.isInteger(v); }
  function analyzeEvent(data) {
    var result = { analyzer: 'event@' + VER, metadata: {}, indicators: [], observations: [], not_performed: [], custody: [] };
    if (data.length > 1024 * 1024) { result.not_performed.push('event record over 1 MiB; not parsed'); return result; }
    var rec;
    try { rec = JSON.parse(utf8Strict(data)); } catch (e) { result.not_performed.push('event record is not valid JSON'); return result; }
    if (rec === null || typeof rec !== 'object' || Array.isArray(rec)) { result.metadata = { record_type: 'opaque' }; return result; }
    var rtype = pySlice(pyStr(rec.record_type === undefined ? 'opaque' : rec.record_type), 60);
    result.metadata = { record_type: rtype, keys: Object.keys(rec).map(function (k) { return pySlice(k, 60); }).sort(strCmp).slice(0, 50) };
    var obs = result.observations;
    if (rtype === 'sensor-window') {
      var start = pyStr(rec.start === undefined ? '' : rec.start), end = pyStr(rec.end === undefined ? '' : rec.end);
      if (start && end) obs.push({ dimension: 'time_window', value: start + '/' + end, basis: 'sensor log window (structured record)' });
      if (rec.location) obs.push({ dimension: 'location', value: pySlice(pyStr(rec.location), 200), basis: 'sensor log location (structured record)' });
      if (rec.sensor) obs.push({ dimension: 'device', value: pySlice(pyStr(rec.sensor), 200), basis: 'sensor log device id (structured record)' });
    } else if (rtype === 'clock-reference') {
      if (isPyInt(rec.offset_seconds)) {
        obs.push({ dimension: 'clock_offset', value: String(rec.offset_seconds),
          basis: 'clock reference for ' + pySlice(pyStr(rec.device === undefined ? '' : rec.device), 80) + ' (structured record)' });
      }
    } else if (rtype === 'custody-receipt') {
      (Array.isArray(rec.entries) ? rec.entries : []).slice(0, 1000).forEach(function (en) {
        if (en && typeof en === 'object' && !Array.isArray(en) && /^[0-9a-f]{64}$/.test(pyStr(en.sha256 === undefined ? '' : en.sha256))) {
          result.custody.push({ evidence_id: pySlice(pyStr(en.evidence_id === undefined ? '' : en.evidence_id), 80), sha256: en.sha256,
            issued_at: pySlice(pyStr(rec.issued_at === undefined ? '' : rec.issued_at), 40),
            issued_by: pySlice(pyStr(rec.issued_by === undefined ? '' : rec.issued_by), 80) });
        }
      });
    }
    return result;
  }
  function analyzeText(data) {
    var text = utf8(data);
    return { analyzer: 'text@' + VER, metadata: { characters: pyLen(text), lines: (text.match(/\n/g) || []).length + (text ? 1 : 0) },
      indicators: [], observations: [], not_performed: ['Automated fact extraction from text (analyst transcription only)'] };
  }

  // ------------------------------------------------------------------
  // correlation (truth_forensics/correlation.py)
  // ------------------------------------------------------------------
  var AGREES = 'AGREES', CONFLICTS = 'CONFLICTS', NOT_COMPARABLE = 'NOT_COMPARABLE';
  var DIMENSIONS = ['identity', 'event', 'time', 'location', 'device', 'sequence'];
  var NEAR_DUPLICATE_BITS = 10;
  var STOPWORDS = new Set(('a an the of to in on at out from into and or is was are were be been by with for as ' +
    'it its this that shows show showing shown seen near inside outside').split(' '));
  function tokens(text) { return String(text || '').toLowerCase().match(/[a-z0-9]+/g) || []; }
  function stem(w) {
    var suf = ['ing', 'es', 'ed', 's'];
    for (var i = 0; i < suf.length; i++) if (w.length > 4 && w.slice(-suf[i].length) === suf[i]) return w.slice(0, -suf[i].length);
    return w;
  }
  function contentWords(text) { return tokens(text).filter(function (t) { return !STOPWORDS.has(t); }).map(stem); }
  function idLike(tok) { return tok.length === 1 || /[0-9]/.test(tok); }
  function parseTime(value) {
    var m = /^(?:(\d{4}-\d{2}-\d{2}))?(?:[T ]?(\d{2}):(\d{2})(?::(\d{2}))?)?Z?$/.exec(pyStrip(value || ''));
    if (!m || !(m[1] || m[2])) return null;
    if (m[2] === undefined) return [m[1] || '', null, null];
    var h = parseInt(m[2], 10), mi = parseInt(m[3], 10);
    if (h > 23 || mi > 59) return null;
    var start = h * 3600 + mi * 60 + (m[4] ? parseInt(m[4], 10) : 0);
    return [m[1] || '', start, start + (m[4] ? 0 : 59)];
  }
  function timeRange(v) {
    if (v.indexOf('/') >= 0) {
      var i = v.indexOf('/'), a = parseTime(v.slice(0, i)), b = parseTime(v.slice(i + 1));
      return (a && b && a[1] !== null && b[1] !== null) ? [a[0], a[1], b[2]] : null;
    }
    return parseTime(v);
  }
  function compareTime(claim, obs, tol) {
    var a = timeRange(claim), b = timeRange(obs);
    if (!a || !b) return NOT_COMPARABLE;
    if (a[0] && b[0] && a[0] !== b[0]) return CONFLICTS;
    if (a[1] === null || b[1] === null) return (a[0] && a[0] === b[0]) ? AGREES : NOT_COMPARABLE;
    return Math.max(0, a[1] - b[2], b[1] - a[2]) <= tol ? AGREES : CONFLICTS;
  }
  function coords(v) { var m = /^\s*(-?\d{1,3}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)\s*$/.exec(v || ''); return m ? [parseFloat(m[1]), parseFloat(m[2])] : null; }
  function distanceM(a, b) {
    var r = Math.PI / 180, lat = ((a[0] + b[0]) / 2) * r;
    var dx = ((b[1] - a[1]) * r) * Math.cos(lat) * 6371000, dy = ((b[0] - a[0]) * r) * 6371000;
    return Math.floor(Math.sqrt(dx * dx + dy * dy));
  }
  function subset(a, b) { var s = new Set(b); return a.every(function (x) { return s.has(x); }); }
  function compareNames(claim, obs) {
    var p = tokens(claim), o = tokens(obs);
    if (!p.length || !o.length) return NOT_COMPARABLE;
    if (subset(p, o) || subset(o, p)) return AGREES;
    for (var i = 0; i + 1 < p.length; i++) {
      for (var j = 0; j + 1 < o.length; j++) {
        if (o[j] === p[i] && o[j + 1] !== p[i + 1] && idLike(p[i + 1]) && idLike(o[j + 1])) return CONFLICTS;
      }
    }
    return NOT_COMPARABLE;
  }
  function compareLocation(claim, obs, tol) {
    var a = coords(claim), b = coords(obs);
    if (a && b) return distanceM(a, b) <= tol ? AGREES : CONFLICTS;
    if (a || b) return NOT_COMPARABLE;
    return compareNames(claim, obs);
  }
  function compareEvent(claim, obs) {
    var p = new Set(contentWords(claim));
    if (!p.size) return NOT_COMPARABLE;
    var o = new Set(contentWords(obs)), hits = 0;
    p.forEach(function (w) { if (o.has(w)) hits++; });
    return 2 * hits >= p.size ? AGREES : NOT_COMPARABLE;
  }
  function compareSequence(first, second, obs) {
    var steps = obs.split('>').map(pyStrip);
    function index(side) {
      var want = new Set(contentWords(side));
      if (!want.size) return null;
      for (var k = 0; k < steps.length; k++) {
        var have = new Set(contentWords(steps[k])), n = 0;
        want.forEach(function (w) { if (have.has(w)) n++; });
        if (2 * n >= want.size) return k;
      }
      return null;
    }
    var i = index(first), j = index(second);
    if (i === null || j === null || i === j) return NOT_COMPARABLE;
    return i < j ? AGREES : CONFLICTS;
  }
  function compare(dim, cv, obs, tol) {
    if (dim === 'time') return compareTime(cv, obs, tol.time_seconds === undefined ? 120 : tol.time_seconds);
    if (dim === 'location') return compareLocation(cv, obs, tol.location_meters === undefined ? 250 : tol.location_meters);
    if (dim === 'identity' || dim === 'device') return compareNames(cv, obs);
    if (dim === 'event') return compareEvent(cv, obs);
    if (dim === 'sequence') return compareSequence(cv[0], cv[1], obs);
    return NOT_COMPARABLE;
  }
  function independenceGroups(evidence) {
    var ids = evidence.map(function (e) { return e.evidence_id; }).sort(strCmp), parent = {};
    ids.forEach(function (i) { parent[i] = i; });
    function find(x) { while (parent[x] !== x) { parent[x] = parent[parent[x]]; x = parent[x]; } return x; }
    function union(a, b) { var ra = find(a), rb = find(b); if (ra !== rb) { if (rb < ra) { var t = ra; ra = rb; rb = t; } parent[rb] = ra; } }
    var byId = {}; evidence.forEach(function (e) { byId[e.evidence_id] = e; });
    var ord = ids.map(function (i) { return byId[i]; }), rel = [];
    for (var i = 0; i < ord.length; i++) {
      for (var j = i + 1; j < ord.length; j++) {
        var a = ord[i], b = ord[j];
        if (a.content_sha256 && a.content_sha256 === b.content_sha256) { rel.push({ a: a.evidence_id, b: b.evidence_id, reason: 'DUPLICATE_CONTENT' }); union(a.evidence_id, b.evidence_id); }
        else if (a.upstream_source && a.upstream_source === b.upstream_source) { rel.push({ a: a.evidence_id, b: b.evidence_id, reason: 'SHARED_UPSTREAM' }); union(a.evidence_id, b.evidence_id); }
        else if (a.perceptual_hash && b.perceptual_hash) {
          var bits = hammingHex(a.perceptual_hash, b.perceptual_hash);
          if (bits <= NEAR_DUPLICATE_BITS) { rel.push({ a: a.evidence_id, b: b.evidence_id, reason: 'NEAR_DUPLICATE_IMAGE (' + bits + '/64 bits differ)' }); union(a.evidence_id, b.evidence_id); }
        }
      }
    }
    ord.forEach(function (e) { if (e.parent_id && Object.prototype.hasOwnProperty.call(parent, e.parent_id)) { rel.push({ a: e.parent_id, b: e.evidence_id, reason: 'DERIVATIVE_OF' }); union(e.parent_id, e.evidence_id); } });
    var roots = uniqSorted(ids.map(find)), names = {};
    roots.forEach(function (r, k) { names[r] = 'G' + (k + 1); });
    var membership = {}; ids.forEach(function (i) { membership[i] = names[find(i)]; });
    var groups = roots.map(function (r) { return { group: names[r], members: ids.filter(function (i) { return find(i) === r; }) }; });
    rel.sort(function (x, y) { return tupleCmp([x.a, x.b, x.reason], [y.a, y.b, y.reason]); });
    return { membership: membership, groups: groups, relations: rel };
  }
  function corroborationMatrix(evidence, observations, membership, tol) {
    var ids = evidence.map(function (e) { return e.evidence_id; }).sort(strCmp), grid = {};
    ids.forEach(function (i) {
      grid[i] = {};
      DIMENSIONS.forEach(function (d) {
        grid[i][d] = uniqSorted((observations[i] || []).filter(function (o) { return o.dimension === d || (d === 'time' && o.dimension === 'time_window'); }).map(function (o) { return o.value; }));
      });
    });
    var pairs = [];
    for (var x = 0; x < ids.length; x++) {
      for (var y = x + 1; y < ids.length; y++) {
        var a = ids[x], b = ids[y];
        DIMENSIONS.forEach(function (dim) {
          var va = grid[a][dim], vb = grid[b][dim];
          if (!va.length || !vb.length || dim === 'sequence') return;
          var res = new Set();
          va.forEach(function (p) { vb.forEach(function (q) { res.add(compare(dim, p, q, tol)); }); });
          res.delete(NOT_COMPARABLE);
          if (!res.size) return;
          pairs.push({ a: a, b: b, dimension: dim, relation: res.size > 1 ? 'MIXED' : Array.from(res)[0], independent: membership[a] !== membership[b] });
        });
      }
    }
    var ind = pairs.filter(function (p) { return p.independent; });
    return {
      grid: grid, pairs: pairs,
      summary: { agreeing: ind.filter(function (p) { return p.relation === AGREES; }).length,
        conflicting: ind.filter(function (p) { return p.relation === CONFLICTS || p.relation === 'MIXED'; }).length,
        dependent: pairs.filter(function (p) { return !p.independent; }).length },
      missing: DIMENSIONS.filter(function (d) { return !ids.some(function (i) { return grid[i][d].length; }); }),
      temporal_conflicts: ind.filter(function (p) { return p.dimension === 'time' && (p.relation === CONFLICTS || p.relation === 'MIXED'); })
    };
  }

  // ------------------------------------------------------------------
  // claims (truth_forensics/claims.py)
  // ------------------------------------------------------------------
  var MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
  var MONTH_ALT = MONTHS.map(function (m) { return m[0].toUpperCase() + m.slice(1); }).join('|');
  var W = "[A-Za-z0-9_\\u00C0-\\u024F'-]", CAP = '[A-Z\\u00C0-\\u00DE]', CAPNUM = '[A-Z0-9\\u00C0-\\u00DE]';
  var TIME_RE = /\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\b/dg;
  var ISO_DATE_RE = /\b(\d{4})-(\d{2})-(\d{2})\b/d;
  var DMY_RE = new RegExp('\\b(\\d{1,2})\\s+(' + MONTH_ALT + ')\\s+(\\d{4})\\b', 'd');
  var MDY_RE = new RegExp('\\b(' + MONTH_ALT + ')\\s+(\\d{1,2}),?\\s+(\\d{4})\\b', 'd');
  var SOURCE_RE = /\b(video|footage|clip|recording|photo|photograph|image|picture|screenshot|audio|document|log|timeline|email|post)\s+([A-Za-z0-9][A-Za-z0-9_-]{0,30})\b/dgi;
  var EVID_RE = /\bEV-[A-Z0-9-]+\b/dg;
  var LOC_RE = new RegExp('\\b(?:[Aa]t|[Ii]n|[Nn]ear|[Oo]utside|[Ii]nside|[Oo]ut of|[Ff]rom|[Ii]nto)\\s+' +
    '((?:the\\s+)?' + CAP + W + '*(?:\\s+(?:' + CAPNUM + W + '*|of|and))*)', 'dg');
  var IDENT_RE = new RegExp('\\bshows?\\s+((?:the\\s+)?' + CAP + W + '*(?:\\s+' + CAPNUM + W + '*)*)', 'dg');
  var SEEN_RE = new RegExp('\\b(' + CAP + W + '*(?:\\s+' + CAPNUM + W + '*)+)\\s+(?:was|is|were|are)\\s+(?:seen|visible|shown|recorded|heard)\\b', 'dg');
  var SEQ_RE = /^(.*?)\b(before|after|followed by|prior to|then)\b(.*)$/i;
  function stripTail(t) { return pyStrip(t).replace(/\s+(?:of|and)$/, '').replace(/^the\s+/, ''); }
  function capitalize(s) { return s ? s[0].toUpperCase() + s.slice(1).toLowerCase() : s; }
  function allMatches(re, text) { re.lastIndex = 0; return Array.from(text.matchAll(re)); }
  function decompose(claim) {
    var text = pySlice(pySplitWs(claim || '').join(' '), 2000), spans = [], props = [];
    function add(dim, value, statement, method, implicit) {
      props.push({ id: 'P' + (props.length + 1), dimension: dim, value: value, text: statement, method: method, implicit: !!implicit });
    }
    allMatches(SOURCE_RE, text).forEach(function (m) {
      var ident = m[2];
      if (!((ident[0] >= 'A' && ident[0] <= 'Z') || (ident[0] >= '0' && ident[0] <= '9'))) return;
      var label = capitalize(m[1]) + ' ' + ident;
      spans.push(m.indices[0]);
      add('source', label, "The source '" + label + "' is in the evidence set with a hash recorded at acquisition.", 'pattern:source');
    });
    allMatches(EVID_RE, text).forEach(function (m) {
      spans.push(m.indices[0]);
      add('source', m[0], 'Evidence ' + m[0] + ' is in the evidence set.', 'pattern:evidence-id');
    });
    var subjectEnd = null;
    [IDENT_RE, SEEN_RE].forEach(function (rx) {
      allMatches(rx, text).forEach(function (m) {
        var who = stripTail(m[1]);
        if (MONTHS.indexOf(who.toLowerCase()) >= 0 || !who) return;
        spans.push(m.indices[1]);
        if (subjectEnd === null) subjectEnd = m.indices[1][1];
        add('identity', who, 'The subject shown is ' + who + '.', 'pattern:subject');
      });
    });
    var date = '', rxs = [[ISO_DATE_RE, 'ymd'], [DMY_RE, 'dmy'], [MDY_RE, 'mdy']];
    for (var r = 0; r < rxs.length; r++) {
      var dm = rxs[r][0].exec(text);
      if (dm) {
        spans.push(dm.indices[0]);
        if (rxs[r][1] === 'ymd') date = dm[1] + '-' + dm[2] + '-' + dm[3];
        else if (rxs[r][1] === 'dmy') date = dm[3] + '-' + pad(MONTHS.indexOf(dm[2].toLowerCase()) + 1, 2) + '-' + pad(parseInt(dm[1], 10), 2);
        else date = dm[3] + '-' + pad(MONTHS.indexOf(dm[1].toLowerCase()) + 1, 2) + '-' + pad(parseInt(dm[2], 10), 2);
        break;
      }
    }
    var th = allMatches(TIME_RE, text);
    th.forEach(function (m) {
      spans.push(m.indices[0]);
      var clock = pad(parseInt(m[1], 10), 2) + ':' + m[2] + (m[3] ? ':' + m[3] : '');
      var value = date ? date + 'T' + clock : clock;
      add('time', value, 'The event occurred at ' + value.replace('T', ' ') + '.', 'pattern:time');
    });
    if (date && !th.length) add('time', date, 'The event occurred on ' + date + '.', 'pattern:date');
    allMatches(LOC_RE, text).forEach(function (m) {
      var place = stripTail(m[1]);
      if (!place || MONTHS.indexOf(place.toLowerCase()) >= 0 || place.indexOf('EV-') === 0) return;
      var s1 = m.indices[1][0];
      if (spans.some(function (sp) { return sp[0] <= s1 && s1 < sp[1]; })) return;
      spans.push(m.indices[0]);
      add('location', place, 'The location is ' + place + '.', 'pattern:place');
    });
    var seq = SEQ_RE.exec(text);
    if (seq && pyStrip(seq[1]) && pyStrip(seq[3])) {
      var left = stripChars(seq[1], ' ,.'), word = seq[2].toLowerCase(), right = stripChars(seq[3], ' ,.');
      var first = word === 'after' ? right : left, second = word === 'after' ? left : right;
      add('sequence', [first, second], "'" + first + "' happened before '" + second + "'.", 'pattern:sequence');
    }
    if (subjectEnd !== null) {
      var later = spans.map(function (s) { return s[0]; }).filter(function (a) { return a >= subjectEnd; });
      var stop = later.length ? Math.min.apply(null, later) : text.length;
      var what = stripChars(text.slice(subjectEnd, stop), ' ,.');
      if (contentWords(what).length >= 2) add('event', what, 'The event shown is: ' + what + '.', 'pattern:predicate');
    }
    add('provenance', '', 'The source evidence has intact provenance: a hash recorded at acquisition that matches any custody record, and lineage to an original.', 'implicit', true);
    add('corroboration', '', 'At least two independent sources beyond the claimed source agree with the claim.', 'implicit', true);
    return props;
  }
  function verdictFromCounts(a, c) {
    if (a === 0 && c === 0) return V.UNVERIFIED;
    if (a === 0) return V.CONTRADICTED;
    if (c) return V.INCONCLUSIVE;
    return a >= 2 ? V.SUPPORTED : V.PARTIALLY_SUPPORTED;
  }
  function confidenceFor(v, a, c, cav) {
    if (v === V.UNVERIFIED) return 'NONE';
    if (v === V.SUPPORTED) return (a >= 3 && cav === 0) ? 'HIGH' : 'MODERATE';
    if (v === V.CONTRADICTED && c >= 2 && cav === 0) return 'MODERATE';
    return 'LOW';
  }
  function combine(vs) {
    if (!vs.length) return V.UNVERIFIED;
    if (vs.indexOf(V.CONTRADICTED) >= 0) return V.CONTRADICTED;
    if (vs.indexOf(V.INCONCLUSIVE) >= 0) return V.INCONCLUSIVE;
    if (vs.every(function (v) { return v === V.SUPPORTED; })) return V.SUPPORTED;
    if (vs.every(function (v) { return v === V.UNVERIFIED; })) return V.UNVERIFIED;
    return V.PARTIALLY_SUPPORTED;
  }
  function findSources(label, evidence) {
    var want = pyStrip(label).toLowerCase();
    return evidence.filter(function (e) { return e.evidence_id.toLowerCase() === want || pyStrip(e.label || '').toLowerCase() === want; });
  }
  function assess(propositions, ctx) {
    var evidence = ctx.evidence, excluded = ctx.excluded || {}, membership = ctx.membership, results = [], referenced = [];
    propositions.forEach(function (prop) {
      var dim = prop.dimension, res = Object.assign({}, prop, { agreeing: [], conflicting: [], excluded: [], rule: '' });
      if (dim === 'source') {
        var found = findSources(prop.value, evidence);
        Array.prototype.push.apply(referenced, found);
        if (found.length) {
          res.agreeing = found.map(function (e) { return { evidence_id: e.evidence_id, value: e.content_sha256, basis: 'evidence set; SHA-256 recorded at acquisition', group: membership[e.evidence_id] }; });
          res.verdict = V.SUPPORTED; res.confidence = 'HIGH'; res.rule = 'source present with an acquisition hash';
        } else { res.verdict = V.UNVERIFIED; res.confidence = 'NONE'; res.rule = 'no evidence item carries this label'; }
        results.push(res); return;
      }
      if (dim === 'provenance' || dim === 'corroboration') { results.push(res); return; }
      var ag = new Set(), cg = new Set();
      evidence.forEach(function (e) {
        var eid = e.evidence_id;
        var ol = (ctx.observations[eid] || []).filter(function (o) { return o.dimension === dim || (dim === 'time' && o.dimension === 'time_window'); });
        if (!ol.length) return;
        if (Object.prototype.hasOwnProperty.call(excluded, eid)) { res.excluded.push({ evidence_id: eid, reason: excluded[eid] }); return; }
        ol.forEach(function (o) {
          var rel = compare(dim, prop.value, o.value, ctx.tolerances);
          var entry = { evidence_id: eid, value: o.value, basis: o.basis, group: membership[eid] };
          if (rel === AGREES) { res.agreeing.push(entry); ag.add(membership[eid]); }
          else if (rel === CONFLICTS) { res.conflicting.push(entry); cg.add(membership[eid]); }
        });
      });
      var cav = uniqSorted(res.agreeing.concat(res.conflicting).map(function (x) { return x.evidence_id; })
        .filter(function (id) { var c = (ctx.caveated || {})[id]; return c && c.length; }));
      res.verdict = verdictFromCounts(ag.size, cg.size);
      res.confidence = confidenceFor(res.verdict, ag.size, cg.size, cav.length);
      res.caveats = cav;
      res.rule = ag.size + ' agreeing and ' + cg.size + ' conflicting independence group(s)';
      results.push(res);
    });
    var explicit = results.filter(function (r) { return !r.implicit; });
    var targets = referenced.length ? referenced : evidence.filter(function (e) { return !Object.prototype.hasOwnProperty.call(excluded, e.evidence_id); });
    var integrity = ctx.integrity || {};
    results.forEach(function (res) {
      if (res.dimension === 'provenance') {
        var states = {};
        targets.forEach(function (e) { states[e.evidence_id] = integrity[e.evidence_id] || 'NO_RECORD'; });
        var gaps = targets.filter(function (e) { return e.provenance_state === V.PROVENANCE_GAP; }).map(function (e) { return e.evidence_id; });
        var keys = sortedKeys(states);
        res.agreeing = keys.filter(function (k) { return states[k] === 'MATCH'; }).map(function (k) { return { evidence_id: k, value: states[k], basis: 'custody record', group: membership[k] }; });
        res.conflicting = keys.filter(function (k) { return states[k] === 'MISMATCH'; }).map(function (k) { return { evidence_id: k, value: states[k], basis: 'custody record', group: membership[k] }; });
        if (!targets.length) { res.verdict = V.UNVERIFIED; res.rule = 'no evidence to assess'; }
        else if (res.conflicting.length) { res.verdict = V.CONTRADICTED; res.rule = 'hash differs from custody record'; }
        else if (gaps.length) { res.verdict = V.INCONCLUSIVE; res.rule = 'content not acquired: ' + gaps.join(', '); }
        else if (keys.every(function (k) { return states[k] === 'MATCH'; })) { res.verdict = V.SUPPORTED; res.rule = 'acquisition hash matches an earlier custody record'; }
        else { res.verdict = V.PARTIALLY_SUPPORTED; res.rule = 'hash recorded at acquisition; no earlier custody record to compare'; }
        res.confidence = (res.verdict === V.SUPPORTED || res.verdict === V.CONTRADICTED) ? 'HIGH' : res.verdict !== V.UNVERIFIED ? 'LOW' : 'NONE';
        res.caveats = [];
      } else if (res.dimension === 'corroboration') {
        var own = new Set(referenced.map(function (e) { return membership[e.evidence_id]; }));
        var gs = uniqSorted([].concat.apply([], explicit.filter(function (r) { return r.dimension !== 'source'; })
          .map(function (r) { return r.agreeing.map(function (x) { return x.group; }); })).filter(function (g) { return !own.has(g); }));
        var conflicted = explicit.some(function (r) { return r.conflicting.length; });
        res.agreeing = gs.map(function (g) { return { evidence_id: '', value: g, basis: 'independence group', group: g }; });
        if (conflicted) { res.verdict = V.INCONCLUSIVE; res.rule = 'independent sources both agree and conflict'; }
        else {
          res.verdict = gs.length >= 2 ? V.SUPPORTED : gs.length ? V.PARTIALLY_SUPPORTED : V.UNVERIFIED;
          res.rule = gs.length + ' independent group(s) beyond the claimed source agree';
        }
        res.confidence = res.verdict === V.SUPPORTED ? 'MODERATE' : res.verdict === V.UNVERIFIED ? 'NONE' : 'LOW';
        res.caveats = [];
      }
    });
    var overall = combine(results.map(function (r) { return r.verdict; }));
    var conflict = explicit.some(function (r) { return r.agreeing.length && r.conflicting.length; });
    return { verdict: overall,
      state: conflict ? V.CORROBORATION_CONFLICT : (overall !== V.UNVERIFIED ? V.REVIEW_REQUIRED : V.INCONCLUSIVE),
      propositions: results, rule: 'conjunction: contradicted > inconclusive > supported only if all supported' };
  }
  function verifyClaim(claim, ctx) {
    var out = assess(decompose(claim), ctx);
    out.claim = pySlice(pySplitWs(claim || '').join(' '), 2000);
    return out;
  }

  // ------------------------------------------------------------------
  // consistency (truth_forensics/consistency.py)
  // ------------------------------------------------------------------
  var ROWS = [['WHO', ['identity']], ['WHAT', ['event']], ['WHEN', ['time']], ['WHERE', ['location']],
    ['SEQUENCE', ['sequence']], ['HOW', ['device']], ['SOURCE', ['source']], ['PROVENANCE', ['provenance']]];
  var RANK = { NONE: 0, LOW: 1, MODERATE: 2, HIGH: 3 };
  function consistencyMatrix(assessment, ctx) {
    var props = assessment.propositions, rows = [];
    ROWS.forEach(function (row) {
      var label = row[0], chosen = props.filter(function (p) { return row[1].indexOf(p.dimension) >= 0; });
      if (label === 'HOW') { rows.push(howRow(ctx)); return; }
      if (!chosen.length) {
        if (label === 'SEQUENCE') return;
        rows.push({ dimension: label, evidence: [], status: V.UNVERIFIED, confidence: 'NONE', rationale: 'the claim makes no testable statement on this dimension' });
        return;
      }
      var ids = uniqSorted([].concat.apply([], chosen.map(function (p) { return p.agreeing.concat(p.conflicting).map(function (x) { return x.evidence_id; }); })).filter(Boolean));
      var conf = chosen.map(function (p) { return p.confidence; }).reduce(function (m, c) { return RANK[c] < RANK[m] ? c : m; });
      rows.push({ dimension: label, evidence: ids, status: combine(chosen.map(function (p) { return p.verdict; })), confidence: conf,
        rationale: chosen.map(function (p) { return p.id + ' ' + p.verdict + ': ' + p.rule; }).join('; ') });
    });
    return rows;
  }
  function howRow(ctx) {
    var obs = [];
    ctx.evidence.forEach(function (e) {
      if (Object.prototype.hasOwnProperty.call(ctx.excluded || {}, e.evidence_id)) return;
      (ctx.observations[e.evidence_id] || []).forEach(function (o) { if (o.dimension === 'device') obs.push([e.evidence_id, o.value]); });
    });
    if (!obs.length) return { dimension: 'HOW', evidence: [], status: V.UNVERIFIED, confidence: 'NONE', rationale: 'no capture-device observation in any item' };
    var conflicts = [];
    for (var i = 0; i < obs.length; i++) {
      for (var j = i + 1; j < obs.length; j++) {
        var a = obs[i][0], b = obs[j][0];
        if (ctx.membership[a] !== ctx.membership[b] && compare('device', obs[i][1], obs[j][1], ctx.tolerances) === CONFLICTS) conflicts.push(a + ' vs ' + b);
      }
    }
    var ids = uniqSorted(obs.map(function (o) { return o[0]; }));
    if (conflicts.length) return { dimension: 'HOW', evidence: ids, status: V.INCONCLUSIVE, confidence: 'LOW', rationale: 'device observations conflict: ' + conflicts.join(', ') };
    return { dimension: 'HOW', evidence: ids, status: V.PARTIALLY_SUPPORTED, confidence: 'LOW',
      rationale: 'device named in metadata or channel records; unsigned, so it describes the file, not the capture' };
  }

  // ------------------------------------------------------------------
  // bifocal (truth_forensics/bifocal.py)
  // ------------------------------------------------------------------
  var KINDS = ['PRIMARY_MEDIA', 'INDEPENDENT_SENSOR', 'TIME_SOURCE', 'PROVENANCE_RECORD'];
  var ADAPTERS = [
    { id: 'declared_hash', name: 'Custody-record hash comparison', implemented: true },
    { id: 'structured_channel', name: 'Structured channel records (JSON)', implemented: true },
    { id: 'camera_telemetry', name: 'Camera telemetry feed', implemented: false },
    { id: 'rfc3161', name: 'RFC 3161 trusted timestamp tokens', implemented: false },
    { id: 'signature', name: 'Detached cryptographic signatures', implemented: false },
    { id: 'sensor_feed', name: 'Live sensor feeds', implemented: false },
    { id: 'device_attestation', name: 'Device attestation', implemented: false },
    { id: 'c2pa', name: 'C2PA / Content Credentials validation', implemented: false },
    { id: 'secure_log', name: 'Secure / append-only logging systems', implemented: false }];
  function windowOf(v) {
    v = v || '';
    if (v.indexOf('/') < 0) { var t = parseTime(v); return (t && t[1] !== null) ? t : null; }
    var i = v.indexOf('/'), a = parseTime(v.slice(0, i)), b = parseTime(v.slice(i + 1));
    return (a && b && a[1] !== null && b[1] !== null) ? [a[0], a[1], b[2]] : null;
  }
  function bifocalVerify(channels, membership, hashes, tol) {
    var byKind = {};
    channels.forEach(function (ch) { if (KINDS.indexOf(ch.kind) >= 0 && !byKind[ch.kind]) byKind[ch.kind] = ch; });
    var present = KINDS.filter(function (k) { return byKind[k]; }), checks = [], primary = byKind.PRIMARY_MEDIA;
    var out = { channels: present.map(function (k) { return { kind: k, evidence_id: byKind[k].evidence_id || '', label: byKind[k].label || '' }; }),
      coverage: present.length + '/' + KINDS.length, checks: checks, score: null, status: 'INSUFFICIENT_CHANNELS',
      disclaimer: V.BIFOCAL_DISCLAIMER, adapters: ADAPTERS.map(function (a) { return Object.assign({}, a); }) };
    if (!primary || present.length < 2) return out;
    var pid = primary.evidence_id || '';
    function independent(ch) { var cid = ch.evidence_id || ''; return !cid || !(cid in membership) || membership[cid] !== membership[pid]; }
    var sensor = byKind.INDEPENDENT_SENSOR;
    if (sensor) {
      var ind = independent(sensor), pw = windowOf(primary.time_window), sw = windowOf(sensor.time_window);
      if (pw && sw) {
        var ov = (pw[0] === sw[0] || !pw[0] || !sw[0]) && pw[1] <= sw[2] && sw[1] <= pw[2];
        checks.push({ check: 'TIME_OVERLAP', channel: 'INDEPENDENT_SENSOR', result: ov ? AGREES : CONFLICTS, independent: ind,
          detail: 'primary ' + primary.time_window + '; sensor ' + sensor.time_window });
      }
      if (primary.location && sensor.location) {
        var rel = compare('location', sensor.location, primary.location, tol);
        if (rel !== NOT_COMPARABLE) checks.push({ check: 'LOCATION', channel: 'INDEPENDENT_SENSOR', result: rel, independent: ind,
          detail: 'primary ' + quote(primary.location) + '; sensor ' + quote(sensor.location) });
      }
    }
    var clock = byKind.TIME_SOURCE;
    if (clock && isPyInt(clock.offset_seconds)) {
      var off = clock.offset_seconds, lim = tol.clock_seconds === undefined ? 5 : tol.clock_seconds;
      checks.push({ check: 'CLOCK_OFFSET', channel: 'TIME_SOURCE', result: Math.abs(off) <= lim ? AGREES : CONFLICTS, independent: independent(clock),
        detail: 'primary device clock offset ' + (off >= 0 ? '+' : '') + off + ' s against the reference (tolerance ' + lim + ' s)' });
    }
    var record = byKind.PROVENANCE_RECORD;
    if (record && record.declared_sha256) {
      var match = (hashes[pid] || '') === record.declared_sha256;
      checks.push({ check: 'INTEGRITY', channel: 'PROVENANCE_RECORD', result: match ? AGREES : CONFLICTS, independent: independent(record),
        detail: match ? 'SHA-256 matches the custody record' : 'SHA-256 differs from the custody record',
        state: match ? V.CRYPTOGRAPHICALLY_VERIFIED : V.ANOMALY_DETECTED, note: V.CRYPTO_NOTE });
    }
    var scored = checks.filter(function (c) { return c.independent; }), agree = scored.filter(function (c) { return c.result === AGREES; }).length;
    out.score = pct(agree, scored.length);
    out.scored_checks = scored.length;
    out.status = !scored.length ? 'NO_APPLICABLE_CHECKS' : agree === scored.length ? V.NORMAL : V.REVIEW_REQUIRED;
    return out;
  }

  // ------------------------------------------------------------------
  // evidence graph (truth_forensics/graph.py)
  // ------------------------------------------------------------------
  function buildGraph(evidence, observations, analyses, assessment, groups) {
    var nodes = {}, edges = [];
    function nid(k, key) { return k + ':' + key; }
    function node(kind, key, label, extra) {
      var id = nid(kind, key);
      if (!nodes[id]) nodes[id] = Object.assign({ id: id, type: kind, label: label }, extra || {});
      return id;
    }
    function edge(s, r, t, basis, why) { edges.push({ source: s, type: r, target: t, basis: basis, why: why }); }
    evidence.forEach(function (e) {
      var eid = e.evidence_id;
      var ev = node('Evidence', eid, e.label || eid, { sha256: e.content_sha256, object_kind: e.object_kind, demonstration: !!e.demonstration });
      if (e.upstream_source) edge(ev, 'ASSOCIATED_WITH', node('Source', e.upstream_source, e.upstream_source), V.INFERENCE, 'declared upstream source');
      if (e.parent_id) {
        var t = node('Transformation', eid, e.transformation || 'declared transformation');
        edge(ev, 'DERIVED_FROM', nid('Evidence', e.parent_id), V.FACTUAL, 'derivation recorded in the provenance ledger');
        edge(t, 'CREATED', ev, V.FACTUAL, 'transformation recorded at acquisition');
      }
      if (analyses[eid]) edge(ev, 'ANALYZED_BY', node('Analysis', eid, 'analysis of ' + eid, { analyzer: analyses[eid].analyzer || '' }), V.FACTUAL, 'analyzer run recorded in the audit trail');
      (observations[eid] || []).forEach(function (o) {
        var d = o.dimension, v = o.value, b = o.basis;
        if (d === 'device') edge(ev, 'CAPTURED_BY', node('Device', v, v), V.INFERENCE, b);
        else if (d === 'location') edge(ev, 'OCCURRED_AT', node('Location', v, v), V.INFERENCE, b);
        else if (d === 'time' || d === 'time_window') edge(ev, 'OCCURRED_AT', node('Timestamp', v, v), V.INFERENCE, b);
        else if (d === 'identity') edge(node({ person: 'Person', organization: 'Organization' }[o.entity || ''] || 'Subject', v, v), 'ASSOCIATED_WITH', ev, V.INFERENCE, b);
        else if (d === 'event') edge(ev, 'REFERENCES', node('Event', v, v), V.INFERENCE, b);
      });
    });
    (groups.relations || []).forEach(function (r) {
      if (r.reason === 'DUPLICATE_CONTENT') edge(nid('Evidence', r.b), 'DERIVED_FROM', nid('Evidence', r.a), V.FACTUAL, 'identical SHA-256: the same bytes');
    });
    if (assessment) {
      var claim = node('Claim', 'claim', assessment.claim || 'claim', { verdict: assessment.verdict });
      assessment.propositions.forEach(function (p) {
        if (p.dimension === 'source') { p.agreeing.forEach(function (x) { edge(claim, 'REFERENCES', nid('Evidence', x.evidence_id), V.FACTUAL, 'the claim names this item'); }); return; }
        p.agreeing.forEach(function (x) { if (x.evidence_id) edge(nid('Evidence', x.evidence_id), 'SUPPORTS', claim, V.INFERENCE, p.id + ' ' + p.dimension + ': ' + x.basis); });
        p.conflicting.forEach(function (x) { if (x.evidence_id) edge(nid('Evidence', x.evidence_id), 'CONTRADICTS', claim, V.INFERENCE, p.id + ' ' + p.dimension + ': ' + x.basis); });
      });
    }
    var seen = new Set(), uniq = [];
    edges.sort(function (a, b) { return tupleCmp([a.source, a.type, a.target, a.why], [b.source, b.type, b.target, b.why]); }).forEach(function (e) {
      var k = JSON.stringify([e.source, e.type, e.target, e.why]);
      if (!seen.has(k) && nodes[e.source] && nodes[e.target]) { seen.add(k); uniq.push(e); }
    });
    return { nodes: sortedKeys(nodes).map(function (k) { return nodes[k]; }), edges: uniq,
      counts: { factual: uniq.filter(function (e) { return e.basis === V.FACTUAL; }).length, inference: uniq.filter(function (e) { return e.basis === V.INFERENCE; }).length } };
  }

  // ------------------------------------------------------------------
  // provenance ledger (truth_forensics/provenance.py)
  // ------------------------------------------------------------------
  var EVENT_TYPES = ['ACQUIRED', 'TRANSFORMED', 'DERIVED', 'ANALYZED', 'REVIEWED', 'REPORTED'];
  function Ledger() { this.records = []; }
  Ledger.prototype.head = function () { return this.records.length ? this.records[this.records.length - 1].record_hash : GENESIS_HASH; };
  Ledger.prototype.append = async function (event, subject, o) {
    if (EVENT_TYPES.indexOf(event) < 0) throw new Error('unknown provenance event ' + event);
    if (!pyStrip(o.actor || '')) throw new Error('every provenance event needs an actor');
    var body = JSON.parse(canonicalJson({ seq: this.records.length + 1, event: event, subject_id: subject, parent_ids: o.parent_ids || [],
      actor: o.actor, at: o.at, detail: o.detail || {}, software: V.ENGINE_NAME + '/' + VER }));
    var prev = this.head();
    var rec = Object.assign({}, body, { prev_hash: prev, record_hash: await sha256Text(prev + canonicalJson(body)) });
    this.records.push(rec);
    return rec;
  };
  Ledger.prototype.lineage = function (eid) {
    var parents = {};
    this.records.forEach(function (r) { if (r.event === 'DERIVED' && r.parent_ids.length) parents[r.subject_id] = r.parent_ids[0]; });
    var chain = [eid], seen = new Set([eid]);
    while (Object.prototype.hasOwnProperty.call(parents, chain[chain.length - 1])) {
      var n = parents[chain[chain.length - 1]];
      if (seen.has(n)) break;
      chain.push(n); seen.add(n);
    }
    return chain;
  };
  async function verifyRecords(records) {
    var prev = GENESIS_HASH;
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      var body = { seq: r.seq, event: r.event, subject_id: r.subject_id, parent_ids: r.parent_ids, actor: r.actor, at: r.at, detail: r.detail, software: r.software };
      if (r.seq !== i + 1 || r.prev_hash !== prev) return [false, i + 1];
      if (await sha256Text(prev + canonicalJson(body)) !== r.record_hash) return [false, i + 1];
      prev = r.record_hash;
    }
    return [true, null];
  }

  // ------------------------------------------------------------------
  // review (truth_forensics/review.py)
  // ------------------------------------------------------------------
  var ACTIONS = ['ACCEPT', 'REJECT', 'ESCALATE', 'MARK_INCONCLUSIVE', 'ADD_EVIDENCE', 'ANNOTATE', 'COMMENT', 'REQUEST_SECOND_REVIEW'];
  var DECISIVE = ['ACCEPT', 'REJECT', 'MARK_INCONCLUSIVE'];
  function ReviewLog(analyst) { this.analyst = analyst; this.records = []; }
  ReviewLog.prototype.head = function () { return this.records.length ? this.records[this.records.length - 1].record_hash : GENESIS_HASH; };
  ReviewLog.prototype.openSecond = function (target) {
    var req = '';
    this.records.forEach(function (r) {
      if (r.target !== target) return;
      if (r.action === 'REQUEST_SECOND_REVIEW') req = r.reviewer;
      else if (DECISIVE.indexOf(r.action) >= 0 && req && r.reviewer !== req) req = '';
    });
    return req;
  };
  ReviewLog.prototype.record = async function (action, target, reviewer, at, note) {
    note = note || '';
    if (ACTIONS.indexOf(action) < 0) throw new ReviewError("unknown review action '" + action + "'");
    reviewer = pyStrip(reviewer || ''); target = pyStrip(target || '');
    if (!reviewer || !target) throw new ReviewError('a review needs a reviewer and a target');
    if (pyLen(note) > 2000) throw new ReviewError('review note exceeds 2000 characters');
    if (DECISIVE.indexOf(action) >= 0) {
      if (reviewer === this.analyst) throw new ReviewError('separation of duties: the analyst cannot decide their own analysis');
      var pending = this.openSecond(target);
      if (pending && reviewer === pending) throw new ReviewError('a second review must come from a different reviewer');
    }
    var body = { seq: this.records.length + 1, action: action, target: target, reviewer: reviewer, at: at, note: note };
    var prev = this.head();
    var rec = Object.assign({}, body, { prev_hash: prev, record_hash: await sha256Text(prev + canonicalJson(body)) });
    this.records.push(rec);
    return Object.assign({}, rec);
  };
  ReviewLog.prototype.decision = function (target) {
    var last = null, state = 'PENDING';
    this.records.forEach(function (r) {
      if (r.target !== target) return;
      if (DECISIVE.indexOf(r.action) >= 0) { last = r; state = 'DECIDED'; }
      else if (r.action === 'ESCALATE') state = 'ESCALATED';
    });
    if (this.openSecond(target)) state = 'AWAITING_SECOND_REVIEW';
    var d = last && state === 'DECIDED';
    return { state: state, action: d ? last.action : '', reviewer: d ? last.reviewer : '', at: d ? last.at : '', note: d ? last.note : '' };
  };
  ReviewLog.prototype.verify = async function () {
    var prev = GENESIS_HASH;
    for (var i = 0; i < this.records.length; i++) {
      var r = this.records[i], body = { seq: r.seq, action: r.action, target: r.target, reviewer: r.reviewer, at: r.at, note: r.note };
      if (r.prev_hash !== prev || r.record_hash !== await sha256Text(prev + canonicalJson(body))) return [false, i + 1];
      prev = r.record_hash;
    }
    return [true, null];
  };
  async function reviewLogFrom(analyst, records) {
    var log = new ReviewLog(analyst);
    for (var i = 0; i < (records || []).length; i++) {
      var r = records[i];
      await log.record(r.action, r.target, r.reviewer, r.at, r.note || '');
    }
    return log;
  }
  function finalStatus(proposed, d, demo) {
    if (demo) return V.SIMULATED;
    if (d.state === 'PENDING') return proposed === V.VERIFIED ? V.SUPPORTED : proposed;
    if (d.state !== 'DECIDED') return V.INCONCLUSIVE;
    if (d.action === 'REJECT') return V.UNVERIFIED;
    if (d.action === 'MARK_INCONCLUSIVE') return V.INCONCLUSIVE;
    return proposed;
  }

  // ------------------------------------------------------------------
  // case pipeline (truth_forensics/case.py)
  // ------------------------------------------------------------------
  function simpleResult(analyzer, note) {
    return { analyzer: analyzer + '@' + VER, metadata: {}, indicators: [], observations: [], not_performed: [note] };
  }
  async function analyzeItem(rec, data) {
    var mime = rec.mime_sniffed, result;
    try {
      if (rec.processing_boundary === 'HASH_ONLY' || data === null || data === undefined) {
        result = simpleResult('boundary', rec.processing_boundary + ': ' + mime + ' is hashed and recorded but never parsed, decompressed or executed');
      } else if (rec.processing_boundary === 'REFERENCE_ONLY') {
        result = simpleResult('reference', 'URL content was not fetched or acquired');
      } else if (mime.indexOf('image/') === 0) result = await analyzeImage(data, mime);
      else if (['video/mp4', 'video/quicktime', 'audio/mp4'].indexOf(mime) >= 0) result = analyzeVideo(data, mime);
      else if (mime.indexOf('audio/') === 0 || mime === 'application/ogg') result = analyzeAudio(data, mime);
      else if (mime === 'application/json') result = analyzeEvent(data);
      else if (mime === 'text/plain') result = analyzeText(data);
      else result = simpleResult('none', 'No analyzer for ' + mime);
    } catch (e) {
      result = { analyzer: 'failed@' + VER, metadata: {}, observations: [], not_performed: ['analysis aborted'],
        indicators: [Indicator({ code: 'CONTAINER.ANALYZER_FAILED', category: 'CONTAINER', title: 'Analyzer failed on this item',
          evidence: 'the analyzer raised an internal error (details withheld)', method: 'Analyzer isolation boundary.', confidence: 'HIGH',
          limitation: 'No findings exist for this item; absence of indicators here means nothing.',
          alternatives: ['Malformed or unsupported input', 'Analyzer defect'], state: V.INCONCLUSIVE, analyzer: 'case@' + VER })] };
    }
    var mm = declaredMimeIndicator(rec);
    result.indicators = assignFindingIds(rec.evidence_id, (mm ? [mm] : []).concat(result.indicators));
    result.observations.forEach(function (o) { if (o.source === undefined) o.source = 'analyzer'; });
    return result;
  }
  async function recordFor(item, data, demo) {
    var miss = ['evidence_id', 'label', 'acquired_at', 'acquired_by'].filter(function (k) { return !pyStrip(pyStr(item[k] === undefined ? '' : item[k])); });
    if (miss.length) throw new CaseError('evidence item is missing ' + miss.join(', '));
    return acquireBytes(data, { label: item.label, acquired_at: item.acquired_at, acquired_by: item.acquired_by,
      declared_name: item.file || '', declared_mime: item.declared_mime || '', evidence_id: item.evidence_id,
      method: item.method || 'file', object_kind: item.object_kind || V.ORIGINAL, parent_id: item.parent_id || '',
      transformation: item.transformation || '', upstream_source: item.upstream_source || '', demonstration: demo });
  }
  function now() { return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'); }
  async function analyzeEvidence(kase, files) {
    if (kase.schema !== V.CASE_SCHEMA) throw new CaseError('case schema must be ' + V.CASE_SCHEMA);
    var items = kase.evidence;
    if (!Array.isArray(items) || !items.length) throw new CaseError('case has no evidence');
    var ids = items.map(function (i) { return i.evidence_id; });
    if (new Set(ids).size !== ids.length) throw new CaseError('evidence ids must be unique');
    var demo = !!kase.demonstration, records = [], analyses = {}, telemetry = [];
    for (var k = 0; k < items.length; k++) {
      var item = items[k], eid = item.evidence_id;
      if (!Object.prototype.hasOwnProperty.call(files, eid)) throw new CaseError('no content supplied for ' + eid);
      var rec = await recordFor(item, files[eid], demo);
      var t0 = (typeof performance !== 'undefined' ? performance.now() : Date.now());
      var a = await analyzeItem(rec, files[eid]);
      telemetry.push({ stage: 'CONTENT_ANALYSIS', evidence_id: eid, size_bytes: rec.size_bytes, analyzer: a.analyzer,
        duration_ms: Math.floor((typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0),
        outcome: a.analyzer.indexOf('failed@') === 0 ? 'failed' : 'ok' });
      (item.observations || []).forEach(function (o) {
        if (o.dimension && o.value) {
          var ob = { dimension: String(o.dimension), value: pySlice(String(o.value), 300),
            basis: 'analyst: ' + pySlice(String(o.basis === undefined ? 'observation' : o.basis), 200), source: 'analyst' };
          if (o.entity) ob.entity = o.entity;
          a.observations.push(ob);
        }
      });
      records.push(rec); analyses[eid] = a;
    }
    return { records: records, analyses: analyses, telemetry: telemetry };
  }
  function firstObs(obs, dim) { for (var i = 0; i < obs.length; i++) if (obs[i].dimension === dim) return obs[i].value; return null; }
  function resolveChannels(kase, observations, receipts) {
    return (kase.channels || []).map(function (ch) {
      var eid = ch.evidence_id || '', obs = observations[eid] || [];
      var r = { kind: ch.kind, evidence_id: eid, label: ch.label || '' };
      var tw = firstObs(obs, 'time_window'), loc = firstObs(obs, 'location'), off = firstObs(obs, 'clock_offset');
      if (tw) r.time_window = tw;
      if (loc) r.location = loc;
      if (off !== null) r.offset_seconds = parseInt(off, 10);
      if (ch.kind === 'PROVENANCE_RECORD') {
        var primary = ((kase.channels || []).filter(function (c) { return c.kind === 'PRIMARY_MEDIA'; })[0] || {}).evidence_id || '';
        if (Object.prototype.hasOwnProperty.call(receipts, primary)) r.declared_sha256 = receipts[primary];
      }
      return r;
    });
  }
  function relativeWindow(primary, sensor) {
    var p = primary ? timeRange(primary) : null, s = sensor ? timeRange(sensor) : null;
    if (!p || !s || p[1] === null || s[1] === null) return null;
    var start = Math.max(p[1], s[1]) - p[1], end = Math.min(p[2], s[2]) - p[1];
    return end > start ? [start * 1000, end * 1000] : null;
  }
  function buildTimelines(analyses, kase, observations, order) {
    var out = {}, chans = kase.channels || [];
    var primary = (chans.filter(function (c) { return c.kind === 'PRIMARY_MEDIA'; })[0] || {}).evidence_id || '';
    var sensor = (chans.filter(function (c) { return c.kind === 'INDEPENDENT_SENSOR'; })[0] || {}).evidence_id || '';
    order.forEach(function (eid) {
      var a = analyses[eid], tl = a.timeline;
      if (!tl) return;
      out[eid] = tl;
      if (eid === primary && sensor) {
        var win = relativeWindow(firstObs(observations[eid] || [], 'time_window') || '', firstObs(observations[sensor] || [], 'time_window') || '');
        if (win && a.frame_runs) { out[eid] = buildTimeline(a.frame_runs, tl.timescale, [win]); out[eid].corroborated_by = sensor; }
      }
    });
    return out;
  }
  function proposedStatus(e, integ, opened, corroborated, conflicted) {
    if (e.provenance_state === V.PROVENANCE_GAP) return [V.UNVERIFIED, 'content not acquired'];
    if (integ === 'MISMATCH') return [V.UNVERIFIED, 'hash differs from the custody receipt'];
    if (opened.some(function (i) { return i.state === V.ANOMALY_DETECTED; })) return [V.INCONCLUSIVE, 'open anomaly indicators'];
    if (conflicted) return [V.INCONCLUSIVE, 'independent sources conflict with this item'];
    var ro = opened.some(function (i) { return i.state === V.REVIEW_REQUIRED || i.state === V.INCONCLUSIVE; });
    if (integ === 'MATCH') return ro ? [V.SUPPORTED, 'custody hash matches; review indicators open'] : [V.VERIFIED, 'custody hash matches; no open indicators (VERIFIED needs a human ACCEPT)'];
    if (corroborated) return ro ? [V.INCONCLUSIVE, 'corroborated, but review indicators open'] : [V.SUPPORTED, 'an independent source agrees; no open indicators'];
    return [V.UNVERIFIED, 'no custody record and no independent corroboration'];
  }
  function gauges(evidence, indicators, assessment, matrix, timelines, excluded, observations) {
    var byId = {}; evidence.forEach(function (e) { byId[e.evidence_id] = e; });
    var open = {};
    indicators.forEach(function (i) { if (i.resolution !== 'DISMISSED' && i.state !== V.NORMAL) (open[i.evidence_id] = open[i.evidence_id] || []).push(i); });
    var active = evidence.filter(function (e) { return !Object.prototype.hasOwnProperty.call(excluded, e.evidence_id); });
    function provOk(e, depth) {
      if (e.integrity === 'MATCH') return true;
      var p = e.parent_id ? byId[e.parent_id] : null;
      return !!p && depth < 16 && provOk(p, depth + 1);
    }
    var integ = active.filter(function (e) { return e.integrity !== 'MISMATCH' && !(open[e.evidence_id] || []).some(function (i) { return i.category === 'CONTAINER' && (i.state === V.ANOMALY_DETECTED || i.state === V.INCONCLUSIVE); }); });
    var timed = active.filter(function (e) { return timelines[e.evidence_id] || (observations[e.evidence_id] || []).some(function (o) { return o.dimension === 'time' || o.dimension === 'time_window'; }); }).map(function (e) { return e.evidence_id; });
    var tconf = new Set(); matrix.temporal_conflicts.forEach(function (p) { tconf.add(p.a); tconf.add(p.b); });
    var tok = timed.filter(function (id) { return !tconf.has(id) && !(open[id] || []).some(function (i) { return i.category === 'TEMPORAL'; }); });
    var parsed = active.filter(function (e) { return e.processing_boundary === 'PARSE'; });
    var mok = parsed.filter(function (e) { return !(open[e.evidence_id] || []).some(function (i) { return i.category === 'METADATA'; }); });
    var expl = ((assessment || {}).propositions || []).filter(function (p) { return !p.implicit && p.dimension !== 'source'; });
    return {
      label: 'ANALYTICAL INDICATORS',
      note: 'Integer percentages of items or propositions meeting each rule. They are not truth scores and do not combine into one.',
      values: { PROVENANCE: pct(active.filter(function (e) { return provOk(e, 0); }).length, active.length),
        INTEGRITY: pct(integ.length, active.length),
        CORROBORATION: pct(expl.filter(function (p) { return p.verdict === V.SUPPORTED; }).length, expl.length),
        TEMPORAL_CONSISTENCY: pct(tok.length, timed.length),
        METADATA_CONSISTENCY: pct(mok.length, parsed.length) },
      definitions: {
        PROVENANCE: 'items whose hash matches a custody receipt, directly or through a recorded parent',
        INTEGRITY: 'items with no custody mismatch and no open container anomaly',
        CORROBORATION: 'claim propositions supported by two or more independent groups',
        TEMPORAL_CONSISTENCY: 'timed items with no open temporal indicator and no independent time conflict',
        METADATA_CONSISTENCY: 'parsed items with no open metadata indicator' }
    };
  }
  async function assessCase(kase, analyzed, reviews, claimText, at) {
    var records = analyzed.records, analyses = analyzed.analyses, demo = !!kase.demonstration;
    var analyst = pyStrip(pyStr(kase.analyst === undefined ? '' : kase.analyst)) || 'analyst';
    at = at || kase.analysis_at || now();
    var tol = Object.assign({ time_seconds: 120, location_meters: 250, clock_seconds: 5 }, kase.tolerances || {});
    var evidence = records.map(function (r) { var e = Object.assign({}, r); e.perceptual_hash = ((analyses[r.evidence_id].pixels) || {}).dhash || ''; return e; });
    var byId = {}; evidence.forEach(function (e) { byId[e.evidence_id] = e; });
    var ledger = new Ledger(), i;
    for (i = 0; i < records.length; i++) {
      var r = records[i];
      await ledger.append('ACQUIRED', r.evidence_id, { actor: r.acquired_by, at: r.acquired_at, detail: { content_sha256: r.content_sha256,
        size_bytes: r.size_bytes, mime: r.mime_sniffed, object_kind: r.object_kind, method: r.acquisition_method } });
      if (r.parent_id) {
        var par = byId[r.parent_id];
        await ledger.append('DERIVED', r.evidence_id, { actor: r.acquired_by, at: r.acquired_at, parent_ids: [r.parent_id],
          detail: { content_sha256: r.content_sha256, parent_sha256: par ? par.content_sha256 : '', transformation: r.transformation } });
      }
    }
    for (i = 0; i < records.length; i++) {
      var an = analyses[records[i].evidence_id];
      await ledger.append('ANALYZED', records[i].evidence_id, { actor: analyst, at: at, detail: { analyzer: an.analyzer, output_sha256: await digest(an), indicators: an.indicators.length } });
    }
    var log = await reviewLogFrom(analyst, reviews || []);
    for (i = 0; i < log.records.length; i++) {
      var rr = log.records[i];
      await ledger.append('REVIEWED', rr.target, { actor: rr.reviewer, at: rr.at, detail: { action: rr.action, review_hash: rr.record_hash } });
    }
    var excluded = {};
    evidence.forEach(function (e) {
      var d = log.decision(e.evidence_id);
      if (d.state === 'DECIDED' && d.action === 'REJECT') excluded[e.evidence_id] = 'rejected by ' + d.reviewer + ' at ' + d.at + ': ' + d.note;
    });
    var indicators = [];
    evidence.forEach(function (e) {
      analyses[e.evidence_id].indicators.forEach(function (ind) {
        var d = log.decision(ind.finding_id);
        indicators.push(Object.assign({}, ind, { evidence_id: e.evidence_id, review: d,
          resolution: d.action === 'ACCEPT' ? 'CONFIRMED' : d.action === 'REJECT' ? 'DISMISSED' : 'OPEN' }));
      });
    });
    var openBy = {};
    indicators.forEach(function (ind) { if (ind.resolution !== 'DISMISSED' && ind.state !== V.NORMAL) (openBy[ind.evidence_id] = openBy[ind.evidence_id] || []).push(ind); });
    var observations = {}; evidence.forEach(function (e) { observations[e.evidence_id] = analyses[e.evidence_id].observations; });
    var receipts = {};
    records.forEach(function (rc) { (analyses[rc.evidence_id].custody || []).forEach(function (en) { if (!(en.evidence_id in receipts)) receipts[en.evidence_id] = en.sha256; }); });
    var integrity = {};
    records.forEach(function (rc) { var dcl = receipts[rc.evidence_id]; integrity[rc.evidence_id] = !dcl ? 'NO_RECORD' : dcl === rc.content_sha256 ? 'MATCH' : 'MISMATCH'; });
    var groups = independenceGroups(evidence), membership = groups.membership;
    var active = evidence.filter(function (e) { return !Object.prototype.hasOwnProperty.call(excluded, e.evidence_id); });
    var matrix = corroborationMatrix(active, observations, membership, tol), pcs = [];
    evidence.forEach(function (e) {
      if (integrity[e.evidence_id] === 'MISMATCH') pcs.push({ evidence_id: e.evidence_id, issue: 'SHA-256 differs from the custody receipt' });
      if (e.parent_id && !byId[e.parent_id]) pcs.push({ evidence_id: e.evidence_id, issue: 'declared parent is not in the evidence set' });
      if (e.provenance_state === V.PROVENANCE_GAP) pcs.push({ evidence_id: e.evidence_id, issue: 'content not acquired (reference only)' });
    });
    matrix.provenance_conflicts = pcs; matrix.groups = groups.groups; matrix.relations = groups.relations;
    var caveated = {};
    Object.keys(openBy).forEach(function (k) {
      var v = openBy[k].filter(function (x) { return x.state === V.ANOMALY_DETECTED || x.state === V.PROVENANCE_GAP; }).map(function (x) { return x.finding_id; });
      if (v.length) caveated[k] = v;
    });
    var ctx = { evidence: evidence, observations: observations, membership: membership, excluded: excluded, caveated: caveated, integrity: integrity, tolerances: tol };
    var ct = (claimText === undefined || claimText === null) ? (kase.claim || '') : claimText;
    var assessment = pyStrip(ct) ? verifyClaim(ct, ctx) : null;
    if (assessment) {
      var dc = log.decision('CLAIM');
      assessment.review = dc;
      assessment.final_verdict = dc.state === 'PENDING' ? 'PENDING_REVIEW' : dc.state !== 'DECIDED' ? V.INCONCLUSIVE :
        ({ ACCEPT: assessment.verdict, REJECT: V.UNVERIFIED, MARK_INCONCLUSIVE: V.INCONCLUSIVE })[dc.action];
    }
    var rows = assessment ? consistencyMatrix(assessment, ctx) : [];
    var bif = bifocalVerify(resolveChannels(kase, observations, receipts), membership, (function () { var h = {}; evidence.forEach(function (e) { h[e.evidence_id] = e.content_sha256; }); return h; })(), tol);
    var timelines = buildTimelines(analyses, kase, observations, records.map(function (x) { return x.evidence_id; }));
    var agreeSet = new Set(), conflictSet = new Set();
    matrix.pairs.forEach(function (p) {
      if (!p.independent) return;
      if (p.relation === AGREES) { agreeSet.add(p.a); agreeSet.add(p.b); }
      if (p.relation === CONFLICTS || p.relation === 'MIXED') { conflictSet.add(p.a); conflictSet.add(p.b); }
    });
    evidence.forEach(function (e) {
      var eid = e.evidence_id, opened = openBy[eid] || [];
      var ps = proposedStatus(e, integrity[eid], opened, agreeSet.has(eid), conflictSet.has(eid)), d = log.decision(eid);
      Object.assign(e, { group: membership[eid], integrity: integrity[eid],
        integrity_state: integrity[eid] === 'MATCH' ? V.CRYPTOGRAPHICALLY_VERIFIED : integrity[eid] === 'MISMATCH' ? V.ANOMALY_DETECTED :
          (e.provenance_state === V.PROVENANCE_GAP ? V.PROVENANCE_GAP : V.REVIEW_REQUIRED),
        open_findings: opened.length, proposed_status: ps[0], status_rule: ps[1], review: d,
        final_status: finalStatus(ps[0], d, demo), lineage: ledger.lineage(eid), excluded: Object.prototype.hasOwnProperty.call(excluded, eid) });
    });
    var gg = gauges(evidence, indicators, assessment, matrix, timelines, excluded, observations);
    var graph = buildGraph(evidence, observations, analyses, assessment, groups);
    var aiAudit = [];
    for (i = 0; i < evidence.length; i++) {
      var ev = evidence[i], aa = analyses[ev.evidence_id], best = 'NONE', bestR = 0;
      aa.indicators.forEach(function (x) { var rk = { LOW: 1, MODERATE: 2, HIGH: 3 }[x.confidence]; if (rk > bestR) { bestR = rk; best = x.confidence; } });
      aiAudit.push({ run_id: 'RUN-' + ev.evidence_id, evidence_id: ev.evidence_id, analyzer: aa.analyzer, provider: 'clearglass-local',
        model: 'deterministic rule set (no machine-learning model)', model_version: aa.analyzer.split('@').pop(), prompt_template_version: null,
        input_sha256: ev.content_sha256, output_sha256: await digest(aa), at: at, analyst: analyst, confidence: best,
        limitations: aa.not_performed || [], human_review_status: ev.review.state });
    }
    var openCount = indicators.filter(function (x) { return x.resolution !== 'DISMISSED' && x.state !== V.NORMAL; }).length;
    var decided = evidence.every(function (e) { return e.review.state === 'DECIDED'; }) && (!assessment || assessment.review.state === 'DECIDED');
    var lv = await verifyRecords(ledger.records), rv = await log.verify();
    var hist = ['QUEUED', 'PROCESSING', 'ANALYZING', 'REVIEW_REQUIRED'];
    if (decided) hist.push('COMPLETE');
    var stages = V.PIPELINE.map(function (s) { return { stage: s, status: 'DONE' }; });
    stages[stages.length - 1].status = decided ? 'DONE' : 'PENDING_HUMAN_REVIEW';
    return {
      schema: V.RESULT_SCHEMA, engine: { name: V.ENGINE_NAME, version: VER }, case_id: kase.case_id || '', title: kase.title || '',
      demonstration: demo, label: demo ? V.DEMO_LABEL : '', disclaimer: V.DISCLAIMER, analysis_at: at, analyst: analyst, tolerances: tol,
      job: { state: hist[hist.length - 1], history: hist }, pipeline: stages, evidence: evidence, analyses: analyses, indicators: indicators,
      observations: observations, correlation: matrix, claim: assessment, consistency: rows, bifocal: bif, timelines: timelines,
      integrity_indicators: gg, graph: graph,
      provenance: { records: ledger.records, verified: lv[0], first_bad_seq: lv[1], head: ledger.head() },
      reviews: { records: log.records.map(function (x) { return Object.assign({}, x); }), verified: rv[0], first_bad_seq: rv[1] },
      ai_audit: aiAudit,
      external_ai: { enabled: false, note: 'No external AI provider is configured or called. An adapter must be explicitly enabled, and every call is then recorded in ai_audit with input and output hashes.' },
      summary: { statement: openCount ? V.INDICATORS_FOUND : V.NO_INDICATORS, open_findings: openCount, evidence_items: evidence.length,
        independent_groups: groups.groups.length, claim_verdict: assessment ? assessment.verdict : null, crypto_note: V.CRYPTO_NOTE }
    };
  }
  async function runCase(kase, files, reviews, claim) {
    var analyzed = await analyzeEvidence(kase, files);
    var result = await assessCase(kase, analyzed, (reviews && reviews.length) ? reviews : (kase.reviews || []), claim);
    result.telemetry = analyzed.telemetry;
    return result;
  }

  // ------------------------------------------------------------------
  // report (truth_forensics/report.py)
  // ------------------------------------------------------------------
  var SECTIONS = ['Executive Summary', 'Evidence Inventory', 'Acquisition Details', 'Cryptographic Hashes', 'Provenance', 'Timeline',
    'Detected Indicators', 'Corroboration', 'Contradictions', 'AI Analysis', 'Human Review', 'Limitations', 'Final Evidence Status', 'Audit Trail'];
  var FORBIDDEN = [
    /\b(?:is|are|was|were)\s+(?:definitely\s+|certainly\s+|clearly\s+)?(?:a\s+)?fake\b/gi,
    /\b(?:is|are)\s+(?:definitely\s+|certainly\s+)?(?:authentic|genuine|real|true)\b/gi,
    /\bprove[sn]?\s+(?:that\s+)?(?:the\s+)?(?:\w+\s+)?(?:is|are)\s+(?:authentic|genuine|fake|real)/gi,
    /\b100\s*%\s*(?:accurate|certain|reliable)/gi, /\bguarantee[sd]?\b/gi, /\binfallibl[ey]\b/gi,
    /\bdetects?\s+all\b/gi, /\bundeniabl[ey]\b/gi, /\bdefinitive(?:ly)?\s+(?:fake|authentic|proof)/gi];
  var USER_KEYS = new Set(['id', 'label', 'claim', 'by', 'at', 'd', 'chain', 't', 'a', 'b', 'fid', 'ev', 'val', 'e', 'rule', 'run', 'who', 'note', 'sub', 'actor', 'detail', 'r_user']);
  function checkLanguage(text) {
    var out = [];
    FORBIDDEN.forEach(function (rx) { rx.lastIndex = 0; var m; while ((m = rx.exec(text))) out.push(m[0]); });
    return out;
  }
  function fill(template, values, mask) {
    return template.replace(/\{(\w+)\}/g, function (_, k) { return (mask && USER_KEYS.has(k)) ? '…' : pyStr(values[k]); });
  }
  function S_(kind, template, values) {
    values = values || {};
    if (V.STATEMENT_KINDS.indexOf(kind) < 0) throw new Error(kind);
    var bad = checkLanguage(fill(template, values, true));
    if (bad.length) throw new LanguageError('engine text makes a false-certainty claim: ' + bad.join(', '));
    return { kind: kind, text: fill(template, values, false) };
  }
  async function buildReport(result, generatedAt) {
    var at = generatedAt || [result.analysis_at].concat(result.reviews.records.map(function (r) { return r.at; })).sort(strCmp).pop();
    var ev = result.evidence, S = {}, OBS = 'OBSERVATION', INT = 'INTERPRETATION', CON = 'CONCLUSION';
    SECTIONS.forEach(function (s) { S[s] = []; });
    var ex = S['Executive Summary'];
    if (result.demonstration) ex.push(S_(OBS, '{label}: every item in this case is synthetic.', { label: V.DEMO_LABEL }));
    ex.push(S_(OBS, '{n} evidence item(s) in {g} independence group(s).', { n: ev.length, g: result.summary.independent_groups }));
    ex.push(S_(INT, '{statement}', { statement: result.summary.statement }));
    if (result.claim) {
      ex.push(S_(OBS, 'Claim examined: “{claim}”', { claim: result.claim.claim }));
      ex.push(S_(CON, 'Claim assessment: {v} (human review: {r}).', { v: result.claim.verdict, r: result.claim.review.state }));
    }
    ex.push(S_(OBS, '{d}', { d: V.DISCLAIMER }));
    ev.forEach(function (e) {
      S['Evidence Inventory'].push(S_(OBS, '{id} — {label}: {kind} {stype}, {mime}, {size} bytes, group {g}.',
        { id: e.evidence_id, label: e.label, kind: e.object_kind.toLowerCase(), stype: e.source_type, mime: e.mime_sniffed, size: e.size_bytes, g: e.group }));
      S['Acquisition Details'].push(S_(OBS, '{id} acquired {at} by {by} via {method}; processing boundary {b}.',
        { id: e.evidence_id, at: e.acquired_at, by: e.acquired_by, method: e.acquisition_method, b: e.processing_boundary }));
      if (e.mime_declared && e.mime_declared !== e.mime_sniffed) {
        S['Acquisition Details'].push(S_(OBS, '{id} was declared as {d}; its bytes identify it as {m}.', { id: e.evidence_id, d: e.mime_declared, m: e.mime_sniffed }));
      }
      S['Cryptographic Hashes'].push(S_(OBS, '{id} SHA-256 {h}; custody comparison {i} ({state}).', { id: e.evidence_id, h: e.content_sha256, i: e.integrity, state: e.integrity_state }));
    });
    S['Cryptographic Hashes'].push(S_(INT, '{n}', { n: V.CRYPTO_NOTE }));
    var prov = result.provenance;
    S.Provenance.push(S_(OBS, 'Provenance ledger: {n} hash-chained record(s); chain verification {ok}.',
      { n: prov.records.length, ok: prov.verified ? 'passed' : 'FAILED at record ' + prov.first_bad_seq }));
    ev.forEach(function (e) {
      if (e.lineage.length > 1) S.Provenance.push(S_(OBS, '{id} lineage: {chain}; transformation: {t}.', { id: e.evidence_id, chain: e.lineage.join(' → '), t: e.transformation || 'not stated' }));
    });
    result.correlation.relations.forEach(function (rel) { S.Provenance.push(S_(INT, '{a} and {b}: {r}; they count as one source.', { a: rel.a, b: rel.b, r: rel.reason })); });
    result.correlation.provenance_conflicts.forEach(function (pc) { S.Provenance.push(S_(INT, '{id}: {issue}.', { id: pc.evidence_id, issue: pc.issue })); });
    var tlKeys = sortedKeys(result.timelines);
    tlKeys.forEach(function (eid) {
      var tl = result.timelines[eid], fps = fdiv(tl.fps_x100, 100) + '.' + pad(tl.fps_x100 % 100, 2);
      S.Timeline.push(S_(OBS, '{id}: nominal {fps} fps over {n} frame interval(s).', { id: eid, fps: fps, n: tl.intervals }));
      tl.segments.forEach(function (seg) {
        S.Timeline.push(S_(INT, '{id} {a}–{b} {label}: {reason}.', { id: eid, a: fmtMs(seg.start_ms), b: fmtMs(seg.end_ms), label: seg.label, reason: seg.reason }));
      });
    });
    if (!tlKeys.length) S.Timeline.push(S_(OBS, 'No frame-timed media in this case.'));
    result.indicators.forEach(function (ind) {
      S['Detected Indicators'].push(S_(INT, '{fid} [{state}, confidence {c}, review {r}]: {title}. Evidence: {ev}. Method: {m}. Other explanations: {alt}. Limitation: {lim}',
        { fid: ind.finding_id, state: ind.state, c: ind.confidence, r: ind.resolution, title: ind.title, ev: ind.evidence, m: ind.method, alt: ind.alternatives.join('; '), lim: ind.limitation }));
    });
    if (!result.indicators.length) S['Detected Indicators'].push(S_(INT, '{msg}', { msg: V.NO_INDICATORS }));
    var corr = result.correlation;
    S.Corroboration.push(S_(OBS, 'Independent pairs agreeing: {a}; conflicting: {c}; dependent pairs not counted: {d}.',
      { a: corr.summary.agreeing, c: corr.summary.conflicting, d: corr.summary.dependent }));
    if (result.claim) {
      result.claim.propositions.forEach(function (p) {
        var val = (typeof p.value === 'string' ? p.value : p.value.join(' before ')) || 'implicit';
        S.Corroboration.push(S_(INT, '{id} {dim} “{val}”: {v} (confidence {c}); {rule}.', { id: p.id, dim: p.dimension, val: val, v: p.verdict, c: p.confidence, rule: p.rule }));
        p.conflicting.forEach(function (x) {
          S.Contradictions.push(S_(INT, '{id} is contradicted by {e} ({val}; basis: {b}).', { id: p.id, e: x.evidence_id || x.group, val: x.value, b: x.basis }));
        });
      });
    }
    result.consistency.forEach(function (row) { S.Corroboration.push(S_(INT, 'Consistency {d}: {s}, confidence {c}.', { d: row.dimension, s: row.status, c: row.confidence })); });
    var bif = result.bifocal;
    S.Corroboration.push(S_(INT, 'Bifocal verification: coverage {cov}, score {score}. {disc}', { cov: bif.coverage, score: bif.score === null ? 'not reported' : String(bif.score), disc: V.BIFOCAL_DISCLAIMER }));
    bif.checks.forEach(function (chk) { if (chk.result !== 'AGREES') S.Contradictions.push(S_(INT, 'Bifocal {chk}: {r} — {d}.', { chk: chk.check, r: chk.result, d: chk.detail })); });
    corr.temporal_conflicts.forEach(function (tc) { S.Contradictions.push(S_(INT, 'Time conflict between {a} and {b}.', { a: tc.a, b: tc.b })); });
    if (!S.Contradictions.length) S.Contradictions.push(S_(OBS, 'No contradictions found by the available rules.'));
    S['AI Analysis'].push(S_(OBS, '{n}', { n: result.external_ai.note }));
    result.ai_audit.forEach(function (run) {
      S['AI Analysis'].push(S_(OBS, '{run}: {an} ({model}), input {i}, output {o}, at {at}, analyst {who}, highest indicator confidence {c}, human review {h}.',
        { run: run.run_id, an: run.analyzer, model: run.model, i: run.input_sha256.slice(0, 16) + '…', o: run.output_sha256.slice(0, 16) + '…', at: run.at, who: run.analyst, c: run.confidence, h: run.human_review_status }));
    });
    result.reviews.records.forEach(function (rec) {
      S['Human Review'].push(S_(OBS, '#{n} {action} on {t} by {r_user} at {at}: “{note}”', { n: rec.seq, action: rec.action, t: rec.target, r_user: rec.reviewer, at: rec.at, note: rec.note }));
    });
    if (!result.reviews.records.length) S['Human Review'].push(S_(OBS, 'No human review recorded yet. Nothing in this report is final until a reviewer decides it.'));
    var seen = new Set();
    sortedKeys(result.analyses).forEach(function (eid) {
      (result.analyses[eid].not_performed || []).forEach(function (lim) { if (!seen.has(lim)) { seen.add(lim); S.Limitations.push(S_(OBS, 'Not performed: {item}.', { item: lim })); } });
    });
    S.Limitations.push(S_(INT, 'Metadata is unsigned and can be rewritten; every metadata observation describes the file, not the event.'));
    S.Limitations.push(S_(INT, 'Indicators mark where to look. Their absence does not establish authenticity.'));
    ev.forEach(function (e) {
      S['Final Evidence Status'].push(S_(CON, '{id}: {final} (analysis proposed {p}: {rule}; review {r}).', { id: e.evidence_id, final: e.final_status, p: e.proposed_status, rule: e.status_rule, r: e.review.state }));
    });
    if (result.claim) S['Final Evidence Status'].push(S_(CON, 'Claim: {v}.', { v: result.claim.final_verdict }));
    var body = { case_id: result.case_id, sections: SECTIONS.slice(0, -1).map(function (t) { return { title: t, statements: S[t] }; }), provenance_head: prov.head };
    var reportSha = await digest(body);
    var ok = (await verifyRecords(prov.records))[0];
    var ledger = new Ledger();
    for (var i = 0; i < prov.records.length; i++) {
      var pr = prov.records[i];
      await ledger.append(pr.event, pr.subject_id, { actor: pr.actor, at: pr.at, parent_ids: pr.parent_ids, detail: pr.detail });
    }
    var reported = await ledger.append('REPORTED', result.case_id || 'case', { actor: 'report-generator', at: at, detail: { report_sha256: reportSha } });
    ledger.records.forEach(function (rec) {
      S['Audit Trail'].push(S_(OBS, '#{seq} {ev} {sub} by {actor} at {at} — {h}', { seq: rec.seq, ev: rec.event, sub: rec.subject_id, actor: rec.actor, at: rec.at, h: rec.record_hash.slice(0, 16) + '…' }));
    });
    S['Audit Trail'].push(S_(OBS, 'Chain verified before reporting: {ok}. Report SHA-256: {h}.', { ok: ok ? 'yes' : 'no', h: reportSha }));
    return { case_id: result.case_id, title: result.title, demonstration: result.demonstration, generated_at: at, report_sha256: reportSha,
      reported_record: reported, sections: SECTIONS.map(function (t) { return { title: t, statements: S[t] }; }), disclaimer: V.DISCLAIMER };
  }
  function renderMarkdown(rep) {
    var lines = ['# ClearGlass Truth Forensics Report — ' + rep.case_id, ''];
    if (rep.demonstration) lines.push('> **' + V.DEMO_LABEL + '**', '');
    lines.push(rep.title ? '_' + rep.title + '_' : '', 'Generated ' + rep.generated_at + ' · report SHA-256 `' + rep.report_sha256 + '`', '', '> ' + rep.disclaimer, '');
    rep.sections.forEach(function (sec, n) {
      lines.push('## ' + (n + 1) + '. ' + sec.title, '');
      sec.statements.forEach(function (st) { lines.push('- **[' + st.kind + ']** ' + st.text); });
      lines.push('');
    });
    return lines.join('\n');
  }

  // ------------------------------------------------------------------
  // browser-side helpers for files the reference engine cannot decode
  // ------------------------------------------------------------------
  // Luminance from RGBA canvas pixels, with the same integer weights as the
  // PNG decoder, then the same copy-move and dHash tests.
  function analyzeCanvasPixels(width, height, rgba) {
    var gray = new Uint8Array(width * height);
    for (var i = 0, p = 0; i < gray.length; i++, p += 4) gray[i] = fdiv(299 * rgba[p] + 587 * rgba[p + 1] + 114 * rgba[p + 2], 1000);
    var pb = pixelBlock(width, height, gray);
    return { pixels: pb.pixels, indicators: pb.pixels.clone_clusters.map(function (cl) { return cloneIndicator(cl, pb.factor); }), gray: gray };
  }
  // Web Audio floats -> the reference engine's 16-bit integer scale.
  function floatChannelsToPcm(floatChannels) {
    return floatChannels.map(function (ch) {
      var out = new Array(ch.length);
      for (var i = 0; i < ch.length; i++) { var x = ch[i]; x = x !== x ? 0 : x > 1 ? 1 : x < -1 ? -1 : x; out[i] = Math.floor(x * 32767 + 0.5); }
      return out;
    });
  }

  return {
    vocab: V, VERSION: VER, DISCLAIMER: V.DISCLAIMER,
    canonicalJson: canonicalJson, sha256Bytes: sha256Bytes, sha256Text: sha256Text, digest: digest, pct: pct, quote: quote,
    sniffMime: sniffMime, displayName: displayName, validateUrl: validateUrl, acquireBytes: acquireBytes,
    analyzeItem: analyzeItem, analyzeImage: analyzeImage, analyzeAudio: analyzeAudio, analyzeVideo: analyzeVideo,
    analyzeEvent: analyzeEvent, analyzeText: analyzeText, analyzePcm: analyzePcm, audioIndicators: audioIndicators,
    parseWav: parseWav, parseJpeg: parseJpeg, parsePng: parsePng, parseBmff: parseBmff, parseExif: parseExif,
    copyMove: copyMove, dhash: dhash, hammingHex: hammingHex, analyzeCanvasPixels: analyzeCanvasPixels,
    floatChannelsToPcm: floatChannelsToPcm, buildTimeline: buildTimeline, runsFromTimestamps: runsFromTimestamps, fmtMs: fmtMs,
    decompose: decompose, compare: compare, independenceGroups: independenceGroups,
    analyzeEvidence: analyzeEvidence, assessCase: assessCase, runCase: runCase,
    buildReport: buildReport, renderMarkdown: renderMarkdown, checkLanguage: checkLanguage,
    ReviewLog: ReviewLog, reviewLogFrom: reviewLogFrom, verifyRecords: verifyRecords, finalStatus: finalStatus,
    errors: { IntakeError: IntakeError, CaseError: CaseError, ReviewError: ReviewError, LanguageError: LanguageError, ParseError: ParseError }
  };
});
