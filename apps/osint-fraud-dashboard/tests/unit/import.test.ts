import { describe, expect, it } from "vitest";
import { parseCsv } from "@/lib/import/csv";
import { parseIsoDate, validateImport, type ImportRequest, type NormalizedTransaction, type NormalizedEvidence } from "@/lib/import/validate";

const enc = (s: string) => new TextEncoder().encode(s);
const base = (over: Partial<ImportRequest>): ImportRequest => ({
  filename: "t.csv",
  bytes: enc(""),
  format: "CSV",
  recordType: "TRANSACTION",
  origin: "SYNTHETIC",
  mapping: null,
  limits: { maxBytes: 100_000, maxRows: 100 },
  ...over,
});

describe("CSV parser", () => {
  it("handles quotes, doubled quotes, embedded commas and newlines, CRLF and BOM", () => {
    const rows = parseCsv('﻿a,b\r\n"x, y","he said ""hi"""\r\n"multi\nline",z\n');
    expect(rows.map((r) => r.cells)).toEqual([
      ["a", "b"],
      ["x, y", 'he said "hi"'],
      ["multi\nline", "z"],
    ]);
    expect(rows.map((r) => r.line)).toEqual([1, 2, 3]);
  });

  it("rejects an unterminated quote with its line number", () => {
    expect(() => parseCsv('a,b\n1,"oops\n')).toThrow(/line 2: unterminated/);
  });
});

describe("ISO dates", () => {
  it("accepts date-only and zoned date-times, rejects ambiguous forms", () => {
    expect(parseIsoDate("2026-03-02")?.toISOString()).toBe("2026-03-02T00:00:00.000Z");
    expect(parseIsoDate("2026-03-02T10:00:00-05:00")?.toISOString()).toBe("2026-03-02T15:00:00.000Z");
    expect(parseIsoDate("2026-03-02T10:00:00")).toBeNull(); // no zone
    expect(parseIsoDate("03/02/2026")).toBeNull();
    expect(parseIsoDate("2026-02-30")).toBeNull();
  });
});

describe("import validation", () => {
  it("maps snake_case headers, records supplied fields, and lists expected-but-missing ones", () => {
    const csv = "record_id,type,vendor_record_id,amount,occurred_at,po_reference\nP-1,payment,V-1,100.50,2026-03-09,\n";
    const out = validateImport(base({ bytes: enc(csv) }));
    expect(out.errors).toEqual([]);
    const r = out.records[0] as NormalizedTransaction;
    expect(r.type).toBe("PAYMENT");
    expect(r.amount).toBe(100.5);
    expect(r.poReference).toBeNull();
    expect(r.provided).toContain("poReference"); // column present, value blank
    expect(r.provided).not.toContain("approvedAt"); // column absent: unknown
    expect(r.missing).toEqual(["approvedAt", "poReference"]);
  });

  it("gives actionable row and field errors for invalid values", () => {
    const csv = "recordId,type,amount,occurredAt,currency\nP-1,REFUND,\"1,200\",03/04/2026,dollars\n";
    const out = validateImport(base({ bytes: enc(csv) }));
    const messages = out.errors.map((e) => `${e.row}:${e.field}:${e.message}`);
    expect(messages).toEqual(
      expect.arrayContaining([
        expect.stringMatching(/^1:type:"REFUND" is not one of/),
        expect.stringMatching(/^1:amount:.*no currency symbols or thousands separators/),
        expect.stringMatching(/^1:occurredAt:.*ISO 8601/),
        expect.stringMatching(/^1:currency:.*three-letter/),
      ]),
    );
    expect(out.records).toEqual([]);
  });

  it("detects in-file duplicates and conflicting ids", () => {
    const csv = "recordId,type,amount\nP-1,PAYMENT,10\nP-1,PAYMENT,10\nP-1,PAYMENT,99\n";
    const out = validateImport(base({ bytes: enc(csv) }));
    expect(out.inFileDuplicates).toEqual([{ row: 2, recordId: "P-1", firstRow: 1 }]);
    expect(out.errors[0]).toMatchObject({ row: 3, field: "recordId" });
    expect(out.records).toHaveLength(1);
  });

  it("enforces file type, size, encoding and row limits", () => {
    expect(validateImport(base({ filename: "x.txt", bytes: enc("a") })).errors[0].message).toMatch(/needs a \.csv file/);
    expect(validateImport(base({ bytes: enc("x".repeat(50)), limits: { maxBytes: 10, maxRows: 10 } })).errors[0].message).toMatch(/limit is 10/);
    expect(validateImport(base({ bytes: new Uint8Array([0xff, 0xfe, 0x00]) })).errors[0].message).toMatch(/not valid UTF-8/);
    const many = "recordId,type\n" + Array.from({ length: 5 }, (_, i) => `P-${i},PAYMENT`).join("\n");
    expect(validateImport(base({ bytes: enc(many), limits: { maxBytes: 10_000, maxRows: 3 } })).errors[0].message).toMatch(/limit is 3/);
  });

  it("requires a recordId column and reports unmapped columns", () => {
    const out = validateImport(base({ bytes: enc("id,type,colour\n1,PAYMENT,red\n") }));
    expect(out.errors.map((e) => e.message)).toContain("No column maps to recordId; every record needs a stable id");
    expect(out.unmappedColumns).toEqual(["id", "colour"]);
  });

  it("applies an explicit field mapping", () => {
    const out = validateImport(base({ bytes: enc("Ref,Kind\nP-9,PAYMENT\n"), mapping: { Ref: "recordId", Kind: "type" } }));
    expect(out.errors).toEqual([]);
    expect(out.records[0].recordId).toBe("P-9");
  });

  it("keeps malicious markup as inert text but refuses javascript: URLs", () => {
    const json = JSON.stringify([
      {
        recordId: "EV-X",
        title: "<img src=x onerror=alert(1)>",
        excerpt: "<script>alert('xss')</script> payment approved",
        sourceTitle: "Test",
        url: "https://example.org/a",
      },
      { recordId: "EV-Y", title: "t", excerpt: "e", sourceTitle: "s", url: "javascript:alert(1)" },
    ]);
    const out = validateImport(base({ filename: "e.json", format: "JSON", recordType: "EVIDENCE", origin: "PUBLIC_SOURCE", bytes: enc(json) }));
    const ev = out.records[0] as NormalizedEvidence;
    expect(ev.excerpt).toBe("<script>alert('xss')</script> payment approved");
    expect(ev.accessClassification).toBe("PUBLIC");
    expect(out.errors).toEqual([expect.objectContaining({ row: 2, field: "url", message: expect.stringMatching(/scheme "javascript:" is not allowed/) })]);
  });

  it("refuses non-public classifications in a public-source import", () => {
    const json = JSON.stringify([{ recordId: "EV-Z", title: "t", excerpt: "e", sourceTitle: "s", accessClassification: "RESTRICTED" }]);
    const out = validateImport(base({ filename: "e.json", format: "JSON", recordType: "EVIDENCE", origin: "PUBLIC_SOURCE", bytes: enc(json) }));
    expect(out.errors[0]).toMatchObject({ field: "accessClassification" });
  });

  it("requires incident steps to cite evidence or be flagged as assumptions", () => {
    const json = JSON.stringify([
      { recordId: "INC-1", title: "Incident", summary: "Something documented", steps: [{ kind: "EVENT", text: "Payment released" }] },
    ]);
    const out = validateImport(base({ filename: "i.json", format: "JSON", recordType: "INCIDENT", bytes: enc(json) }));
    expect(out.errors[0].message).toMatch(/set isAssumption: true/);
  });
});
