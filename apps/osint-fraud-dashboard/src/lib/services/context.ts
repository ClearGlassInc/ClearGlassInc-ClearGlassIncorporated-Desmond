import type { Prisma } from "@/generated/prisma/client";
import type { Actor } from "../auth/actor";
import { can, type Permission } from "../auth/roles";
import type { Db } from "../db";
import { ForbiddenError } from "../errors";

/** Everything a service call needs. Pages and actions build one per request. */
export interface Ctx {
  db: Db;
  actor: Actor;
  now?: () => Date;
}

export function now(ctx: Ctx): Date {
  return ctx.now ? ctx.now() : new Date();
}

type Tx = Db | Prisma.TransactionClient;

export async function audit(
  db: Tx,
  actor: Pick<Actor, "id" | "role"> | null,
  action: string,
  target: { type?: string; id?: string } = {},
  details?: Prisma.InputJsonValue,
  outcome: "ok" | "denied" | "failed" = "ok",
): Promise<void> {
  await db.auditEvent.create({
    data: {
      actorId: actor?.id ?? null,
      actorRole: actor?.role ?? null,
      action,
      targetType: target.type ?? null,
      targetId: target.id ?? null,
      outcome,
      details: details ?? undefined,
    },
  });
}

/** Server-side authorization. Denials are recorded, then refused. */
export async function requirePermission(
  ctx: Ctx,
  permission: Permission,
  target: { type?: string; id?: string } = {},
): Promise<void> {
  if (can(ctx.actor.role, permission)) return;
  await audit(ctx.db, ctx.actor, "security.access_denied", target, { permission }, "denied");
  throw new ForbiddenError(`Role ${ctx.actor.role} cannot ${permission}`);
}
