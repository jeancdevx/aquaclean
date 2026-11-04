import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
const require=createRequire(new URL('../web/package.json',import.meta.url));
const { chromium }=require('@playwright/test');
const root=resolve(import.meta.dirname,'..');
const browser=await chromium.launch({headless:true});
try {
  const page=await browser.newPage();
  await page.goto(pathToFileURL(resolve(root,'docs/GUIA_PRUEBAS_DETALLADA.html')).href);
  await page.pdf({path:resolve(root,'docs/GUIA_PRUEBAS_DETALLADA.pdf'),format:'A4',printBackground:true,displayHeaderFooter:true,
    headerTemplate:'<div style="font:8px Arial;width:100%;padding:0 16mm;color:#475569">Aqua Clean · Guía de pruebas V1 · Datos de demostración</div>',
    footerTemplate:'<div style="font:8px Arial;width:100%;padding:0 16mm;text-align:right;color:#475569"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin:{top:'20mm',bottom:'20mm',left:'16mm',right:'16mm'}});
  console.log('docs/GUIA_PRUEBAS_DETALLADA.pdf');
} finally {await browser.close();}
