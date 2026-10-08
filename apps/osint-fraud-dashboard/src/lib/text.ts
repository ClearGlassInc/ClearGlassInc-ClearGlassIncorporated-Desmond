// Imported evidence is untrusted data. It is stored as plain text and rendered
// through React text nodes, which escape markup. Nothing here turns text into
// HTML, and nothing in the app uses dangerouslySetInnerHTML.

const CONTROL_CHARS = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g;

/** Strip control characters and cap length. Markup is kept verbatim as text. */
export function cleanText(input: string, maxLength = 20_000): string {
  return input.replace(CONTROL_CHARS, "").normalize("NFC").slice(0, maxLength);
}

/**
 * Validate a user-supplied public-source URL. Only http(s), no embedded
 * credentials. The app never fetches it server-side; it is a citation.
 */
export function parsePublicUrl(raw: string): { ok: true; url: string } | { ok: false; error: string } {
  let u: URL;
  try {
    u = new URL(raw.trim());
  } catch {
    return { ok: false, error: "Not a valid absolute URL" };
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") {
    return { ok: false, error: `URL scheme "${u.protocol}" is not allowed; use http or https` };
  }
  if (u.username || u.password) return { ok: false, error: "URLs with embedded credentials are not accepted" };
  return { ok: true, url: u.toString() };
}

/** href for rendering a stored URL; anything that is not http(s) renders as plain text. */
export function safeHref(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const parsed = parsePublicUrl(raw);
  return parsed.ok ? parsed.url : null;
}
