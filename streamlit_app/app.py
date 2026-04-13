#!/usr/bin/env python3
"""
Aplicação Streamlit - Produção Ambulatorial (SIA/SUS)
Dashboard para consulta e visualização dos dados do DATASUS.

Uso:
    streamlit run streamlit_app/app.py
"""

import os
import sys
import sqlite3

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configurar path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.config import DATABASE_PATH

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="DATASUS - Produção Ambulatorial (SIA/SUS)",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
    /* Tema principal */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1B4F72;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #2E86C1;
        margin-bottom: 1.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #5D6D7E;
        text-align: center;
        margin-bottom: 2rem;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1B4F72 0%, #2E86C1 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        margin: 0.5rem 0;
    }
    .kpi-label {
        font-size: 0.85rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
    }
    [data-testid="stSidebar"] h1 {
        color: #1B4F72;
    }

    /* Metric cards refinement */
    [data-testid="stMetric"] {
        background-color: #F0F8FF;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #2E86C1;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÕES DE BANCO DE DADOS
# ============================================================
@st.cache_resource
def get_connection():
    """Retorna conexão com o banco de dados."""
    if not os.path.exists(DATABASE_PATH):
        st.error(f"Banco de dados não encontrado: {DATABASE_PATH}")
        st.info("Execute primeiro o scraper e a carga dos dados.")
        st.stop()
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


@st.cache_data(ttl=300)
def load_data(query: str, params: tuple = None) -> pd.DataFrame:
    """Executa query e retorna DataFrame."""
    conn = get_connection()
    if params:
        return pd.read_sql_query(query, conn, params=params)
    return pd.read_sql_query(query, conn)


@st.cache_data(ttl=300)
def get_filter_options():
    """Carrega opções de filtros."""
    conn = get_connection()
    regioes = pd.read_sql_query(
        "SELECT DISTINCT regiao FROM producao_ambulatorial WHERE regiao != '' ORDER BY regiao",
        conn
    )["regiao"].tolist()

    ufs = pd.read_sql_query(
        "SELECT DISTINCT uf FROM producao_ambulatorial WHERE uf != '' ORDER BY uf",
        conn
    )["uf"].tolist()

    periodos = pd.read_sql_query(
        "SELECT DISTINCT periodo FROM producao_ambulatorial ORDER BY periodo",
        conn
    )["periodo"].tolist()

    subgrupos = pd.read_sql_query(
        "SELECT DISTINCT subgrupo_procedimento FROM producao_ambulatorial ORDER BY subgrupo_procedimento",
        conn
    )["subgrupo_procedimento"].tolist()

    return regioes, ufs, periodos, subgrupos


def format_number(n):
    """Formata número para exibição."""
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    elif n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def format_currency(n):
    """Formata valor monetário."""
    if n >= 1_000_000_000:
        return f"R$ {n/1_000_000_000:.2f}B"
    elif n >= 1_000_000:
        return f"R$ {n/1_000_000:.2f}M"
    elif n >= 1_000:
        return f"R$ {n/1_000:.2f}K"
    return f"R$ {n:.2f}"


# ============================================================
# SIDEBAR - FILTROS
# ============================================================
with st.sidebar:
    st.markdown("# 🏥 Filtros")
    st.markdown("---")

    try:
        regioes, ufs, periodos, subgrupos = get_filter_options()
    except Exception as e:
        st.error(f"Erro ao carregar filtros: {e}")
        st.stop()

    # Filtro de Região
    selected_regioes = st.multiselect(
        "🌎 Região",
        options=regioes,
        default=[],
        help="Selecione as regiões"
    )

    # Filtro de UF
    uf_options = ufs
    if selected_regioes:
        conn = get_connection()
        uf_df = pd.read_sql_query(
            f"SELECT DISTINCT uf FROM producao_ambulatorial WHERE regiao IN ({','.join('?'*len(selected_regioes))}) ORDER BY uf",
            conn, params=tuple(selected_regioes)
        )
        uf_options = uf_df["uf"].tolist()

    selected_ufs = st.multiselect(
        "📍 UF",
        options=uf_options,
        default=[],
        help="Selecione os estados"
    )

    # Filtro de Período
    selected_periodos = st.multiselect(
        "📅 Período",
        options=periodos,
        default=[],
        help="Selecione os períodos"
    )

    # Filtro de Subgrupo
    selected_subgrupos = st.multiselect(
        "🔬 Subgrupo de Procedimento",
        options=subgrupos,
        default=[],
        help="Selecione os subgrupos"
    )

    st.markdown("---")
    st.markdown("### ℹ️ Informações")
    st.markdown("""
    **Fonte:** DATASUS/TabNet
    **Sistema:** SIA/SUS
    **Período:** Jan/2024 - Jan/2026
    """)


# ============================================================
# CONSTRUIR QUERY COM FILTROS
# ============================================================
def build_where_clause():
    """Constrói cláusula WHERE baseada nos filtros."""
    conditions = []
    params = []

    if selected_regioes:
        placeholders = ",".join(["?" for _ in selected_regioes])
        conditions.append(f"regiao IN ({placeholders})")
        params.extend(selected_regioes)

    if selected_ufs:
        placeholders = ",".join(["?" for _ in selected_ufs])
        conditions.append(f"uf IN ({placeholders})")
        params.extend(selected_ufs)

    if selected_periodos:
        placeholders = ",".join(["?" for _ in selected_periodos])
        conditions.append(f"periodo IN ({placeholders})")
        params.extend(selected_periodos)

    if selected_subgrupos:
        placeholders = ",".join(["?" for _ in selected_subgrupos])
        conditions.append(f"subgrupo_procedimento IN ({placeholders})")
        params.extend(selected_subgrupos)

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, tuple(params)


# ============================================================
# PÁGINA PRINCIPAL - DASHBOARD
# ============================================================
st.markdown('<div class="main-header">🏥 Produção Ambulatorial (SIA/SUS)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Sistema de Informações Ambulatoriais do SUS • DATASUS • Jan/2024 a Jan/2026</div>', unsafe_allow_html=True)

where_clause, params = build_where_clause()

# KPIs
try:
    kpi_query = f"""
        SELECT
            COUNT(*) as total_registros,
            SUM(quantidade_aprovada) as total_qtd,
            SUM(valor_aprovado) as total_valor,
            COUNT(DISTINCT municipio) as total_municipios,
            COUNT(DISTINCT uf) as total_ufs,
            COUNT(DISTINCT subgrupo_procedimento) as total_subgrupos,
            COUNT(DISTINCT periodo) as total_periodos
        FROM producao_ambulatorial
        WHERE {where_clause}
    """
    kpi_df = load_data(kpi_query, params)

    if not kpi_df.empty:
        row = kpi_df.iloc[0]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "📊 Total de Registros",
                format_number(row["total_registros"]),
                help="Quantidade total de registros no banco"
            )
        with col2:
            st.metric(
                "✅ Qtd. Aprovada Total",
                format_number(row["total_qtd"] or 0),
                help="Soma total de procedimentos aprovados"
            )
        with col3:
            st.metric(
                "💰 Valor Aprovado Total",
                format_currency(row["total_valor"] or 0),
                help="Soma total do valor aprovado"
            )
        with col4:
            st.metric(
                "🏙️ Municípios",
                format_number(row["total_municipios"]),
                help="Quantidade de municípios nos dados"
            )

        st.markdown("---")

        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("📍 UFs", int(row["total_ufs"]))
        with col6:
            st.metric("🔬 Subgrupos", int(row["total_subgrupos"]))
        with col7:
            st.metric("📅 Períodos", int(row["total_periodos"]))

