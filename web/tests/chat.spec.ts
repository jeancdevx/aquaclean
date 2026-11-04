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

test("U02 U03 U05 U07 · sugerencia de recojo enviada, P1 Gemini real y confirmación", async ({
  page,
}) => {
  test.skip(
    process.env.RUN_REAL_PROVIDER !== "1",
    "Opt-in de llamadas reales Gemini",
  );
  const session = await (await page.request.get("/api/session")).json();
  expect(session.ai.configured).toBe(true);
  await page.goto("/");
  await page.getByRole("main", { name: "Conversación" }).getByRole("button", { name: "Programar un recojo" }).click();
  await expect(
    page.getByRole("textbox", { name: "Mensaje", exact: true }),
  ).toHaveValue(
    "Quiero programar un recojo. Ayúdame a revisar los datos necesarios.",
  );
  await page
    .getByLabel("Cliente demo verificado por operador")
    .selectOption("CLI-0001");
  const firstRun = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/runs$/.test(response.url()),
  );
  await page.getByRole("button", { name: "Enviar mensaje" }).click();
  const run = await (await firstRun).json();
  await expect.poll(async () => {
    const snapshot = await (await page.request.get(`/api/cases/${run.case_id}`)).json();
    return snapshot.runs.find((r: { id: string }) => r.id === run.id)?.status || "queued";
  }, { timeout: 150000 }).not.toMatch(/^(queued|running)$/);
  const initial = await (await page.request.get(`/api/cases/${run.case_id}`)).json();
  expect(initial.runs.find((r: { id: string }) => r.id === run.id)?.status,
    initial.messages.at(-1)?.content).toBe("completed");
  expect(initial.case.process).toBe("P1");
  expect(initial.case.status).toBe("awaiting_information");
  expect(initial.case.proposal.fields.cliente_id).toBe("CLI-0001");
  expect(initial.case.proposal.missing_fields.length).toBeGreaterThan(0);
  expect(initial.orders).toHaveLength(0);
  expect(initial.approvals).toHaveLength(0);
  expect(initial.events.some((event: { type: string }) => event.type === "run.failed")).toBe(false);
  await page.reload();
  await expect(page.getByRole("button", { name: "Enviar mensaje" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await expect(page.getByText("Logística necesita un pedido registrado en este caso.", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: "Mensaje", exact: true })).toBeEnabled();
  await page.screenshot({ path: "../artifacts/pickup-suggestion-fields.png", fullPage: true });
  writeFileSync("../artifacts/pickup-suggestion-real.json", JSON.stringify({
    synthetic: true, provider: "Gemini real", case_id: run.case_id, run_id: run.id,
    status: initial.case.status, process: initial.case.process,
    fields: initial.case.proposal.fields, missing_fields: initial.case.proposal.missing_fields,
    response: initial.messages.at(-1)?.content, orders_before_confirmation: initial.orders.length,
  }, null, 2));
  const now = new Date();
  const day = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Lima",
  }).format(now);
  const prompt = `QA de demostración sintética. Solicito recojo para CLI-0001. Solicitante: Operador Demo. Correo: demo@example.invalid. Fecha exacta: ${day}. Turno: manana. Tipo: toallas. Bolsas: 3. Presenta los siete campos para confirmar.`;
  await page
    .getByRole("textbox", { name: "Mensaje", exact: true })
    .fill(prompt);
  const draftResponse = page.waitForResponse(
    (response) => response.request().method() === "POST" && /\/runs$/.test(response.url()),
  );
  await page.getByRole("button", { name: "Enviar mensaje" }).click();
  const draftRun = await (await draftResponse).json();
  await expect.poll(async () => {
    const snapshot = await (await page.request.get(`/api/cases/${draftRun.case_id}`)).json();
    return snapshot.runs.find((r: { id: string }) => r.id === draftRun.id)?.status || "queued";
  }, { timeout: 150000 }).not.toMatch(/^(queued|running)$/);
  const draftSnapshot = await (await page.request.get(`/api/cases/${draftRun.case_id}`)).json();
  expect(draftSnapshot.runs.find((r: { id: string }) => r.id === draftRun.id)?.status,
    draftSnapshot.messages.at(-1)?.content).toBe("paused");
  await expect(
    page.getByRole("region", { name: "Revisión de propuesta" }),
  ).toBeVisible({ timeout: 150000 });
  await expect(
    page.getByText("Revisa los siete campos antes de registrar"),
  ).toBeVisible();
  const cid = await page.evaluate(() => localStorage.getItem("aquaclean-case"));
  await page.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByText("Resultado guardado")).toBeVisible({
    timeout: 30000,
  });
  await page.reload();
  await expect(page.getByText("Resultado guardado")).toBeVisible();
  const snapshot = await (await page.request.get(`/api/cases/${cid}`)).json();
  expect(snapshot.orders).toHaveLength(1);
  expect(
    snapshot.events.some(
      (event: { type: string }) => event.type === "tool.completed",
    ),
  ).toBe(true);
  expect(
    snapshot.events.some(
      (event: { type: string }) => event.type === "approval.resolved",
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../artifacts/p1-real-persisted.png",
    fullPage: true,
  });
});
