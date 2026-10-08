import type { RoleName } from "./roles";

export interface Actor {
  id: string;
  email: string;
  name: string;
  role: RoleName;
  isDemo: boolean;
}

/**
 * The authentication interface. A production deployment implements this
 * against its identity provider (OIDC/SAML) and maps the verified subject to a
 * User row; the role always comes from the database, never from the IdP token
 * or the browser. See docs/ARCHITECTURE.md "Authentication".
 */
export interface AuthProvider {
  readonly name: string;
  readonly isDemo: boolean;
  /** Resolve the signed-in actor from request cookies, or null. */
  resolve(cookieValue: (name: string) => string | undefined): Promise<Actor | null>;
}
