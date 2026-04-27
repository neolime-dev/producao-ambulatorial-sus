"""
Página: Estatísticas Descritivas
Apresenta análise estatística completa dos dados de produção ambulatorial.
"""

import os
import sys
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.config import DATABASE_PATH

st.set_page_config(page_title="Estatísticas - SIA/SUS", page_icon="📊", layout="wide")

# ============================================================
# CSS CUSTOMIZADO
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Outfit:wght@500;700&display=swap');
    
    .main-header {
        font-family: 'Outfit', sans-serif;
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .stat-card {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 Inteligência Estatística</div>', unsafe_allow_html=True)
st.markdown("Análise profunda da variabilidade e distribuição dos dados de produção.")
st.markdown("---")


@st.cache_resource
def get_conn():
    lite_path = os.path.join(os.path.dirname(DATABASE_PATH), "lite_producao_ambulatorial.db")
    if os.path.exists(DATABASE_PATH):
        return sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    if os.path.exists(lite_path):
        return sqlite3.connect(lite_path, check_same_thread=False)
    st.error("Banco de dados não encontrado.")
    st.stop()


conn = get_conn()

# Filtro de variável
variable = st.radio(
    "Selecione a variável para análise:",
    ["Quantidade Aprovada", "Valor Aprovado"],
    horizontal=True
)
col_name = "quantidade_aprovada" if variable == "Quantidade Aprovada" else "valor_aprovado"

# ============================================================
# ESTATÍSTICAS GERAIS
# ============================================================
st.markdown("## 📈 Medidas de Tendência Central e Dispersão")

stats_query = f"""
    SELECT
        COUNT(*) as n,
        SUM({col_name}) as soma,
        AVG({col_name}) as media,
        MIN({col_name}) as minimo,
        MAX({col_name}) as maximo
    FROM producao_ambulatorial
    WHERE {col_name} > 0
"""
stats_df = pd.read_sql_query(stats_query, conn)

# Carregar todos os valores para estatísticas avançadas
values_query = f"""
    SELECT {col_name} as valor
    FROM producao_ambulatorial
    WHERE {col_name} > 0
"""
values_df = pd.read_sql_query(values_query, conn)

if not values_df.empty and not stats_df.empty:
    valores = values_df["valor"].dropna()
    row = stats_df.iloc[0]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### Tendência Central")
        media = valores.mean()
        mediana = valores.median()
        try:
            moda = float(stats.mode(valores, keepdims=False).mode)
        except Exception:
            moda = valores.mode().iloc[0] if not valores.mode().empty else 0

        st.metric("Média", f"{media:,.2f}")
        st.metric("Mediana", f"{mediana:,.2f}")
        st.metric("Moda", f"{moda:,.2f}")

    with col2:
        st.markdown("### Dispersão")
        desvio = valores.std()
        variancia = valores.var()
        amplitude = valores.max() - valores.min()
        cv = (desvio / media * 100) if media > 0 else 0

        st.metric("Desvio Padrão", f"{desvio:,.2f}")
        st.metric("Variância", f"{variancia:,.2f}")
        st.metric("Amplitude", f"{amplitude:,.2f}")
        st.metric("Coeficiente de Variação", f"{cv:.1f}%")

    with col3:
        st.markdown("### Quartis")
        q1 = valores.quantile(0.25)
        q2 = valores.quantile(0.50)
        q3 = valores.quantile(0.75)
        iqr = q3 - q1
        p10 = valores.quantile(0.10)
        p90 = valores.quantile(0.90)

        st.metric("Q1 (25%)", f"{q1:,.2f}")
        st.metric("Q2 (50%)", f"{q2:,.2f}")
        st.metric("Q3 (75%)", f"{q3:,.2f}")
        st.metric("IQR (Q3-Q1)", f"{iqr:,.2f}")
        st.metric("P10", f"{p10:,.2f}")
        st.metric("P90", f"{p90:,.2f}")

    st.markdown("---")

    # Tabela resumo
    st.markdown("### 📋 Resumo Estatístico Completo")
    summary = pd.DataFrame({
        "Estatística": [
            "Contagem (N)", "Soma", "Média", "Mediana", "Moda",
            "Desvio Padrão", "Variância", "Mínimo", "Máximo",
            "Amplitude", "Q1 (25%)", "Q2 (50%)", "Q3 (75%)",
            "IQR", "P10", "P90", "Coef. Variação (%)",
            "Assimetria (Skewness)", "Curtose (Kurtosis)"
        ],
        "Valor": [
            f"{len(valores):,}",
            f"{valores.sum():,.2f}",
            f"{media:,.2f}",
            f"{mediana:,.2f}",
            f"{moda:,.2f}",
            f"{desvio:,.2f}",
            f"{variancia:,.2f}",
            f"{valores.min():,.2f}",
            f"{valores.max():,.2f}",
            f"{amplitude:,.2f}",
            f"{q1:,.2f}",
            f"{q2:,.2f}",
            f"{q3:,.2f}",
            f"{iqr:,.2f}",
            f"{p10:,.2f}",
            f"{p90:,.2f}",
            f"{cv:.2f}%",
            f"{valores.skew():.4f}",
            f"{valores.kurtosis():.4f}"
        ]
    })
    st.dataframe(summary, width="stretch", hide_index=True)

    st.markdown("---")

    # ============================================================
    # HISTOGRAMA
    # ============================================================
    st.markdown("### 📊 Distribuição dos Valores")

    # Usar amostra se dataset é muito grande
    sample = valores.sample(min(10000, len(valores)), random_state=42)

    fig = px.histogram(
        sample, x="valor",
        nbins=50,
        color_discrete_sequence=["#2E86C1"],
        labels={"valor": variable, "count": "Frequência"},
        title=f"Histograma - {variable}"
    )
    fig.add_vline(x=media, line_dash="dash", line_color="red",
                  annotation_text=f"Média: {media:,.0f}")
    fig.add_vline(x=mediana, line_dash="dash", line_color="green",
                  annotation_text=f"Mediana: {mediana:,.0f}")
    fig.update_layout(template="plotly_white", height=450)
    st.plotly_chart(fig, width="stretch")

    # ============================================================
    # ESTATÍSTICAS POR REGIÃO
    # ============================================================
    st.markdown("---")
    st.markdown("## 🌎 Estatísticas por Região")

    regiao_stats = pd.read_sql_query(f"""
        SELECT
            regiao as "Região",
            COUNT(*) as "N",
            SUM({col_name}) as "Soma",
            ROUND(AVG({col_name}), 2) as "Média",
            MIN({col_name}) as "Mínimo",
            MAX({col_name}) as "Máximo"
        FROM producao_ambulatorial
        WHERE {col_name} > 0 AND regiao != ''
        GROUP BY regiao
        ORDER BY SUM({col_name}) DESC
    """, conn)

    if not regiao_stats.empty:
        st.dataframe(
            regiao_stats.style.format({
                "N": "{:,.0f}",
                "Soma": "{:,.2f}",
                "Média": "{:,.2f}",
                "Mínimo": "{:,.2f}",
                "Máximo": "{:,.2f}"
            }),
            width="stretch",
            hide_index=True
        )

    # ============================================================
    # ESTATÍSTICAS POR UF
    # ============================================================
    st.markdown("---")
    st.markdown("## 📍 Estatísticas por UF (Top 10)")

    uf_stats = pd.read_sql_query(f"""
        SELECT
            uf as "UF",
            regiao as "Região",
            COUNT(*) as "N",
            SUM({col_name}) as "Soma",
            ROUND(AVG({col_name}), 2) as "Média",
            COUNT(DISTINCT municipio) as "Municípios"
        FROM producao_ambulatorial
        WHERE {col_name} > 0 AND uf != ''
        GROUP BY uf, regiao
        ORDER BY SUM({col_name}) DESC
        LIMIT 10
    """, conn)

    if not uf_stats.empty:
        st.dataframe(uf_stats, width="stretch", hide_index=True)

        fig = px.bar(
            uf_stats, x="UF", y="Soma",
            color="Região",
            title=f"Top 10 UFs - {variable}",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(template="plotly_white", height=400)
        st.plotly_chart(fig, width="stretch")

    # ============================================================
    # ESTATÍSTICAS POR SUBGRUPO
    # ============================================================
    st.markdown("---")
    st.markdown("## 🔬 Estatísticas por Subgrupo de Procedimento (Top 15)")

    subgrupo_stats = pd.read_sql_query(f"""
        SELECT
            subgrupo_procedimento as "Subgrupo",
            COUNT(*) as "N",
            SUM({col_name}) as "Soma",
            ROUND(AVG({col_name}), 2) as "Média"
        FROM producao_ambulatorial
        WHERE {col_name} > 0
        GROUP BY subgrupo_procedimento
        ORDER BY SUM({col_name}) DESC
        LIMIT 15
    """, conn)

    if not subgrupo_stats.empty:
        st.dataframe(subgrupo_stats, width="stretch", hide_index=True)

    # ============================================================
    # ANÁLISE TEMPORAL
    # ============================================================
    st.markdown("---")
    st.markdown("## 📅 Evolução Temporal")

    temporal_stats = pd.read_sql_query(f"""
        SELECT
            periodo,
            SUM({col_name}) as total,
            COUNT(DISTINCT municipio) as municipios,
            ROUND(AVG({col_name}), 2) as media
        FROM producao_ambulatorial
        WHERE {col_name} > 0
        GROUP BY periodo
        ORDER BY periodo
    """, conn)

    if not temporal_stats.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=temporal_stats["periodo"],
            y=temporal_stats["total"],
            mode="lines+markers",
            name="Total",
            line=dict(color="#2E86C1", width=2),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title=f"Evolução Temporal - {variable} (Total)",
            xaxis_title="Período",
            yaxis_title=variable,
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig, width="stretch")

        # Tabela temporal
        st.dataframe(
            temporal_stats.rename(columns={
                "periodo": "Período",
                "total": "Total",
                "municipios": "Municípios Ativos",
                "media": "Média"
            }),
            width="stretch",
            hide_index=True
        )

    # ============================================================
    # ANÁLISE DE OUTLIERS
    # ============================================================
    st.markdown("---")
    st.markdown("## 🔍 Detecção de Valores Extremos (Outliers)")
    
    q1 = valores.quantile(0.25)
    q3 = valores.quantile(0.75)
    iqr = q3 - q1
    limite_superior = q3 + 3.0 * iqr # Outliers extremos
    
    outliers_df = pd.read_sql_query(f"""
        SELECT municipio, uf, regiao, {col_name} as valor
        FROM producao_ambulatorial
        WHERE {col_name} > ?
        ORDER BY {col_name} DESC
        LIMIT 10
    """, conn, params=(limite_superior,))
    
    if not outliers_df.empty:
        st.warning(f"Foram identificados registros com valores extremamente altos (acima de {limite_superior:,.2f}). Estes municípios são prováveis polos regionais de saúde.")
        st.dataframe(outliers_df, width="stretch", hide_index=True)
    else:
        st.success("Não foram detectados outliers extremos na amostra atual.")

else:
    st.warning("Nenhum dado encontrado no banco de dados.")
