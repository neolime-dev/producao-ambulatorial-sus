#!/usr/bin/env python3
"""
Pipeline completo: Extração + Carga no Banco de Dados.
Uso:
  python pipeline.py --test          # Apenas Jan/2024
  python pipeline.py --months 3      # Primeiros 3 meses
  python pipeline.py                 # Todos os 25 meses
"""

import os
import sys
import time
import sqlite3
import logging
import argparse
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper.http_extractor import run_extraction, PERIODOS
from database.tabnet_parser import load_all, ensure_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Pipeline DATASUS - Produção Ambulatorial")
    parser.add_argument("--test", action="store_true", help="Apenas Jan/2024")
    parser.add_argument("--months", type=int, default=0, help="Número de meses")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay entre requisições")
    parser.add_argument("--skip-extract", action="store_true", help="Pular extração, só carregar CSVs existentes")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  PIPELINE DATASUS - Produção Ambulatorial (SIA/SUS)")
    print("="*60)

    # STEP 1: Extração
    if not args.skip_extract:
        periodos = PERIODOS
        if args.test:
            periodos = [(2024, 1)]
            print("\n⚡ Modo TESTE: Extraindo apenas Jan/2024")
        elif args.months > 0:
            periodos = PERIODOS[:args.months]
            print(f"\n⚡ Extraindo {args.months} meses")
        else:
            print(f"\n⚡ Extraindo TODOS os {len(PERIODOS)} meses (25 meses × 2 conteúdos = 50 requisições)")

        print(f"   Delay entre requisições: {args.delay}s")
        print()

        files, errors = run_extraction(periodos=periodos, delay=args.delay)
        print(f"\n✓ Extração: {len(files)} arquivos obtidos, {len(errors)} erros")
    else:
        print("\n⏭️  Pulando extração, usando CSVs existentes")

    # STEP 2: Criar banco se necessário
    print("\n📦 Criando/verificando banco de dados...")
    ensure_db()
    print("✓ Banco de dados OK")

    # STEP 3: Carregar dados
    print("\n📥 Carregando dados no banco...")
    n = load_all()
    print(f"✓ {n} registros no banco de dados")

    # STEP 4: Verificação
    from scraper.config import DATABASE_PATH
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM producao_ambulatorial")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT municipio) FROM producao_ambulatorial")
    muns = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT periodo) FROM producao_ambulatorial")
    periodos_db = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT uf) FROM producao_ambulatorial")
    ufs = cur.fetchone()[0]

    cur.execute("SELECT SUM(quantidade_aprovada), SUM(valor_aprovado) FROM producao_ambulatorial")
    row = cur.fetchone()
    total_qtd = row[0] or 0
    total_val = row[1] or 0

    conn.close()

    print("\n" + "="*60)
    print("  RESULTADO FINAL")
    print("="*60)
    print(f"  Total de registros: {total:,}")
    print(f"  Municípios:         {muns:,}")
    print(f"  Períodos:           {periodos_db}")
    print(f"  UFs:                {ufs}")
    print(f"  Qtd. Aprovada:      {total_qtd:,.0f}")
    print(f"  Valor Aprovado:     R$ {total_val:,.2f}")
    print("="*60)

    print("\n🚀 Para iniciar o Streamlit:")
    print("   streamlit run streamlit_app/app.py")


if __name__ == "__main__":
    main()
