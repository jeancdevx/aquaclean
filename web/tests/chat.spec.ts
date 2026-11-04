import { test, expect } from "@playwright/test";
import path from "node:path";
import { writeFileSync } from "node:fs";

for (const width of [360, 768, 1440]) {
  test(`U01 U02 U08 · chat, sugerencias, teclado y temas a ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "¿Qué necesitas coordinar hoy?" }),
    ).toBeVisible();
    const writes: string[] = [];
    page.on("request", (request) => {
      if (request.method() === "POST") writes.push(request.url());
    });
    await page.getByRole("main", { name: "Conversación" }).getByRole("button", { name: "Programar un recojo" }).click();
    await expect(
      page.getByRole("textbox", { name: "Mensaje", exact: true }),
    ).toHaveValue(/Quiero programar/);
    expect(writes).toEqual([]);
    await page
      .getByRole("textbox", { name: "Mensaje", exact: true })
      .press("Shift+Enter");
    await expect(
      page.getByRole("textbox", { name: "Mensaje", exact: true }),
    ).toHaveValue(/\n$/);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Activar tema oscuro" }).click();
    await expect(page.locator("html")).toHaveClass("dark");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "Abrir actividad y caso" }).click();
    await expect(page.getByRole("tab", { name: "Fuentes" })).toBeVisible();
    await page.getByRole("tab", { name: "Fuentes" }).click();
    await expect(
      page.getByText("Datos y referencias históricas"),
    ).toBeVisible();
    await page.screenshot({
      path: `../artifacts/chat-${width}-dark.png`,
      fullPage: true,
    });
  });
}

test("U04 · subida real, previsualización y archivo inválido", async ({
  page,
}) => {
  await page.goto("/");
  const file = page.getByLabel("Adjuntar imagen PDF o audio");
  await file.setInputFiles(path.resolve("../tests/fixtures/guia-demo.png"));
  await expect(page.getByText("guia-demo.png", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Enviar mensaje" }),
  ).toBeEnabled();
  await file.setInputFiles({
    name: "archivo-invalido.png",
    mimeType: "image/png",
    buffer: Buffer.from("invalid png"),
  });
  await expect(page.getByRole("alert")).toContainText(/inválido|incompatible/);
});

test("U06 U09 · fuentes oficiales y recursos locales servidos por FastAPI", async ({
  page,
  request,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Abrir actividad y caso" }).click();
  await page.getByRole("tab", { name: "Fuentes" }).click();
  await expect(page.getByText(/pedidos sintéticos/)).toBeVisible();
  await page.getByRole("button", { name: "Consultar fuente pública" }).click();
  await expect(
    page.getByText(/Samsung Recalls Top-Load Washing Machines/).first(),
  ).toBeVisible();
  const openapi = await request.get("/api/openapi.json");
  expect(openapi.status()).toBe(200);
  const missing = await request.get("/api/not-a-route");
  expect(missing.status()).toBe(404);
  const remote = await page.evaluate(() =>
    performance
      .getEntriesByType("resource")
      .map((entry) => entry.name)
      .filter((name) => !name.startsWith(location.origin)),
  );
  expect(remote).toEqual([]);
});

test("U08 · contraste WCAG de tokens claros y oscuros", async ({ page }) => {
  await page.goto("/");
  const values = await page.evaluate(() => {
    const pairs = [
      ["--foreground", "--background"],
      ["--muted-foreground", "--card"],
      ["--primary-foreground", "--primary"],
      ["--error", "--error-bg"],
      ["--pending", "--pending-bg"],
      ["--success", "--success-bg"],
    ];
    const luminance = (hex: string) => {
      const value = hex.replace("#", "");
      const normalized =
        value.length === 3
          ? value
              .split("")
              .map((c) => c + c)
              .join("")
          : value;
      const rgb = normalized
        .match(/../g)!
        .map((n) => parseInt(n, 16) / 255)
        .map((n) => (n <= 0.04045 ? n / 12.92 : ((n + 0.055) / 1.055) ** 2.4));
      return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
    };
    return ["light", "dark"].flatMap((theme) => {
      document.documentElement.classList.toggle("dark", theme === "dark");
      const css = getComputedStyle(document.documentElement);
      return pairs.map(([fg, bg]) => {
        const a = luminance(css.getPropertyValue(fg).trim()),
          b = luminance(css.getPropertyValue(bg).trim());
        return {
          theme,
          fg,
          bg,
          ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        };
      });
    });
  });
  for (const value of values)
    expect(value.ratio, JSON.stringify(value)).toBeGreaterThanOrEqual(4.5);
  writeFileSync(
    "../artifacts/contrast-product.json",
    JSON.stringify(values, null, 2),
  );
});
