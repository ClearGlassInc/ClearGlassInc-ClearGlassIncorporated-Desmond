export const metadata = {
  title: "Login | ClearGlass Premium",
  alternates: { canonical: "/login" },
  description: "Authenticate before viewing protected ClearGlass premium workflows and assets.",
};

export default function LoginPage({ searchParams }: { searchParams?: { next?: string } }) {
  return (
    <section aria-labelledby="login-title">
      <p style={{ color: "#9aa6c8" }}>© ClearGlass Inc. All rights reserved.</p>
      <h1 id="login-title">Login required</h1>
      <p style={{ color: "#9aa6c8", lineHeight: 1.6 }}>
        Premium intelligence copy, workflows, prompts, and downloads are rendered only after server-side
        authentication. Connect this screen to your identity provider and issue a signed <code>cg_session</code>
        cookie after successful login.
      </p>
      <form method="post" action="/api/auth/login" aria-describedby="login-help">
        <input type="hidden" name="next" value={searchParams?.next || "/premium"} />
        <label htmlFor="email">Email</label>
        <input id="email" name="email" type="email" autoComplete="email" required style={{ display: "block", margin: "8px 0 12px", padding: 10 }} />
        <button type="submit" disabled style={{ padding: "10px 16px" }}>Authenticate with IdP</button>
      </form>
      <p id="login-help" style={{ color: "#9aa6c8" }}>
        The disabled button is intentional in this scaffold; production should use SSO/OIDC and set an HttpOnly,
        Secure, SameSite=Lax session cookie.
      </p>
    </section>
  );
}
