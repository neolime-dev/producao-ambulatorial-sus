#!/usr/bin/env python3
"""
Pipeline de carga dos CSVs extraídos para o banco de dados SQLite.
Processa os arquivos CSV do TabNet, limpa e normaliza os dados,
e insere na tabela producao_ambulatorial.
"""

import os
import sys
import re
import glob
import sqlite3
import logging
from datetime import datetime

import pandas as pd
import numpy as np

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.config import DATABASE_PATH, CSV_OUTPUT_DIR, PERIODO_LABELS
from database.db_setup import create_database

logger = logging.getLogger(__name__)

# Mapeamento de código IBGE UF -> Nome UF e Região
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

# Para extrair UF do nome do município quando vem no formato "120000 Município - AC"
REGIOES_MAP = {
    "1": "Norte", "2": "Nordeste", "3": "Sudeste",
    "4": "Sul", "5": "Centro-Oeste"
}


def extract_municipio_info(municipio_str: str) -> dict:
    """
    Extrai informações do município do formato TabNet.
    Formatos possíveis:
    - "120040 Acrelândia"
    - "1 Região Norte"
    - "..12 Acre"
    - "....120040 Acrelândia"
    """
    result = {
        "municipio": municipio_str.strip(),
        "codigo_municipio": "",
        "uf": "",
        "regiao": ""
    }

    # Limpar o nome - remover pontos de indentação do TabNet
    cleaned = municipio_str.strip().lstrip(".")

    # Tentar extrair código numérico
    match = re.match(r"^(\d+)\s+(.+)$", cleaned)
    if match:
        codigo = match.group(1)
        nome = match.group(2).strip()
        result["municipio"] = nome
        result["codigo_municipio"] = codigo

        # Identificar UF a partir do código IBGE
        if len(codigo) >= 2:
            uf_code = codigo[:2]
            if uf_code in UF_MAP:
                result["uf"] = UF_MAP[uf_code][0]
                result["regiao"] = UF_MAP[uf_code][1]

        # Verificar se é código de região (1 dígito)
        if len(codigo) == 1 and codigo in REGIOES_MAP:
            result["regiao"] = REGIOES_MAP[codigo]
            result["municipio"] = nome

    return result


def parse_numeric_value(value_str: str) -> float:
    """
    Converte valores numéricos do formato TabNet.
    Trata: "-", "0", "1.234", "1.234,56", etc.
    """
    if not value_str or value_str.strip() in ["-", "", "...", "....", "0"]:
        return 0.0

    # Limpar
    value_str = value_str.strip()

    # Remove aspas
    value_str = value_str.strip('"').strip()

    if value_str in ["-", ""]:
        return 0.0

    try:
        # Formato brasileiro: ponto para milhar, vírgula para decimal
        # Remover pontos de milhar
        value_str = value_str.replace(".", "")
        # Converter vírgula decimal para ponto
        value_str = value_str.replace(",", ".")
        return float(value_str)
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter valor: '{value_str}'")
        return 0.0


