import { execSync } from "node:child_process";
import pg from "pg";

// Integration tests need a disposable PostgreSQL database. They fail loudly
// when it is missing rather than skipping, so a green run always means the
// database paths were exercised.
export default async function setup() {
  const url = process.env.TEST_DATABASE_URL;
  if (!url) {
    throw new Error("TEST_DATABASE_URL is not set. Point it at a disposable PostgreSQL database whose name ends in _test (see README).");
  }
  const name = new URL(url).pathname.replace(/^\//, "");
  if (!name.endsWith("_test")) throw new Error(`Refusing to reset database "${name}": its name must end in _test`);
  const client = new pg.Client({ connectionString: url });
  await client.connect();
  await client.query("DROP SCHEMA IF EXISTS public CASCADE");
  await client.query("CREATE SCHEMA public");
  await client.end();
  execSync("npx prisma migrate deploy", { env: { ...process.env, DATABASE_URL: url }, stdio: "pipe" });
}
