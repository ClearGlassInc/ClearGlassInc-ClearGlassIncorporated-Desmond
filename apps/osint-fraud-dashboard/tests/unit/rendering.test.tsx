import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SourceLink } from "@/components/ui";
import { ClaimBadge, OutcomeBadge, SyntheticBadge } from "@/components/labels";

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? (f === "generated" ? [] : files(p)) : [p];
  });
}

describe("safe rendering of imported content", () => {
  it("no source file renders raw HTML", () => {
    const offenders = files(join(__dirname, "..", "..", "src")).filter((f) => /\.(tsx?|jsx?)$/.test(f) && /dangerouslySetInnerHTML\s*[=:]/.test(readFileSync(f, "utf8")));
    expect(offenders).toEqual([]);
  });

  it("escapes markup in text and refuses javascript: links", () => {
    const html = renderToStaticMarkup(
      <div>
        <blockquote>{"<script>alert('x')</script><img src=x onerror=alert(1)>"}</blockquote>
        <SourceLink url="javascript:alert(1)" />
        <SourceLink url="https://example.org/a" />
      </div>,
    );
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;script&gt;");
    expect(html).not.toContain('href="javascript:');
    expect(html).toContain('href="https://example.org/a"');
    expect(html).toContain('rel="noopener noreferrer nofollow"');
  });

  it("labels carry their meaning in words", () => {
    const html = renderToStaticMarkup(
      <>
        <SyntheticBadge synthetic />
        <ClaimBadge status="ALLEGATION" />
        <OutcomeBadge outcome="NO_MATCH" />
      </>,
    );
    expect(html).toContain("Synthetic");
    expect(html).toContain("Allegation");
    expect(html).toContain("No match - not a clearance");
  });
});
