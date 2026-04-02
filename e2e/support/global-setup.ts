/**
 * Runs after webServer processes in Playwright start. Verifies backend + DB are reachable.
 */
async function globalSetup(): Promise<void> {
  const healthUrl = "http://localhost:8000/api/beta/shared/health";
  const deadline = Date.now() + 60_000;
  let lastError: unknown;

  while (Date.now() < deadline) {
    try {
      const resp = await fetch(healthUrl);
      if (resp.ok) {
        const body = (await resp.json()) as { status?: string };
        if (body.status === "ok") return;
      }
      lastError = new Error(`Health returned ${resp.status}`);
    } catch (e) {
      lastError = e;
    }
    await new Promise((r) => setTimeout(r, 500));
  }

  throw new Error(
    `E2E global setup: backend health check failed after 60s. Is local Supabase running? Try: ./bin/dev db\nLast error: ${String(lastError)}`,
  );
}

export default globalSetup;
