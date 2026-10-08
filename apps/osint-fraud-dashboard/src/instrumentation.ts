// Runs once when the server starts. Unsafe configuration (for example demo
// sign-in with APP_ENV=production) stops the server instead of running open.
export async function register() {
  const { loadConfig } = await import("./lib/config");
  loadConfig();
}
