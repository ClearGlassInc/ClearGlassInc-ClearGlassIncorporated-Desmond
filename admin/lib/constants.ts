// Edge-safe shared constants. This module has no imports and no side effects so
// it can be pulled into the edge middleware bundle as well as server-only code,
// keeping the session-cookie name in one place without dragging `next/headers`
// or Node built-ins across the edge/server boundary.

export const SESSION_COOKIE = "cg_admin_session";
