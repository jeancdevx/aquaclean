import { test, expect } from "@playwright/test";

test("U10 · fixture visual explícito de sesión sin clave", async ({ page }) => {
  await page.route("**/api/session", async (route) => {
    const response = await route.fetch();
    const session = await response.json();
    session.ai.configured = false;
    session.ai.status = "Fixture UI sin clave";
    await route.fulfill({ response, json: session });
  });
  await page.goto("/");
  await expect(
    page.getByText("IA y embeddings no disponibles.", { exact: true }),
  ).toBeVisible();
});

