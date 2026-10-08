import { config } from "@/lib/config";
import { db } from "@/lib/db";
import { Card, Flash, sp } from "@/components/ui";
import { signInDemo } from "../actions";

export const dynamic = "force-dynamic";

export default async function LoginPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const cfg = config();
  const users = cfg.demoAuthEnabled ? await db().user.findMany({ where: { isDemo: true }, orderBy: { email: "asc" } }) : [];
  return (
    <div className="mx-auto max-w-xl py-10">
      <h1 className="mb-1">
        Clear<span className="text-cyan-300">Glass</span> OSINT Fraud Detection
      </h1>
      <p className="muted mb-6">Evidence-first investigation workspace - local prototype.</p>
      <Flash error={sp(params.error)} />
      {cfg.demoAuthEnabled ? (
        <Card title="Demo sign-in (local only)">
          <p className="muted mb-4">
            These demo users exist only in this local database. There is no password: this mode is for local development and is refused when APP_ENV is
            production.
          </p>
          {users.length === 0 ? (
            <p className="muted">No demo users found. Run <code>npm run db:seed</code>.</p>
          ) : (
            <ul className="space-y-2">
              {users.map((u) => (
                <li key={u.id}>
                  <form action={signInDemo} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 px-3 py-2">
                    <input type="hidden" name="userId" value={u.id} />
                    <span>
                      <span className="text-slate-100">{u.name}</span> <span className="muted">({u.role.replace("_", "-").toLowerCase()})</span>
                    </span>
                    <button className="btn" type="submit">
                      Sign in as {u.role.replace("_", "-").toLowerCase()}
                    </button>
                  </form>
                </li>
              ))}
            </ul>
          )}
        </Card>
      ) : (
        <Card title="Sign-in is not configured">
          <p className="muted">
            No authentication provider is configured, so every page is closed. For local development set APP_ENV=local, DEMO_AUTH_ENABLED=true and a
            SESSION_SECRET of at least 32 characters. For a deployment, implement the AuthProvider interface against your identity provider (see
            docs/ARCHITECTURE.md).
          </p>
        </Card>
      )}
    </div>
  );
}
