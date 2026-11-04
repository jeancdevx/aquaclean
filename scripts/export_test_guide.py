"""Export the checked-in Markdown test guide to a standalone printable HTML file."""

from pathlib import Path

from markdown_it import MarkdownIt

source = Path("docs/GUIA_PRUEBAS_DETALLADA.md")
body = MarkdownIt("commonmark", {"html": False}).enable("table").render(source.read_text())
style = """
@page { size: A4; margin:20mm 16mm; }
body {font:11pt/1.55 Arial,sans-serif;color:#0F172A;max-width:920px;margin:32px auto;padding:0 20px;background:white;}
h1 {font-size:28pt;line-height:1.2;color:#0F766E;} h2 {font-size:18pt;border-bottom:1px solid #CBD5E1;padding-bottom:8px;margin-top:32px;} h3{font-size:13pt;margin-top:24px;}
h1,h2,h3{break-after:avoid;} a{color:#0F766E;overflow-wrap:anywhere;} p,li{orphans:3;widows:3;}
code{font:9pt/1.5 monospace;overflow-wrap:anywhere;} pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#F1F5F9;border:1px solid #CBD5E1;border-radius:6px;padding:12px;break-inside:avoid;}
blockquote{margin:16px 0;padding:8px 16px;border-left:4px solid #0F766E;background:#F0FDFA;break-inside:avoid;}
table{border-collapse:collapse;width:100%;font-size:9pt;table-layout:fixed;}th,td{border:1px solid #CBD5E1;text-align:left;vertical-align:top;padding:8px;overflow-wrap:anywhere;}th{background:#F1F5F9;}thead{display:table-header-group;}tr{break-inside:avoid;}
@media print {body{margin:0;padding:0;max-width:none;}a{text-decoration:none;}h2{margin-top:24px;}pre{font-size:8pt;}}
"""
Path("docs/GUIA_PRUEBAS_DETALLADA.html").write_text(
    '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Guía de pruebas Aqua Clean V1</title><style>'
    + style
    + "</style></head><body>"
    + body
    + "</body></html>"
)
print("docs/GUIA_PRUEBAS_DETALLADA.html")
