// Supplemental captures of actual persisted state and actual perceived attachments.
import { chromium } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const output = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const result = JSON.parse(await readFile(path.join(output, "07-aplicacion/recorrido-proveedor-real.json"), "utf8"));
if (result.status !== "passed") throw new Error("A completed real run is required; no simulated capture");
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1600 } });
  await page.goto("http://127.0.0.1:8000");
  await page.evaluate(cid => localStorage.setItem("aquaclean-case", cid), result.reception_case_id);
  await page.reload();
  const order = page.getByRole("region", { name: "Orden al detalle persistida" });
  await order.getByText(/CLOSED/).waitFor();
  await order.getByText("Comprobante de demostración · final", { exact: true }).click();
  await order.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(output, "07-aplicacion/07-comprobante-final-visible.png"), fullPage: true });
  for (const [index, file] of ["recepcion-sintetica.png", "recepcion-sintetica.pdf", "recepcion-sintetica.wav"].entries()) {
    const attachment = page.locator(".attachment").filter({ has: page.getByRole("link", { name: file, exact: true }) });
    await attachment.locator("summary").click();
    await attachment.scrollIntoViewIfNeeded();
    await attachment.screenshot({ path: path.join(output, `07-aplicacion/08-medio-${index + 1}-percepcion-real.png`) });
  }
  await page.getByRole("button", { name: "Nueva conversación", exact: true }).click();
  await page.getByRole("button", { name: "Atención al detalle", exact: true }).click();
  await page.getByLabel("Nombre del cliente").fill("Lucía Muestra (sintética)");
  await page.getByLabel("Contacto necesario").fill("Contacto sintético en mostrador");
  await page.getByLabel("Prenda", { exact: true }).fill("Camisa sintética");
  await page.getByLabel("Cantidad", { exact: true }).fill("2");
  await page.getByLabel("Observaciones de recepción").fill("Botón flojo declarado");
  await page.getByLabel("Evidencia de recepción efectiva").fill("Operador recibió y contó prendas sintéticas");
  await page.getByLabel("Declaro haber recibido y contado estas prendas.").check();
  await page.screenshot({ path: path.join(output, "07-aplicacion/09-formulario-mostrador-real.png"), fullPage: true });
  await page.getByRole("combobox", { name: "Operación de Atención" }).selectOption("request_pickup");
  await page.screenshot({ path: path.join(output, "07-aplicacion/10-formulario-solicitud-previa.png"), fullPage: true });
  await writeFile(path.join(output, "07-aplicacion/capturas-adicionales.json"), JSON.stringify({ kind: "actual_ui", mocked_routes: false, generated_images: false, case_id: result.reception_case_id, purpose: "Closed order, visible demo receipt, actual attachment observations; forms filled but not submitted" }, null, 2));
} finally { await browser.close(); }
