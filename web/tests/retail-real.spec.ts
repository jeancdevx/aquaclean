import { test, expect } from "@playwright/test";

test("V2 · mostrador nuevo por formulario real, pausa y confirmación", async ({ page, request }) => {
  test.skip(process.env.RUN_REAL_PROVIDER !== "1", "Gemini real opt-in, separado de fakes");
  await page.goto("/");
  await page.getByRole("button", { name: "Atención al detalle", exact: true }).click();
  await page.getByLabel("Nombre del cliente").fill("Nora Prueba (sintética UI)");
  await page.getByLabel("Contacto necesario").fill("Contacto ficticio en mostrador");
  await page.getByLabel("Prenda", { exact: true }).fill("Camisa sintética");
  await page.getByLabel("Cantidad", { exact: true }).fill("2");
  await page.getByLabel("Observaciones de recepción").fill("Botón flojo declarado por operador");
  await page.getByLabel("Evidencia de recepción efectiva").fill("Operador recibió y contó las dos camisas sintéticas");
  await page.getByLabel("Declaro haber recibido y contado estas prendas.").check();
  await page.getByRole("button", { name: "Preparar confirmación", exact: true }).click();
  const confirm = page.getByRole("button", { name: "Confirmar", exact: true });
  await expect(confirm).toBeVisible({ timeout: 120000 });
  const cid = await page.evaluate(() => localStorage.getItem("aquaclean-case"));
  const before = await (await request.get(`/api/cases/${cid}`)).json();
  expect(before.orders).toHaveLength(0);
  expect(before.case.client_id).toBeNull();
  expect(before.case.proposal.quote.total).toBe("12.00");
  await confirm.click();
  await expect(page.getByRole("region", { name: "Orden al detalle persistida" })).toBeVisible({ timeout: 60000 });
  const after = await (await request.get(`/api/cases/${cid}`)).json();
  expect(after.orders[0].status).toBe("RECEIVED");
  expect(after.retail.items).toHaveLength(1);
  expect(after.retail.balance).toBe("12.00");
});
