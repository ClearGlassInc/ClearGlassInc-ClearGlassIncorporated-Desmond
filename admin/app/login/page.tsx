export const metadata = {
  title: "Login — ClearGlass Commerce Admin",
  alternates: { canonical: "/login" },
};

export default function LoginPage({ searchParams }: { searchParams?: { next?: string } }) {
  const next = searchParams?.next || "/";
  return (
    <section aria-labelledby="login-title" style={{ display: "grid", gap: 16, maxWidth: 520 }}>
      <h1 id="login-title">Admin login</h1>
      <p>Authenticate to access premium workflows, approvals, prompts, and downloadable operational assets.</p>
      <form action="/api/login" method="post" style={{ display: "grid", gap: 12 }}>
        <input type="hidden" name="next" value={next} />
        <label htmlFor="token">Access token</label>
        <input id="token" name="token" type="password" autoComplete="current-password" required />
        <button type="submit">Sign in</button>
      </form>
    </section>
  );
}