except Exception as e:
    st.error(f"Erro ao carregar KPIs: {e}")

st.markdown("---")

# ============================================================
# GRÁFICOS RÁPIDOS NO DASHBOARD
# ============================================================
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.markdown("### 📈 Evolução Temporal - Qtd. Aprovada")
    try:
        temporal_query = f"""
            SELECT periodo,
                   SUM(quantidade_aprovada) as total_qtd
            FROM producao_ambulatorial
            WHERE {where_clause}
            GROUP BY periodo
            ORDER BY periodo
        """
        temp_df = load_data(temporal_query, params)
        if not temp_df.empty:
            fig = px.line(
                temp_df, x="periodo", y="total_qtd",
                markers=True,
                color_discrete_sequence=["#2E86C1"]
            )
            fig.update_layout(
                xaxis_title="Período",
                yaxis_title="Quantidade Aprovada",
                template="plotly_white",
                height=350
            )
            st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.warning(f"Erro no gráfico temporal: {e}")

with col_chart2:
    st.markdown("### 🥧 Distribuição por Região")
    try:
        regiao_query = f"""
            SELECT regiao,
                   SUM(quantidade_aprovada) as total_qtd
            FROM producao_ambulatorial
            WHERE {where_clause} AND regiao != ''
            GROUP BY regiao
            ORDER BY total_qtd DESC
        """
        reg_df = load_data(regiao_query, params)
        if not reg_df.empty:
            colors = ["#1B4F72", "#2E86C1", "#3498DB", "#85C1E9", "#AED6F1"]
            fig = px.pie(
                reg_df, values="total_qtd", names="regiao",
                color_discrete_sequence=colors,
                hole=0.4
            )
            fig.update_layout(
                template="plotly_white",
                height=350
            )
            st.plotly_chart(fig, width="stretch")
    except Exception as e:
        st.warning(f"Erro no gráfico de região: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #95A5A6; font-size: 0.85rem;">
    Projeto: Integração de Técnicas e Projeto de Sistemas Inteligentes | IESB<br>
    Aluno: Matheus Lima Ribeiro | Prof. Sérgio da Costa Côrtes<br>
    Fonte: DATASUS/TabNet - Sistema de Informações Ambulatoriais do SUS (SIA/SUS)
</div>
""", unsafe_allow_html=True)
