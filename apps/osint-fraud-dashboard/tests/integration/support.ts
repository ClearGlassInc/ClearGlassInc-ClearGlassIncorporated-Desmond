import { createDb, type Db } from "@/lib/db";
import { seedDemo, type SeedResult } from "@/lib/seed";
import type { Ctx } from "@/lib/services/context";
import type { RoleName } from "@/lib/auth/roles";

export const db: Db = createDb(process.env.TEST_DATABASE_URL);

export async function resetAndSeed(): Promise<SeedResult> {
  const tables = await db.$queryRaw<{ tablename: string }[]>`SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> '_prisma_migrations'`;
  await db.$executeRawUnsafe(`TRUNCATE ${tables.map((t) => `"${t.tablename}"`).join(", ")} RESTART IDENTITY CASCADE`);
  return seedDemo(db);
}

export function as(seed: SeedResult, role: RoleName): Ctx {
  return { db, actor: seed.actors[role] };
}

export async function alertFor(ruleKey: string, outcome: string, subjectKey?: string) {
  return db.alert.findFirstOrThrow({ where: { rule: { ruleKey }, outcome: outcome as "MATCH", ...(subjectKey ? { subjectKey } : {}) }, include: { ruleVersion: true } });
}
