#!/usr/bin/env python3
"""
Extrator direto via HTTP POST para o TabNet DATASUS.
Mais rápido que Selenium - usa requests diretamente.
Extrai Produção Ambulatorial (SIA/SUS) por Município x Subgrupo.
"""

import os
import sys
import time
import logging
import requests
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Diretório de saída
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE_DIR, "data", "csv")
os.makedirs(CSV_DIR, exist_ok=True)

# URL do TabNet Brasil (Região, UF e Município)
TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def"

# Períodos: Jan/2024 = 202401, ..., Jan/2026 = 202601
PERIODOS = []
for year in [2024, 2025]:
    for month in range(1, 13):
        PERIODOS.append((year, month))
PERIODOS.append((2026, 1))  # Jan/2026

MESES_LABEL = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]


def period_to_file(year, month):
    """Converte (2024, 1) -> 'qabr2401.dbf'"""
    return f"qabr{year % 100:02d}{month:02d}.dbf"


def period_label(year, month):
    return f"{MESES_LABEL[month-1]}/{year}"


def build_payload(year, month, content):
    """
    Monta o payload POST para o TabNet.
    content: 'Qtd.aprovada' ou 'Valor aprovado'
    """
    arquivo = period_to_file(year, month)
    return {
        # Campos principais - usando VALORES HTML (não texto visível)
        "Linha": "Município",             # valor do option HTML
        "Coluna": "Subgrupo_proced.",    # valor interno do option HTML
        "Incremento": content,            # "Qtd.aprovada" ou "Valor_aprovado"
        "Arquivos": arquivo,              # ex: "qabr2401.dbf"
        # Seleções padrão (todas as categorias)
        "pesqmes1": "Digite o texto e ache o c%F3digo",
        "SMunic%EDpio": "TODAS_AS_CATEGORIAS___",
        "pesqmes2": "Digite o texto e ache o c%F3digo",
        "SSubgrupo_proced.": "TODAS_AS_CATEGORIAS___",
        "pesqmes3": "Digite o texto e ache o c%F3digo",
        "SForma_organiz.": "TODAS_AS_CATEGORIAS___",
        "pesqmes4": "Digite o texto e ache o c%F3digo",
        "SComplexidade": "TODAS_AS_CATEGORIAS___",
        "pesqmes5": "Digite o texto e ache o c%F3digo",
        "SFinanciamento": "TODAS_AS_CATEGORIAS___",
        "pesqmes6": "Digite o texto e ache o c%F3digo",
        "SRubrica_FAEC": "TODAS_AS_CATEGORIAS___",
        "pesqmes7": "Digite o texto e ache o c%F3digo",
        "SRegra_contratual": "TODAS_AS_CATEGORIAS___",
        "pesqmes8": "Digite o texto e ache o c%F3digo",
        "SCarater_Atendiment": "TODAS_AS_CATEGORIAS___",
        "pesqmes9": "Digite o texto e ache o c%F3digo",
        "SGestao": "TODAS_AS_CATEGORIAS___",
        "pesqmes10": "Digite o texto e ache o c%F3digo",
        "SDocumento_registro": "TODAS_AS_CATEGORIAS___",
        "pesqmes11": "Digite o texto e ache o c%F3digo",
        "SEsfera_administrat": "TODAS_AS_CATEGORIAS___",
        "pesqmes12": "Digite o texto e ache o c%F3digo",
        "STipo_de_prestador": "TODAS_AS_CATEGORIAS___",
        "pesqmes13": "Digite o texto e ache o c%F3digo",
        "SNatureza_Juridica": "TODAS_AS_CATEGORIAS___",
        "pesqmes14": "Digite o texto e ache o c%F3digo",
        "SEsfera_Juridica": "TODAS_AS_CATEGORIAS___",
        "pesqmes15": "Digite o texto e ache o c%F3digo",
        "SAprovacao_producao": "TODAS_AS_CATEGORIAS___",
        "pesqmes16": "Digite o texto e ache o c%F3digo",
        "SProfissional_-_CBO": "TODAS_AS_CATEGORIAS___",
        "zeradas": "1",        # checkbox = 1 para exibir linhas zeradas
        "formato": "prn",      # colunas separadas por ;
        "mostre": "Mostra",
    }


