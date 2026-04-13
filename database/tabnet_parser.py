#!/usr/bin/env python3
"""
Parser robusto para as respostas do TabNet DATASUS.
O TabNet retorna HTML com uma tabela PRE dentro.
Este módulo extrai os dados e carrega no SQLite.
"""

import os
import sys
import re
import glob
import sqlite3
import logging
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.config import DATABASE_PATH, CSV_OUTPUT_DIR

logger = logging.getLogger(__name__)

# Mapeamento código IBGE (2 dígitos) -> (sigla UF, região)
UF_MAP = {
    "11": ("RO", "Norte"), "12": ("AC", "Norte"), "13": ("AM", "Norte"),
    "14": ("RR", "Norte"), "15": ("PA", "Norte"), "16": ("AP", "Norte"),
    "17": ("TO", "Norte"),
    "21": ("MA", "Nordeste"), "22": ("PI", "Nordeste"), "23": ("CE", "Nordeste"),
    "24": ("RN", "Nordeste"), "25": ("PB", "Nordeste"), "26": ("PE", "Nordeste"),
    "27": ("AL", "Nordeste"), "28": ("SE", "Nordeste"), "29": ("BA", "Nordeste"),
    "31": ("MG", "Sudeste"), "32": ("ES", "Sudeste"), "33": ("RJ", "Sudeste"),
    "35": ("SP", "Sudeste"),
    "41": ("PR", "Sul"), "42": ("SC", "Sul"), "43": ("RS", "Sul"),
    "50": ("MS", "Centro-Oeste"), "51": ("MT", "Centro-Oeste"),
    "52": ("GO", "Centro-Oeste"), "53": ("DF", "Centro-Oeste"),
}


def extract_pre_content(html: str) -> str:
    """Extrai o conteúdo da tag <pre> do HTML do TabNet."""
    # O TabNet retorna uma página HTML com os dados em uma tag <pre>
    match = re.search(r'<pre[^>]*>(.*?)</pre>', html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)

    # Às vezes o conteúdo é direto (formato PRN sem HTML)
    if ";" in html and ("Município" in html or "municipio" in html.lower()):
        return html

    return ""


def parse_tabnet_content(content: str, sep: str = ";") -> tuple:
    """
    Faz parse do conteúdo PRN/CSV do TabNet.
    Retorna (headers, rows) onde rows é lista de listas.
    """
    # Remover entidades HTML
    content = content.replace("&nbsp;", " ").replace("&amp;", "&")
    content = re.sub(r'<[^>]+>', '', content)  # remover tags HTML restantes

    lines = content.strip().split("\n")

    headers = []
    rows = []
    header_found = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Pular linhas de fonte/nota
        if any(line.upper().startswith(x) for x in ["FONTE", "NOTA", "OBS", "SELEÇÃO", "SELE"]):
            break

        if sep in line:
            parts = [p.strip().strip('"') for p in line.split(sep)]

            if not header_found:
                # Primeira linha com separador = cabeçalho
                headers = parts
                header_found = True
            else:
                if parts and parts[0]:
                    rows.append(parts)

    return headers, rows


def get_uf_regiao(codigo: str) -> tuple:
    """Extrai UF e Região do código IBGE do município."""
    if len(codigo) >= 2:
        uf_code = codigo[:2]
        if uf_code in UF_MAP:
            return UF_MAP[uf_code]
    return ("", "")


def parse_municipio(raw: str) -> dict:
    """
    Parseia o nome do município do formato TabNet.
    Ex: '120040 Acrelândia' -> {municipio, codigo, uf, regiao}
    """
    raw = raw.strip().lstrip(".")

    # Linha de subtotal/total
    if raw.lower().startswith("total"):
        return None

    # Ex: "120040 Acrelândia"
    m = re.match(r'^(\d{6,7})\s+(.+)$', raw)
    if m:
        codigo = m.group(1)
        nome = m.group(2).strip()
        uf, regiao = get_uf_regiao(codigo)
        return {"municipio": nome, "codigo_municipio": codigo, "uf": uf, "regiao": regiao}

    # Linha de agregação (Região, UF) - ignorar
    m2 = re.match(r'^(\d{1,2})\s+', raw)
    if m2:
        return None  # Linha de região/UF - não é município

    # Sem código numérico - pode ser município sem código
    if raw and raw != "-":
        return {"municipio": raw, "codigo_municipio": "", "uf": "", "regiao": ""}

    return None


def parse_value(s: str) -> float:
    """Converte string numérica brasileira para float."""
    s = s.strip().strip('"')
    if not s or s in ["-", "...", "...."]:
        return 0.0
    try:
        # Remove pontos de milhar, converte vírgula decimal
        s = s.replace(".", "").replace(",", ".")
        return float(s)
    except ValueError:
        return 0.0


def detect_content_type(filename: str) -> str:
    """Detecta o tipo de conteúdo pelo nome do arquivo."""
    fn = os.path.basename(filename).lower()
    if "quantidade" in fn or "qtd" in fn:
        return "quantidade_aprovada"
    elif "valor" in fn:
        return "valor_aprovado"
    return "unknown"


