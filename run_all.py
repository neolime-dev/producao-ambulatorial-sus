#!/usr/bin/env python3
"""
Pipeline completo DATASUS - Produção Ambulatorial (SIA/SUS).
Extrai dados via HTTP POST direto no TabNet + carrega no SQLite.

Uso:
  python run_all.py --test          # Apenas Jan/2024 (2 requisições)
  python run_all.py --months 3      # 3 meses (6 requisições)
  python run_all.py                 # 25 meses (50 requisições)
  python run_all.py --load-only     # Só carrega HTMLs já baixados
"""
import os, sys, time, sqlite3, logging, re, glob
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DATASUS")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_DIR   = os.path.join(BASE_DIR, "data", "csv")
DB_PATH   = os.path.join(BASE_DIR, "database", "producao_ambulatorial.db")
os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def"
TABNET_FORM = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def"

PERIODOS = [(y, m) for y in [2024, 2025] for m in range(1, 13)] + [(2026, 1)]
MESES    = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

UF_MAP = {
    "11":("RO","Norte"),  "12":("AC","Norte"),  "13":("AM","Norte"),  "14":("RR","Norte"),
    "15":("PA","Norte"),  "16":("AP","Norte"),  "17":("TO","Norte"),
    "21":("MA","Nordeste"),"22":("PI","Nordeste"),"23":("CE","Nordeste"),
    "24":("RN","Nordeste"),"25":("PB","Nordeste"),"26":("PE","Nordeste"),
    "27":("AL","Nordeste"),"28":("SE","Nordeste"),"29":("BA","Nordeste"),
    "31":("MG","Sudeste"), "32":("ES","Sudeste"), "33":("RJ","Sudeste"),"35":("SP","Sudeste"),
    "41":("PR","Sul"),     "42":("SC","Sul"),     "43":("RS","Sul"),
    "50":("MS","Centro-Oeste"),"51":("MT","Centro-Oeste"),
    "52":("GO","Centro-Oeste"),"53":("DF","Centro-Oeste"),
}

def plabel(y, m): return f"{MESES[m-1]}/{y}"
def pfname(y, m): return f"qabr{y%100:02d}{m:02d}.dbf"

