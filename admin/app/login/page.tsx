import { safeNextPath } from "@/lib/login-guard";

export const metadata = {
  title: "Login — ClearGlass Commerce Admin",
  alternates: { canonical: "/login" },
  robots: { index: false, follow: false },
};

const MESSAGES: Record<string, string> = {
  "1": "That access token was not accepted.",
  locked: "Too many failed attempts. Sign-in is paused for up to 15 minutes.",
};

// Next.js 15+ passes searchParams as a Promise. Reading it as a plain object
// returned undefined, so `next` was always dropped and errors never showed.
export default async function LoginPage({
  searchParams,
}: {
  searchParams?: Promise<{ next?: string; error?: string }>;
}) {
  const params = (await searchParams) ?? {};
  const next = safeNextPath(params.next);
  const message = params.error ? MESSAGES[params.error] || MESSAGES["1"] : null;
  return (
    <section aria-labelledby="login-title" style={{ display: "grid", gap: 16, maxWidth: 520 }}>
      <h1 id="login-title">Admin login</h1>
      <p>Authenticate to access premium workflows, approvals, prompts, and downloadable operational assets.</p>
      {message ? (
        <p role="alert" style={{ color: "#ffb4ae", margin: 0 }}>
          {message}
        </p>
      ) : null}
      <form action="/api/login" method="post" style={{ display: "grid", gap: 12 }}>
        <input type="hidden" name="next" value={next} />
        <label htmlFor="token">Access token</label>
        <input id="token" name="token" type="password" autoComplete="current-password" required />
        <button type="submit">Sign in</button>
      </form>
    </section>
  );
}
