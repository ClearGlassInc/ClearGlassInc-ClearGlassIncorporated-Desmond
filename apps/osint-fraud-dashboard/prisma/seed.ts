import "dotenv/config";
import { createDb } from "../src/lib/db";
import { seedDemo } from "../src/lib/seed";

async function main() {
  const db = createDb();
  try {
    if (await db.user.count()) {
      console.log("Database already has users; skipping the synthetic seed. Run `npm run db:reset` to start over.");
      return;
    }
    const out = await seedDemo(db);
    console.log(`Seeded SYNTHETIC demonstration data: ${out.alerts} alerts. No real records are included.`);
  } finally {
    await db.$disconnect();
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
