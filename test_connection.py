#!/usr/bin/env python3
"""
Teste de conexão e extração do TabNet com payload CORRETO.
Resultado salvo em test_result.txt e test_response.html
"""
import os, sys, re, requests

OUT = "/home/lemondesk/projects/IESB/test_result.txt"

def log(msg=""):
    print(msg)
    with open(OUT, "a") as f:
        f.write(msg + "\n")

open(OUT, "w").close()  # limpar

log(f"Python: {sys.version.split()[0]} em {sys.executable}")

try:
    import pandas as pd
    log(f"✓ requests {requests.__version__} | pandas {pd.__version__}")
except ImportError as e:
    log(f"✗ {e}")
    sys.exit(1)

# Payload CORRETO - filtros usam "all", não "TODAS_AS_CATEGORIAS___"
payload = {
    "Linha":      "Município",
    "Coluna":     "Subgrupo_proced.",
    "Incremento": "Qtd.aprovada",
    "Arquivos":   "qabr2401.dbf",
    "zeradas": "1",
    "formato": "prn",
    "mostre":  "Mostra",
}

log("\n--- POST Jan/2024 Qtd.aprovada ---")
try:
    sess = requests.Session()
    sess.get("http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def", timeout=30)

    r = sess.post(
        "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def",
        data=payload,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120",
            "Referer": "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=120
    )
    r.encoding = "iso-8859-1"
    txt = r.text

    log(f"Status: {r.status_code} | Tamanho: {len(txt):,} chars")
    with open("/home/lemondesk/projects/IESB/test_response.html", "w", encoding="utf-8") as f:
        f.write(txt)

    if "EConvertError" in txt:
        log(f"✗ Erro do servidor: {txt[:300]}")
    else:
        log(f"✓ Sem EConvertError")

    # Extrair dados
    m = re.search(r'<pre[^>]*>(.*?)</pre>', txt, re.S|re.I)
    if m:
        pre = re.sub(r'<[^>]+>', '', m.group(1))
        lines = [l for l in pre.split('\n') if ';' in l]
        log(f"✓ Dados em <pre>: {len(lines)} linhas")
        if lines:
            log(f"  Cabeçalho: {lines[0][:120]}" if lines else "")
            log(f"  Linha 1:   {lines[1][:120]}" if len(lines)>1 else "")
            log(f"  Linha 2:   {lines[2][:120]}" if len(lines)>2 else "")
    else:
        log("⚠ Sem tag <pre>")
        log(f"Primeiros 500 chars: {txt[:500]}")

except Exception as e:
    import traceback
    log(f"✗ Erro: {e}")
    log(traceback.format_exc())

log("\n✅ Veja test_result.txt")
