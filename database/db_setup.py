#!/usr/bin/env python3
"""
Criação do banco de dados SQLite para armazenamento dos dados
de Produção Ambulatorial (SIA/SUS).
"""

import os
import sys
import sqlite3
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.config import DATABASE_PATH

logger = logging.getLogger(__name__)


def create_database():
    """Cria as tabelas no banco de dados SQLite."""

    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Tabela principal de produção ambulatorial
    cursor.execute("""
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

    # Índices para otimizar consultas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_municipio
        ON producao_ambulatorial(municipio)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_uf
        ON producao_ambulatorial(uf)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_regiao
        ON producao_ambulatorial(regiao)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subgrupo
        ON producao_ambulatorial(subgrupo_procedimento)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_periodo
        ON producao_ambulatorial(periodo)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_uf_periodo
        ON producao_ambulatorial(uf, periodo)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_regiao_periodo
        ON producao_ambulatorial(regiao, periodo)
    """)

    # Tabela de metadados de extração
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracao_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo_origem TEXT NOT NULL,
            tipo_conteudo TEXT NOT NULL,
            periodo TEXT NOT NULL,
            registros_inseridos INTEGER DEFAULT 0,
            data_extracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # View agregada por UF
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS vw_producao_por_uf AS
        SELECT
            uf,
            regiao,
            periodo,
            SUM(quantidade_aprovada) as total_quantidade,
            SUM(valor_aprovado) as total_valor,
            COUNT(DISTINCT municipio) as num_municipios,
            COUNT(DISTINCT subgrupo_procedimento) as num_subgrupos
        FROM producao_ambulatorial
        GROUP BY uf, regiao, periodo
    """)

    # View agregada por Região
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS vw_producao_por_regiao AS
        SELECT
            regiao,
            periodo,
            SUM(quantidade_aprovada) as total_quantidade,
            SUM(valor_aprovado) as total_valor,
            COUNT(DISTINCT uf) as num_ufs,
            COUNT(DISTINCT municipio) as num_municipios
        FROM producao_ambulatorial
        GROUP BY regiao, periodo
    """)

    conn.commit()
    conn.close()

    logger.info(f"Banco de dados criado em: {DATABASE_PATH}")
    print(f"✓ Banco de dados criado: {DATABASE_PATH}")


def verify_database():
    """Verifica a estrutura do banco de dados."""
    if not os.path.exists(DATABASE_PATH):
        print("✗ Banco de dados não encontrado")
        return False

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Listar tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\nTabelas: {[t[0] for t in tables]}")

    # Listar views
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views = cursor.fetchall()
    print(f"Views: {[v[0] for v in views]}")

    # Contar registros
    cursor.execute("SELECT COUNT(*) FROM producao_ambulatorial")
    count = cursor.fetchone()[0]
    print(f"Registros em producao_ambulatorial: {count}")

    conn.close()
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_database()
    verify_database()
