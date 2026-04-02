import { test, expect } from "@playwright/test";
import { SharedApi } from "@api/shared.api";

test("health endpoint returns ok", async ({ request }) => {
  const shared = new SharedApi(request);
  const body = await shared.health();
  expect(body.status).toBe("ok");
});