def extract_one(year, month, content_key, content_label, session, delay=2):
    """
    Extrai um mês/conteúdo do TabNet via POST.
    Retorna o caminho do CSV salvo ou None em caso de erro.
    """
    label = period_label(year, month)
    logger.info(f"Extraindo: {content_key} - {label}")

    payload = build_payload(year, month, content_label)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    for attempt in range(3):
        try:
            resp = session.post(TABNET_URL, data=payload, headers=headers, timeout=60)
            resp.encoding = "iso-8859-1"

            if resp.status_code != 200:
                logger.warning(f"  Status {resp.status_code}, tentativa {attempt+1}")
                time.sleep(5 * (attempt + 1))
                continue

            text = resp.text

            # Verificar se tem conteúdo útil
            if "Município" not in text and "municipio" not in text.lower():
                logger.warning(f"  Resposta sem dados esperados ({len(text)} chars)")
                # Tentar verificar se é página de erro
                if "erro" in text.lower() or "error" in text.lower():
                    logger.error(f"  Erro retornado pelo servidor")
                time.sleep(5)
                continue

            # Salvar
            month_label = label.replace("/", "-")
            filename = f"sia_{content_key}_{month_label}.csv"
            filepath = os.path.join(CSV_DIR, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(text)

            logger.info(f"  ✓ Salvo: {filename} ({len(text)} chars)")
            time.sleep(delay)
            return filepath

        except requests.exceptions.Timeout:
            logger.warning(f"  Timeout na tentativa {attempt+1}")
            time.sleep(10)
        except Exception as e:
            logger.error(f"  Erro: {e}")
            time.sleep(5)

    logger.error(f"  ✗ Falhou após 3 tentativas: {content_key}/{label}")
    return None


def run_extraction(periodos=None, max_workers=1, delay=3):
    """Executa a extração completa."""
    if periodos is None:
        periodos = PERIODOS

    conteudos = [
        ("quantidade_aprovada", "Qtd.aprovada"),
        ("valor_aprovado", "Valor_aprovado"),   # underscore no valor HTML
    ]

    session = requests.Session()
    # Primeiro acesso para pegar cookies
    try:
        session.get(
            "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def",
            timeout=30
        )
    except Exception as e:
        logger.warning(f"Não foi possível iniciar sessão: {e}")

    total = len(periodos) * len(conteudos)
    done = 0
    files = []
    errors = []

    for content_key, content_label in conteudos:
        for year, month in periodos:
            done += 1
            logger.info(f"--- [{done}/{total}] ---")
            fp = extract_one(year, month, content_key, content_label, session, delay=delay)
            if fp:
                files.append(fp)
            else:
                errors.append(f"{content_key}/{period_label(year,month)}")

    logger.info(f"\n{'='*50}")
    logger.info(f"Extração finalizada: {len(files)}/{total} arquivos")
    if errors:
        logger.warning(f"Falhas: {errors}")
    logger.info(f"{'='*50}")
    return files, errors


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Apenas Jan/2024")
    parser.add_argument("--months", type=int, default=0)
    parser.add_argument("--delay", type=float, default=3.0)
    args = parser.parse_args()

    periodos = PERIODOS
    if args.test:
        periodos = [(2024, 1)]
    elif args.months > 0:
        periodos = PERIODOS[:args.months]

    files, errors = run_extraction(periodos=periodos, delay=args.delay)
    print(f"\nArquivos extraídos: {len(files)}")
    for f in files:
        print(f"  {f}")
    sys.exit(0 if not errors else 1)