# ─── EXTRAÇÃO ─────────────────────────────────────────────────────────────────
def fetch_one(session, year, month, ckey, cval, delay=3):
    label = plabel(year, month)
    logger.info(f"  → {ckey} {label}")
    
    hdrs = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
        "Referer": TABNET_FORM,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    payload = {}
    for attempt in range(3):
        try:
            # 1) Requisitar o formulário atualizado para pegar os campos ocultos e dropdowns default
            r_form = session.get(TABNET_FORM, headers=hdrs, timeout=30)
            r_form.encoding = "iso-8859-1"
            html = r_form.text
            
            import re
            # Extrair input tags
            inputs = re.findall(r'<input([^>]+)>', html, re.I)
            for attrs in inputs:
                name_m = re.search(r'name="([^"]+)"', attrs, re.I)
                value_m = re.search(r'value="([^"]*)"', attrs, re.I)
                type_m = re.search(r'type="([^"]+)"', attrs, re.I)
                if name_m:
                    name = name_m.group(1)
                    val = value_m.group(1) if value_m else ""
                    t = type_m.group(1).lower() if type_m else "text"
                    if t in ('hidden', 'text', 'submit'):
                        payload[name] = val
                    elif t == 'checkbox' and 'checked' in attrs.lower():
                        payload[name] = val
                    elif t == 'radio' and 'checked' in attrs.lower():
                        payload[name] = val

            # Extrair select tags
            selects = re.split(r'<select', html, flags=re.I)[1:]
            for s_block in selects:
                name_m = re.search(r'name="([^"]+)"', s_block[:100], re.I)
                if name_m:
                    name = name_m.group(1)
                    end_idx = s_block.lower().find('</select>')
                    select_content = s_block[:end_idx] if end_idx != -1 else s_block
                    # Tentar pegar option selected
                    sel_m = re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', select_content, re.I)
                    if not sel_m: # senao pega o primeiro
                        sel_m = re.search(r'<option[^>]*value="([^"]*)"', select_content, re.I)
                    if sel_m:
                        payload[name] = sel_m.group(1)

            # 2) Modificar o payload com os nossos parâmetros
            payload["Linha"] = "Município"
            payload["Coluna"] = "Subgrupo_proced."
            payload["Incremento"] = cval         # "Qtd.aprovada" ou "Valor_aprovado"
            payload["Arquivos"] = pfname(year, month) # ex: "qabr2401.dbf"
            payload["zeradas"] = "1"
            payload["formato"] = "prn"
            payload["mostre"] = "Mostra"
            
            import urllib.parse
            encoded_payload = urllib.parse.urlencode(payload, encoding='iso-8859-1')

            # Post headers
            post_hdrs = hdrs.copy()
            post_hdrs["Content-Type"] = "application/x-www-form-urlencoded"

            # 3) Enviar o POST
            r = session.post(TABNET_URL, data=encoded_payload, headers=post_hdrs, timeout=120)
            r.encoding = "iso-8859-1"
            txt = r.text

            if r.status_code != 200:
                logger.warning(f"    HTTP {r.status_code}, tentativa {attempt+1}")
                time.sleep(8); continue

            if len(txt) < 5000: # respostas muito pequenas no tabnet indicam erro ou index page
                if "EConvertError" in txt or "not a valid integer" in txt:
                    logger.error(f"    ERRO servidor: EConvertError")
                    return None
                logger.warning(f"    Resposta pequena ({len(txt)} chars)")
                time.sleep(8); continue

            if "Munic" not in txt and "munic" not in txt.lower():
                logger.warning(f"    Sem dados esperados ({len(txt)} chars)")
                time.sleep(8); continue

            fp = os.path.join(CSV_DIR, f"sia_{ckey}_{label.replace('/','_')}.html")
            with open(fp, "w", encoding="utf-8") as f:
                f.write(txt)
            logger.info(f"    ✓ {os.path.basename(fp)} ({len(txt):,} chars)")
            time.sleep(delay)
            return fp

        except Exception as e:
            logger.error(f"    Erro tentativa {attempt+1}: {e}")
            time.sleep(10)

    logger.error(f"    ✗ Falhou após 3 tentativas: {ckey}/{label}")
    return None

def extract(periodos, delay=3):
    import requests
    conteudos = [
        ("quantidade_aprovada", "Qtd.aprovada"),
        ("valor_aprovado",      "Valor_aprovado"),
    ]
    sess = requests.Session()
    try:
        sess.get(TABNET_FORM, timeout=30)
        logger.info("Sessão TabNet iniciada")
    except Exception as e:
        logger.warning(f"Sessão inicial falhou: {e}")

    files, errs = [], []
    total = len(periodos) * len(conteudos)
    n = 0
    for ckey, cval in conteudos:
        for y, m in periodos:
            n += 1
            print(f"[{n:02d}/{total}] {ckey:25s} {plabel(y,m)}", end=" ... ", flush=True)
            fp = fetch_one(sess, y, m, ckey, cval, delay)
            if fp: files.append(fp); print("✓ OK")
            else:  errs.append(f"{ckey}/{plabel(y,m)}"); print("✗ FALHOU")
    return files, errs

