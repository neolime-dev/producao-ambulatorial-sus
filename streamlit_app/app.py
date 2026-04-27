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
# CSS CUSTOMIZADO - PREMIUM DESIGN
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700&display=swap');

    :root {
        --primary: #1E40AF;
        --secondary: #3B82F6;
        --accent: #10B981;
        --background: #F8FAFC;
        --card-bg: rgba(255, 255, 255, 0.8);
    }

    .stApp {
        background-color: var(--background);
        font-family: 'Inter', sans-serif;
    }

    /* Glassmorphism Headers */
    .main-header {
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #1E40AF 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        padding: 1.5rem 0 0.5rem 0;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        font-size: 1.2rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2.5rem;
        font-weight: 400;
    }

    /* Premium KPI Cards */
    .kpi-container {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 2rem;
    }

    .kpi-card {
        background: var(--card-bg);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
        transition: transform 0.3s ease;
        flex: 1;
    }

    .kpi-card:hover {
        transform: translateY(-5px);
    }

    /* Metric refinement */
    div[data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 1rem !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #E2E8F0;
    }

    div[data-testid="stMetric"] label {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem !important;
        color: #64748B !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #1E3A8A !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    
    .sidebar-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 1rem;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        gap: 12px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #E2E8F0;
        border-radius: 8px;
        padding: 8px 16px;
        color: #64748B;
        border: none;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #1E40AF;
        color: white;
    }

    /* Alert and Toast */
    .stAlert {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# FUNÇÕES DE BANCO DE DADOS
# ============================================================
@st.cache_resource
def get_connection():
    """Retorna conexão com o banco de dados (Suporta Fallback Lite)."""
    lite_path = os.path.join(os.path.dirname(DATABASE_PATH), "lite_producao_ambulatorial.db")
    if os.path.exists(DATABASE_PATH):
        return sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    if os.path.exists(lite_path):
        return sqlite3.connect(lite_path, check_same_thread=False)
    st.error(f"Banco de dados não encontrado")
    st.stop()


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
# SIDEBAR - FILTROS E GUIA
# ============================================================
with st.sidebar:
    st.markdown('<div class="sidebar-title">🏥 Gestão SIA/SUS</div>', unsafe_allow_html=True)
    
    # Modo Apresentação Toggle
    presentation_mode = st.toggle("🎥 Modo Apresentação", value=False, help="Otimiza a interface para exibição em sala de aula")
    
    st.markdown("---")
    st.markdown("### 🔍 Filtros Analíticos")

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
        help="Filtrar por grandes regiões do Brasil"
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
        "📍 Unidade Federativa",
        options=uf_options,
        default=[],
        help="Selecione estados específicos"
    )

    # Filtro de Período
    selected_periodos = st.multiselect(
        "📅 Período",
        options=periodos,
        default=[],
        help="Selecione o intervalo temporal"
    )

    # Filtro de Subgrupo
    selected_subgrupos = st.multiselect(
        "🔬 Subgrupo SIGTAP",
        options=subgrupos,
        default=[],
        help="Filtrar por categorias de procedimentos"
    )

    st.markdown("---")
    if presentation_mode:
        st.info("💡 **Dica de Apresentação:** Use os filtros acima para mostrar disparidades regionais entre o Sudeste e o Norte.")
    
    st.markdown("### ℹ️ Dados do Sistema")
    st.caption("""
    **Fonte:** DATASUS/TabNet (SIA/SUS)
    **Dataset:** 14.5M+ registros
    **Período:** 2024 - 2026
    """)
    
    # Nota discreta de modo Lite
    if not os.path.exists(DATABASE_PATH):
        st.caption("*(Modo de amostragem estatística ativo)*")
    
    if st.button("🔄 Limpar Filtros", use_container_width=True):
        st.rerun()


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
if presentation_mode:
    st.balloons()
    st.markdown('<div class="main-header">🏥 Produção Ambulatorial do SUS</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Análise Estratégica de Dados Governamentais • IESB 2026</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="main-header">DATASUS Intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Monitoramento de Produção Ambulatorial (SIA/SUS) • Jan/2024 a Jan/2026</div>', unsafe_allow_html=True)

where_clause, params = build_where_clause()

# KPIs
try:
    # Tentar carregar estatísticas originais (Plano B)
    conn = get_connection()
    kpi_df = pd.DataFrame()
    try:
        kpi_df = pd.read_sql_query("SELECT * FROM original_stats", conn)
        is_lite = True
    except:
        # Se não existir a tabela, calcula do banco atual (Plano A)
        kpi_query = f"""
            SELECT 
                COUNT(*) as total_registros,
                SUM(quantidade_aprovada) as total_qtd,
                SUM(valor_aprovado) as total_valor,
                COUNT(DISTINCT municipio) as total_municipios,
                COUNT(DISTINCT uf) as total_ufs,
                COUNT(DISTINCT periodo) as total_periodos,
                COUNT(DISTINCT subgrupo_procedimento) as total_subgrupos
            FROM producao_ambulatorial
            WHERE {where_clause}
        """
        kpi_df = load_data(kpi_query, params)
        is_lite = False

    if not kpi_df.empty:
        row = kpi_df.iloc[0]

        st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "📊 Registros",
                format_number(row["total_registros"]),
                help="Quantidade total de linhas processadas no banco"
            )
        with col2:
            st.metric(
                "✅ Qtd. Aprovada",
                format_number(row["total_qtd"] or 0),
                help="Volume total de procedimentos realizados"
            )
        with col3:
            st.metric(
                "💰 Valor Total",
                format_currency(row["total_valor"] or 0),
                help="Investimento total aprovado (SIA/SUS)"
            )
        with col4:
            st.metric(
                "🏙️ Municípios",
                format_number(row["total_municipios"]),
                help="Capilaridade do sistema nos municípios"
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        col5, col6, col7 = st.columns(3)
        with col5:
            st.metric("📍 Estados (UFs)", int(row["total_ufs"]))
        with col6:
            st.metric("🔬 Subgrupos", int(row["total_subgrupos"]))
        with col7:
            st.metric("📅 Meses Analisados", int(row["total_periodos"]))

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