def load_csv_file(filepath: str, content_type: str) -> pd.DataFrame:
    """
    Carrega e processa um arquivo CSV do TabNet.

    Args:
        filepath: Caminho do arquivo CSV
        content_type: 'quantidade_aprovada' ou 'valor_aprovado'

    Returns:
        DataFrame processado
    """
    logger.info(f"Processando: {filepath}")

    # Ler o conteúdo bruto
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Identificar início e fim dos dados
    lines = content.strip().split("\n")

    # Encontrar a linha de cabeçalho (primeira com ';')
    header_idx = None
    data_start = None
    data_end = None

    for i, line in enumerate(lines):
        if ";" in line and header_idx is None:
            # Verificar se é cabeçalho (não é nota de rodapé)
            if not line.strip().startswith('"Fonte') and not line.strip().startswith('"Nota'):
                header_idx = i
                data_start = i + 1
                continue

        if data_start is not None and i >= data_start:
            stripped = line.strip()
            if (stripped.startswith('"Fonte') or
                stripped.startswith('"Total') or
                stripped.startswith('"Nota') or
                stripped == "" or
                not ";" in stripped):
                # Incluir linha de Total se existir
                if stripped.startswith('"Total'):
                    data_end = i + 1
                else:
                    data_end = i
                break

    if data_end is None:
        data_end = len(lines)

    if header_idx is None:
        logger.error(f"Não encontrou cabeçalho no arquivo: {filepath}")
        return pd.DataFrame()

    # Extrair cabeçalho e dados
    header_line = lines[header_idx]
    data_lines = lines[data_start:data_end]

    # Parse header
    headers = [h.strip().strip('"') for h in header_line.split(";")]

    # A primeira coluna é Município
    if headers and headers[0]:
        headers[0] = "Municipio"

    # Parse linhas de dados
    records = []
    for line in data_lines:
        if not line.strip() or not ";" in line:
            continue

        parts = line.split(";")
        if len(parts) < 2:
            continue

        municipio_raw = parts[0].strip().strip('"')

        # Pular linhas de total e cabeçalhos internos
        if municipio_raw.lower().startswith("total"):
            continue

        # Extrair informações do município
        mun_info = extract_municipio_info(municipio_raw)

        # Filtrar apenas municípios (códigos com 6+ dígitos)
        # Pular linhas de região e UF (códigos com 1-2 dígitos)
        codigo = mun_info["codigo_municipio"]
        if codigo and len(codigo) < 6:
            # É uma linha de agregação (região ou UF), pular
            continue

        # Para cada subgrupo (coluna), criar um registro
        for j in range(1, len(headers)):
            if j >= len(parts):
                break

            subgrupo = headers[j] if j < len(headers) else f"Col_{j}"
            if not subgrupo or subgrupo == "Total":
                continue

            value = parse_numeric_value(parts[j])

            record = {
                "municipio": mun_info["municipio"],
                "codigo_municipio": mun_info["codigo_municipio"],
                "uf": mun_info["uf"],
                "regiao": mun_info["regiao"],
                "subgrupo_procedimento": subgrupo,
            }

            if content_type == "quantidade_aprovada":
                record["quantidade_aprovada"] = int(value)
                record["valor_aprovado"] = 0.0
            else:
                record["quantidade_aprovada"] = 0
                record["valor_aprovado"] = value

            records.append(record)

    df = pd.DataFrame(records)
    logger.info(f"  Registros extraídos: {len(df)}")
    return df


def extract_period_from_filename(filename: str) -> str:
    """
    Extrai o período do nome do arquivo.
    Ex: "producao_ambulatorial_quantidade_aprovada_Jan-2024.csv" -> "2024-01"
    """
    meses_map = {
        "jan": "01", "fev": "02", "mar": "03", "abr": "04",
        "mai": "05", "jun": "06", "jul": "07", "ago": "08",
        "set": "09", "out": "10", "nov": "11", "dez": "12"
    }

    # Tentar formato "Mmm-YYYY"
    match = re.search(r"([A-Za-z]{3})-?(\d{4})", filename)
    if match:
        mes_str = match.group(1).lower()
        ano = match.group(2)
        mes = meses_map.get(mes_str, "01")
        return f"{ano}-{mes}"

    # Tentar formato YYMM
    match = re.search(r"(\d{2})(\d{2})\.csv", filename)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        full_year = 2000 + year
        return f"{full_year}-{month:02d}"

    return "unknown"


def detect_content_type(filename: str) -> str:
    """Detecta o tipo de conteúdo pelo nome do arquivo."""
    filename_lower = filename.lower()
    if "quantidade" in filename_lower or "qtd" in filename_lower:
        return "quantidade_aprovada"
    elif "valor" in filename_lower:
        return "valor_aprovado"
    return "unknown"


