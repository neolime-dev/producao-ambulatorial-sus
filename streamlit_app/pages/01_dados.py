"""
Página: Lista dos Dados Armazenados
Exibe tabela interativa com os dados do banco, com filtros e paginação.
"""

import os
import sys
import sqlite3
import streamlit as st
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.config import DATABASE_PATH

st.set_page_config(page_title="Dados - SIA/SUS", page_icon="📋", layout="wide")

st.markdown("# 📋 Lista dos Dados Armazenados")
st.markdown("Visualize todos os registros de produção ambulatorial com filtros interativos.")
st.markdown("---")


@st.cache_resource
def get_conn():
    if not os.path.exists(DATABASE_PATH):
        st.error("Banco de dados não encontrado. Execute o scraper primeiro.")
        st.stop()
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


conn = get_conn()

# Filtros
col1, col2, col3, col4 = st.columns(4)

with col1:
    regioes = pd.read_sql_query(
        "SELECT DISTINCT regiao FROM producao_ambulatorial WHERE regiao != '' ORDER BY regiao", conn
    )["regiao"].tolist()
    sel_regiao = st.selectbox("🌎 Região", ["Todas"] + regioes)

with col2:
    if sel_regiao != "Todas":
        ufs = pd.read_sql_query(
            "SELECT DISTINCT uf FROM producao_ambulatorial WHERE regiao = ? ORDER BY uf",
            conn, params=(sel_regiao,)
        )["uf"].tolist()
    else:
        ufs = pd.read_sql_query(
            "SELECT DISTINCT uf FROM producao_ambulatorial WHERE uf != '' ORDER BY uf", conn
        )["uf"].tolist()
    sel_uf = st.selectbox("📍 UF", ["Todas"] + ufs)

with col3:
    periodos = pd.read_sql_query(
        "SELECT DISTINCT periodo FROM producao_ambulatorial ORDER BY periodo", conn
    )["periodo"].tolist()
    sel_periodo = st.selectbox("📅 Período", ["Todos"] + periodos)

with col4:
    subgrupos = pd.read_sql_query(
        "SELECT DISTINCT subgrupo_procedimento FROM producao_ambulatorial ORDER BY subgrupo_procedimento", conn
    )["subgrupo_procedimento"].tolist()
    sel_subgrupo = st.selectbox("🔬 Subgrupo", ["Todos"] + subgrupos)

# Busca por município
municipio_search = st.text_input("🔍 Buscar Município", placeholder="Digite o nome do município...")

# Construir query
conditions = []
params = []

if sel_regiao != "Todas":
    conditions.append("regiao = ?")
    params.append(sel_regiao)
if sel_uf != "Todas":
    conditions.append("uf = ?")
    params.append(sel_uf)
if sel_periodo != "Todos":
    conditions.append("periodo = ?")
    params.append(sel_periodo)
if sel_subgrupo != "Todos":
    conditions.append("subgrupo_procedimento = ?")
    params.append(sel_subgrupo)
if municipio_search:
    conditions.append("municipio LIKE ?")
    params.append(f"%{municipio_search}%")

where = " AND ".join(conditions) if conditions else "1=1"

# Contagem total
count_query = f"SELECT COUNT(*) as total FROM producao_ambulatorial WHERE {where}"
total_records = pd.read_sql_query(count_query, conn, params=params).iloc[0]["total"]

st.markdown(f"**Total de registros encontrados:** {total_records:,}")

# Paginação
page_size = st.selectbox("Registros por página", [25, 50, 100, 500], index=1)
total_pages = max(1, (total_records + page_size - 1) // page_size)
page = st.number_input("Página", min_value=1, max_value=total_pages, value=1)

offset = (page - 1) * page_size

# Query paginada
data_query = f"""
    SELECT
        municipio as "Município",
        codigo_municipio as "Código IBGE",
        uf as "UF",
        regiao as "Região",
        subgrupo_procedimento as "Subgrupo de Procedimento",
        periodo as "Período",
        quantidade_aprovada as "Qtd. Aprovada",
        valor_aprovado as "Valor Aprovado (R$)"
    FROM producao_ambulatorial
    WHERE {where}
    ORDER BY municipio, periodo, subgrupo_procedimento
    LIMIT ? OFFSET ?
"""
params_paginated = params + [page_size, offset]

df = pd.read_sql_query(data_query, conn, params=params_paginated)

st.markdown(f"Mostrando página **{page}** de **{total_pages}**")

# Formatação
if not df.empty:
    st.dataframe(
        df.style.format({
            "Qtd. Aprovada": "{:,.0f}",
            "Valor Aprovado (R$)": "R$ {:,.2f}"
        }),
        width="stretch",
        height=600
    )

    # Botão de exportação
    st.markdown("---")
    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        # Exportar página atual
        csv_page = df.to_csv(index=False, sep=";", decimal=",")
        st.download_button(
            "📥 Exportar Página Atual (CSV)",
            csv_page,
            file_name="dados_pagina_atual.csv",
            mime="text/csv"
        )

    with col_exp2:
        # Exportar todos (com filtros)
        if st.button("📥 Preparar Exportação Completa"):
            full_query = f"""
                SELECT * FROM producao_ambulatorial WHERE {where}
                ORDER BY municipio, periodo, subgrupo_procedimento
            """
            full_df = pd.read_sql_query(full_query, conn, params=params)
            csv_full = full_df.to_csv(index=False, sep=";", decimal=",")
            st.download_button(
                "⬇️ Download Completo",
                csv_full,
                file_name="dados_completos.csv",
                mime="text/csv"
            )
else:
    st.info("Nenhum registro encontrado com os filtros selecionados.")
