import { PrismaPg } from "@prisma/adapter-pg";
import { PrismaClient } from "@/generated/prisma/client";

export type Db = PrismaClient;

export function createDb(url = process.env.DATABASE_URL): Db {
  if (!url) throw new Error("DATABASE_URL is not set");
  return new PrismaClient({ adapter: new PrismaPg({ connectionString: url }) });
}

const globalForDb = globalThis as unknown as { __cgOsintDb?: Db };

/** One client per process; Next dev reloads modules, so it is kept on globalThis. */
export function db(): Db {
  globalForDb.__cgOsintDb ??= createDb();
  return globalForDb.__cgOsintDb;
}
