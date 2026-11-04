// Exact-source diagram/snippet renderer. No image generation, no mocked API.
import { chromium } from "@playwright/test";
import { createServer } from "node:http";
import { readFile, writeFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const output = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const bpmnPath = require.resolve("bpmn-js/dist/bpmn-viewer.development.js");
const mermaidDir = path.dirname(require.resolve("mermaid"));
const html = `<!doctype html><html lang="es"><meta charset="utf-8"><style>body{margin:0;background:#fff;color:#0f172a;font-family:system-ui}h1{font-size:22px;margin:24px}#canvas{width:2400px;height:1600px}#mermaid{padding:32px;width:max-content}#snippet{padding:32px;width:1240px}pre{font:16px/1.6 monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f8fafc;padding:24px;border:1px solid #cbd5e1}small{color:#475569}</style><script src="/bpmn.js"></script><h1 id="title"></h1><div id="canvas"></div><div id="mermaid"></div><article id="snippet"></article><script type="module">import mermaid from '/mermaid/mermaid.esm.min.mjs';mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',themeVariables:{fontSize:'18px',primaryColor:'#f0fdfa',primaryTextColor:'#0f172a',lineColor:'#475569'}});window.mermaid=mermaid;</script></html>`;
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, "http://localhost");
    if (url.pathname === "/") { res.setHeader("Content-Type", "text/html"); return res.end(html); }
    const location = url.pathname === "/bpmn.js" ? bpmnPath : url.pathname.startsWith("/mermaid/") ? path.resolve(mermaidDir, url.pathname.slice(9)) : "";
    if (!location || (location !== bpmnPath && !location.startsWith(mermaidDir + path.sep))) { res.writeHead(404); return res.end(); }
    res.setHeader("Content-Type", "text/javascript"); res.end(await readFile(location));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 2400, height: 1700 }, deviceScaleFactor: 1 });
  await page.goto(`http://127.0.0.1:${server.address().port}`);
  await page.waitForFunction(() => !!window.mermaid);
  const imports = [];
  for (const file of (await readdir(path.join(repo, "docs/bpmn"))).filter(f => f.endsWith("-v2.bpmn")).sort()) {
    const xml = await readFile(path.join(repo, "docs/bpmn", file), "utf8");
    const result = await page.evaluate(async ({ xml, file }) => {
      document.querySelector("#title").textContent = file + " · bpmn.io · XML descriptivo V2";
      document.querySelector("#canvas").style.display = "block"; document.querySelector("#mermaid").style.display = "none";
      if (window.viewer) window.viewer.destroy();
      window.viewer = new window.BpmnJS({ container: "#canvas" });
      const { warnings } = await window.viewer.importXML(xml);
      const box = window.viewer.get("canvas").viewbox();
      const size = window.viewer.get("canvas").getRootElement();
      const bounds = window.viewer.get("canvas").viewbox().inner;
      document.querySelector("#canvas").style.width = Math.ceil(bounds.width + 100) + "px";
      document.querySelector("#canvas").style.height = Math.ceil(bounds.height + 100) + "px";
      window.viewer.get("canvas").resized();
      window.viewer.get("canvas").zoom("fit-viewport");
      return { warnings: warnings.map(w => w.message), svg: (await window.viewer.saveSVG()).svg, root: size.id, box };
    }, { xml, file });
    const name = file.replace(/\.bpmn$/, "");
    await writeFile(path.join(output, "03-bpmn", file), xml);
    await writeFile(path.join(output, "03-bpmn", name + ".svg"), result.svg);
    await page.locator("#canvas").screenshot({ path: path.join(output, "03-bpmn", name + ".png") });
    imports.push({ file, imported: true, warnings: result.warnings, root: result.root, tool: "bpmn-js 18.31.1 / Chromium" });
  }
  await writeFile(path.join(output, "03-bpmn/importacion-bpmn-io.json"), JSON.stringify(imports, null, 2));
  const diagrams = [];
  for (const dir of ["01-lcel", "02-langgraph", "09-ecosistema"]) {
    for (const file of (await readdir(path.join(output, dir))).filter(f => f.endsWith(".mmd"))) diagrams.push({ dir, file });
  }
  for (const { dir, file } of diagrams) {
    const definition = await readFile(path.join(output, dir, file), "utf8");
    const svg = await page.evaluate(async text => {
      document.querySelector("#canvas").style.display = "none"; document.querySelector("#title").textContent = "Exportación exacta de fuente Mermaid";
      const container = document.querySelector("#mermaid");container.style.display = "block";
      const { svg } = await window.mermaid.render("diagram" + Date.now(), text); container.innerHTML = svg;
      const element = container.querySelector("svg"), box = element.viewBox.baseVal;
      element.style.maxWidth = "none"; element.setAttribute("width", box.width);element.setAttribute("height", box.height);
      return element.outerHTML;
    }, definition);
    await writeFile(path.join(output, dir, file.replace(/\.mmd$/, ".svg")), svg);
    await page.locator("#mermaid").screenshot({ path: path.join(output, dir, file.replace(/\.mmd$/, ".png")) });
  }
  for (const dir of ["01-lcel", "06-deepagents"]) {
    const snippets = JSON.parse(await readFile(path.join(output, dir, "extractos.json"), "utf8"));
    for (const snippet of snippets) {
      await page.evaluate(data => {
        document.querySelector("#title").textContent = "Extracto renderizado de código · no es captura de VS Code";
        document.querySelector("#canvas").style.display = "none";document.querySelector("#mermaid").style.display = "none";
        const article = document.querySelector("#snippet");article.replaceChildren();
        const title = document.createElement("h2");title.textContent = `${data.path}:${data.start} · ${data.symbol}`;
        const pre = document.createElement("pre");pre.textContent = data.lines.map((line, i) => `${String(data.start + i).padStart(4)}  ${line}`).join("\n");
        article.append(title, pre);
      }, snippet);
      await page.locator("#snippet").screenshot({ path: path.join(output, dir, snippet.image) });
    }
  }
  const investigation = JSON.parse(await readFile(path.join(output, "06-deepagents/ejecuciones-reales.json"), "utf8"));
  const completed = investigation.runs.filter(r => r.result.proposal);
  await page.evaluate(data => {
    document.querySelector("#title").textContent = "Registro real de la aplicación · Deep Agents SDK + Gemini · no es LangSmith";
    document.querySelector("#canvas").style.display = "none";document.querySelector("#mermaid").style.display = "none";
    const article = document.querySelector("#snippet");article.replaceChildren();
    for (const run of data) {
      const heading = document.createElement("h2");heading.textContent = `Caso ${run.case_id} · ${run.result.proposal.action}`;
      const pre = document.createElement("pre");pre.textContent = `app_run_id: ${run.app_run_id}\nDuración: ${run.result.duration_ms} ms · llamadas al modelo: ${run.result.model_calls}\nCosto: desconocido\n\n` + run.result.journal.map(j => `${j.agent} → ${j.tool}` + (j.args.subagent_type ? ` (${j.args.subagent_type})` : "") + (j.args.todos ? "\n" + j.args.todos.map(t => `  ${t.status}: ${t.content}`).join("\n") : "")).join("\n");
      article.append(heading, pre);
    }
  }, completed);
  await page.locator("#snippet").screenshot({ path: path.join(output, "06-deepagents/planificacion-delegacion-real.png") });
} finally { await browser.close(); server.close(); }
