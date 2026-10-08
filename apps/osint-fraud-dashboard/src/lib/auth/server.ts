// Request-scoped auth for pages, server actions and route handlers.

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { config } from "../config";
import { db } from "../db";
import type { Ctx } from "../services/context";
import type { Actor, AuthProvider } from "./actor";
import { DemoAuthProvider, UnconfiguredAuthProvider } from "./demo";

export function authProvider(): AuthProvider {
  const cfg = config();
  return cfg.demoAuthEnabled ? new DemoAuthProvider(db(), cfg.sessionSecret!) : new UnconfiguredAuthProvider();
}

export async function getActor(): Promise<Actor | null> {
  const jar = await cookies();
  return authProvider().resolve((name) => jar.get(name)?.value);
}

/** For pages and server actions: signed-out users are sent to /login. */
export async function requireCtx(): Promise<Ctx> {
  const actor = await getActor();
  if (!actor) redirect("/login");
  return { db: db(), actor };
}