def extract_period(filename: str) -> str:
    """Extrai período do nome do arquivo. Ex: 'Jan-2024' -> '2024-01'"""
    meses = {"jan":"01","fev":"02","mar":"03","abr":"04","mai":"05","jun":"06",
              "jul":"07","ago":"08","set":"09","out":"10","nov":"11","dez":"12"}
    m = re.search(r'([a-zA-Z]{3})-(\d{4})', filename)
    if m:
        mes_str = m.group(1).lower()
        ano = m.group(2)
        mes = meses.get(mes_str, "01")
        return f"{ano}-{mes}"
    return "unknown"


def process_file(filepath: str) -> pd.DataFrame:
    """Processa um arquivo CSV/HTML do TabNet e retorna DataFrame."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    # Se for HTML, extrair o conteúdo <pre>
    if "<html" in raw.lower() or "<pre>" in raw.lower():
        content = extract_pre_content(raw)
    else:
        content = raw

    if not content or len(content) < 100:
        logger.warning(f"Arquivo sem conteúdo útil: {filepath}")
        return pd.DataFrame()

    headers, rows = parse_tabnet_content(content)

    if not headers or not rows:
        logger.warning(f"Sem dados parseados em: {filepath}")
        return pd.DataFrame()

    content_type = detect_content_type(filepath)
    period = extract_period(filepath)

    records = []

    for row in rows:
        if not row or not row[0]:
            continue

        mun_info = parse_municipio(row[0])
        if mun_info is None:
            continue  # linha de agregação ou total

        # Para cada subgrupo (colunas 1..n-1, excluir coluna Total se existir)
        for j in range(1, len(headers)):
            if j >= len(row):
                break

            subgrupo = headers[j].strip()
            if not subgrupo or subgrupo.lower() in ["total", ""]:
                continue

            valor = parse_value(row[j])

            rec = {
                "municipio": mun_info["municipio"],
                "codigo_municipio": mun_info["codigo_municipio"],
                "uf": mun_info["uf"],
                "regiao": mun_info["regiao"],
                "subgrupo_procedimento": subgrupo,
                "periodo": period,
                "quantidade_aprovada": 0,
                "valor_aprovado": 0.0,
                "data_extracao": datetime.now().isoformat(),
            }

            if content_type == "quantidade_aprovada":
                rec["quantidade_aprovada"] = int(valor)
            else:
                rec["valor_aprovado"] = valor

            records.append(rec)

    df = pd.DataFrame(records)
    logger.info(f"  {os.path.basename(filepath)}: {len(df)} registros")
    return df


def ensure_db():
    """Garante que o banco de dados e tabela existem."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS producao_ambulatorial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            municipio TEXT NOT NULL,
            codigo_municipio TEXT,
            uf TEXT,
            regiao TEXT,
            subgrupo_procedimento TEXT NOT NULL,
            periodo TEXT NOT NULL,
            quantidade_aprovada INTEGER DEFAULT 0,
            valor_aprovado REAL DEFAULT 0.0,
            data_extracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_municipio ON producao_ambulatorial(municipio)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_uf ON producao_ambulatorial(uf)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_regiao ON producao_ambulatorial(regiao)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_periodo ON producao_ambulatorial(periodo)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subgrupo ON producao_ambulatorial(subgrupo_procedimento)")
    conn.commit()
    conn.close()


def load_all(csv_dir=None):
    """Carrega todos os CSVs no banco de dados."""
    if csv_dir is None:
        csv_dir = CSV_OUTPUT_DIR

    ensure_db()

    files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")) +
                   glob.glob(os.path.join(csv_dir, "*.htm")) +
                   glob.glob(os.path.join(csv_dir, "*.html")))

    if not files:
        logger.warning(f"Nenhum arquivo em: {csv_dir}")
        return 0

    logger.info(f"Carregando {len(files)} arquivos...")

    conn = sqlite3.connect(DATABASE_PATH)
    total = 0

    for fp in files:
        try:
            df = process_file(fp)
            if df.empty:
                continue

            df.to_sql("producao_ambulatorial", conn, if_exists="append", index=False)
            conn.commit()
            total += len(df)
        except Exception as e:
            logger.error(f"Erro ao processar {fp}: {e}")

    # Consolidar: preencher valores faltantes cruzando qtd e valor do mesmo município/período/subgrupo
    logger.info("Consolidando registros duplos (qtd + valor)...")
    try:
        conn.execute("""
            DELETE FROM producao_ambulatorial
            WHERE id NOT IN (
                SELECT MIN(id) FROM producao_ambulatorial
                GROUP BY municipio, subgrupo_procedimento, periodo
            )
        """)
        conn.commit()
    except Exception as e:
        logger.warning(f"Erro na deduplicação: {e}")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM producao_ambulatorial")
    final_count = cur.fetchone()[0]
    conn.close()

    logger.info(f"Carga finalizada. Registros no banco: {final_count}")
    return final_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    n = load_all()
    print(f"Total de registros: {n}")