# ─── BANCO DE DADOS ────────────────────────────────────────────────────────────
def setup_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS producao_ambulatorial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            municipio TEXT, codigo_municipio TEXT,
            uf TEXT, regiao TEXT,
            subgrupo_procedimento TEXT,
            periodo TEXT,
            quantidade_aprovada INTEGER DEFAULT 0,
            valor_aprovado REAL DEFAULT 0.0,
            data_extracao TEXT
        )""")
    for idx in ["municipio","uf","periodo","subgrupo_procedimento","regiao"]:
        conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{idx[:6]} ON producao_ambulatorial({idx})")
    conn.commit()
    return conn

# ─── PARSING ──────────────────────────────────────────────────────────────────
def parse_num(s):
    s = str(s).strip().strip('"')
    if not s or s in ["-","...","....",""]: return 0.0
    try: return float(s.replace(".","").replace(",","."))
    except: return 0.0

def get_uf_reg(cod):
    return UF_MAP.get(cod[:2] if len(cod)>=2 else "", ("",""))

def parse_mun(raw):
    raw = raw.strip().lstrip(".")
    if raw.lower().startswith("total"): return None
    m = re.match(r'^(\d{6,7})\s+(.+)$', raw)
    if m:
        cod, nome = m.group(1), m.group(2).strip()
        uf, reg = get_uf_reg(cod)
        return dict(municipio=nome, codigo_municipio=cod, uf=uf, regiao=reg)
    if re.match(r'^\d{1,5}\s', raw): return None  # agregação
    if raw.strip(): return dict(municipio=raw.strip(), codigo_municipio="", uf="", regiao="")
    return None

def extract_data(html):
    """Extrai conteúdo de dados do HTML do TabNet (conteúdo dentro de <pre>)."""
    m = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.S|re.I)
    if m:
        t = m.group(1)
        t = re.sub(r'<[^>]+>', '', t)
        return t.replace("&nbsp;"," ").replace("&amp;","&").replace("&lt;","<")
    if ";" in html: return html
    return ""

def period_from_name(fn):
    mmap = {"jan":"01","fev":"02","mar":"03","abr":"04","mai":"05","jun":"06",
            "jul":"07","ago":"08","set":"09","out":"10","nov":"11","dez":"12"}
    m = re.search(r'([A-Za-z]{3})_(\d{4})', fn)
    if m: return f"{m.group(2)}-{mmap.get(m.group(1).lower(),'01')}"
    m2 = re.search(r'(\d{4})_(\d{2})', fn)
    if m2: return f"{m2.group(1)}-{m2.group(2)}"
    return "unknown"

def ctype_from_name(fn):
    fn = fn.lower()
    if "quantidade" in fn: return "quantidade_aprovada"
    if "valor" in fn: return "valor_aprovado"
    return "unknown"

def process_file(fp):
    with open(fp, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    if "<html" in raw.lower() or "<pre" in raw.lower():
        content = extract_data(raw)
    else:
        content = raw

    if len(content) < 100:
        logger.warning(f"  Conteúdo insuficiente em {os.path.basename(fp)}")
        return []

    lines = content.strip().split("\n")
    headers, rows, hfound = [], [], False

    for line in lines:
        line = line.strip()
        if not line: continue
        lu = line.upper()
        if lu.startswith(("FONTE","NOTA","OBS","SELECAO","SELEÇÃO")): break
        if ";" in line:
            parts = [p.strip().strip('"') for p in line.split(";")]
            if not hfound:
                headers = parts
                hfound = True
            elif parts and parts[0]:
                rows.append(parts)

    if not headers or not rows:
        logger.warning(f"  Sem dados parseados em {os.path.basename(fp)}")
        return []

    ctype  = ctype_from_name(fp)
    period = period_from_name(os.path.basename(fp))
    records = []

    for row in rows:
        if not row or not row[0]: continue
        mi = parse_mun(row[0])
        if mi is None: continue

        for j in range(1, len(headers)):
            if j >= len(row): break
            sg = headers[j].strip()
            if not sg or sg.lower() == "total": continue
            val = parse_num(row[j])
            rec = dict(
                municipio=mi["municipio"], codigo_municipio=mi["codigo_municipio"],
                uf=mi["uf"], regiao=mi["regiao"],
                subgrupo_procedimento=sg, periodo=period,
                quantidade_aprovada=0, valor_aprovado=0.0,
                data_extracao=datetime.now().isoformat()
            )
            if ctype == "quantidade_aprovada": rec["quantidade_aprovada"] = int(val)
            else: rec["valor_aprovado"] = float(val)
            records.append(rec)

    return records

def load_to_db(conn, files):
    try:
        import pandas as pd
    except ImportError:
        logger.error("pandas não instalado")
        return 0

    total = 0
    for fp in files:
        recs = process_file(fp)
        if not recs:
            logger.warning(f"  0 registros de {os.path.basename(fp)}")
            continue
        df = pd.DataFrame(recs)
        df.to_sql("producao_ambulatorial", conn, if_exists="append", index=False)
        conn.commit()
        total += len(df)
        logger.info(f"  {len(df):,} registros de {os.path.basename(fp)}")
    return total

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Pipeline DATASUS SIA/SUS")
    p.add_argument("--test",      action="store_true", help="Só Jan/2024")
    p.add_argument("--months",    type=int, default=0, help="Número de meses")
    p.add_argument("--delay",     type=float, default=3.0, help="Delay entre requests (s)")
    p.add_argument("--load-only", action="store_true", help="Só carregar arquivos existentes")
    args = p.parse_args()

    # Verificar dependências
    try:
        import requests, pandas
    except ImportError as e:
        print(f"❌ Dependência faltando: {e}")
        print("   Execute: pip install requests pandas")
        sys.exit(1)

    print("\n" + "="*60)
    print("  DATASUS - Produção Ambulatorial (SIA/SUS)")
    print("="*60)

    periodos = PERIODOS
    if args.test:       periodos = [(2024, 1)]
    elif args.months>0: periodos = PERIODOS[:args.months]

    # 1. Extração
    if not args.load_only:
        n_per = len(periodos)
        print(f"\n📡 Extraindo {n_per} meses × 2 = {n_per*2} requisições")
        print(f"   Delay: {args.delay}s | Servidor: tabnet.datasus.gov.br\n")
        files, errs = extract(periodos, delay=args.delay)
        print(f"\n✓ Extração: {len(files)} arquivos OK | {len(errs)} falhas")
        if errs: print(f"  Falhas: {errs}")
    else:
        files = sorted(glob.glob(os.path.join(CSV_DIR,"*.html")) +
                       glob.glob(os.path.join(CSV_DIR,"*.csv")))
        print(f"📂 Usando {len(files)} arquivos existentes")

    if not files:
        print("\n⚠️  Nenhum arquivo para carregar.")
        sys.exit(1)

    # 2. Banco
    print("\n📦 Configurando banco de dados...")
    conn = setup_db()
    conn.execute("DELETE FROM producao_ambulatorial")
    conn.commit()
    print(f"   DB: {DB_PATH}")

    # 3. Carga
    print("\n📥 Carregando dados no banco...")
    total_recs = load_to_db(conn, files)

    # 4. Resultado
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), COUNT(DISTINCT municipio), COUNT(DISTINCT uf),
               COUNT(DISTINCT periodo), SUM(quantidade_aprovada), SUM(valor_aprovado)
        FROM producao_ambulatorial
    """)
    row = cur.fetchone()
    conn.close()

    print("\n" + "="*60)
    print(f"  Registros inseridos: {row[0]:>15,}")
    print(f"  Municípios:          {row[1]:>15,}")
    print(f"  UFs:                 {row[2]:>15,}")
    print(f"  Períodos:            {row[3]:>15,}")
    print(f"  Qtd. Aprovada:       {(row[4] or 0):>15,.0f}")
    print(f"  Valor Aprovado: R$   {(row[5] or 0):>12,.2f}")
    print("="*60)

    if row[0] == 0:
        print("\n⚠️  Nenhum registro foi carregado!")
        print("   Verifique os arquivos HTML em data/csv/")
    else:
        print("\n🚀 Inicie o dashboard:")
        print("   streamlit run streamlit_app/app.py\n")
