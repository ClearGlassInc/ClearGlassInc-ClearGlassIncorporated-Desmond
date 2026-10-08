import "dotenv/config";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
    seed: "tsx prisma/seed.ts",
  },
  datasource: {
    // Unset is fine for `prisma generate`; migrate and seed need it.
    url: process.env.DATABASE_URL ?? "",
  },
});