def load_all_csvs(csv_dir: str = None):
    """
    Carrega todos os CSVs do diretório para o banco de dados.
    """
    if csv_dir is None:
        csv_dir = CSV_OUTPUT_DIR

    # Garantir que o banco existe
    create_database()

    # Encontrar todos os CSVs
    csv_files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))
    if not csv_files:
        logger.warning(f"Nenhum CSV encontrado em: {csv_dir}")
        print(f"✗ Nenhum CSV encontrado em: {csv_dir}")
        return

    logger.info(f"Encontrados {len(csv_files)} arquivos CSV")
    conn = sqlite3.connect(DATABASE_PATH)

    total_inserted = 0

    for filepath in csv_files:
        filename = os.path.basename(filepath)
        content_type = detect_content_type(filename)
        periodo = extract_period_from_filename(filename)

        if content_type == "unknown":
            logger.warning(f"Tipo de conteúdo desconhecido: {filename}")
            continue

        logger.info(f"Carregando: {filename} (tipo={content_type}, período={periodo})")

        try:
            df = load_csv_file(filepath, content_type)

            if df.empty:
                logger.warning(f"DataFrame vazio para: {filename}")
                continue

            # Adicionar período
            df["periodo"] = periodo
            df["data_extracao"] = datetime.now().isoformat()

            # Inserir no banco
            df.to_sql("producao_ambulatorial", conn, if_exists="append", index=False)

            inserted = len(df)
            total_inserted += inserted

            # Registrar metadados
            conn.execute(
                """INSERT INTO extracao_metadata
                   (arquivo_origem, tipo_conteudo, periodo, registros_inseridos)
                   VALUES (?, ?, ?, ?)""",
                (filename, content_type, periodo, inserted)
            )
            conn.commit()

            logger.info(f"  ✓ Inseridos {inserted} registros")

        except Exception as e:
            logger.error(f"Erro ao processar {filename}: {e}")
            conn.rollback()

    conn.close()

    logger.info(f"\n{'='*60}")
    logger.info(f"CARGA FINALIZADA")
    logger.info(f"Total de registros inseridos: {total_inserted}")
    logger.info(f"{'='*60}")

    print(f"\n✓ Carga finalizada: {total_inserted} registros inseridos")


def merge_qtd_valor():
    """
    Consolida registros de quantidade e valor que foram inseridos separadamente.
    Atualiza registros com valor_aprovado=0 usando os dados do par correspondente.
    """
    conn = sqlite3.connect(DATABASE_PATH)

    # Atualizar quantidade_aprovada onde só tem valor
    conn.execute("""
        UPDATE producao_ambulatorial AS target
        SET quantidade_aprovada = (
            SELECT src.quantidade_aprovada
            FROM producao_ambulatorial src
            WHERE src.municipio = target.municipio
              AND src.subgrupo_procedimento = target.subgrupo_procedimento
              AND src.periodo = target.periodo
              AND src.quantidade_aprovada > 0
            LIMIT 1
        )
        WHERE target.quantidade_aprovada = 0
          AND EXISTS (
            SELECT 1 FROM producao_ambulatorial src
            WHERE src.municipio = target.municipio
              AND src.subgrupo_procedimento = target.subgrupo_procedimento
              AND src.periodo = target.periodo
              AND src.quantidade_aprovada > 0
        )
    """)

    # Atualizar valor_aprovado onde só tem quantidade
    conn.execute("""
        UPDATE producao_ambulatorial AS target
        SET valor_aprovado = (
            SELECT src.valor_aprovado
            FROM producao_ambulatorial src
            WHERE src.municipio = target.municipio
              AND src.subgrupo_procedimento = target.subgrupo_procedimento
              AND src.periodo = target.periodo
              AND src.valor_aprovado > 0
            LIMIT 1
        )
        WHERE target.valor_aprovado = 0
          AND EXISTS (
            SELECT 1 FROM producao_ambulatorial src
            WHERE src.municipio = target.municipio
              AND src.subgrupo_procedimento = target.subgrupo_procedimento
              AND src.periodo = target.periodo
              AND src.valor_aprovado > 0
        )
    """)

    # Remover duplicatas (manter apenas o registro mais completo)
    conn.execute("""
        DELETE FROM producao_ambulatorial
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM producao_ambulatorial
            GROUP BY municipio, subgrupo_procedimento, periodo
        )
    """)

    conn.commit()

    # Contar registros restantes
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM producao_ambulatorial")
    count = cursor.fetchone()[0]

    conn.close()
    logger.info(f"Consolidação finalizada. Registros: {count}")
    print(f"✓ Consolidação finalizada. Registros no banco: {count}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    if len(sys.argv) > 1 and sys.argv[1] == "--merge":
        merge_qtd_valor()
    else:
        load_all_csvs()
        print("\nExecute com --merge para consolidar quantidade e valor")
