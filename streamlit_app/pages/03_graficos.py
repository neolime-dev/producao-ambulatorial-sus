"""
Página: Gráficos Diversos
Visualizações avançadas dos dados de produção ambulatorial.
"""

import os
import sys
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.config import DATABASE_PATH

st.set_page_config(page_title="Gráficos - SIA/SUS", page_icon="📉", layout="wide")

st.markdown("# 📉 Gráficos Diversos")
st.markdown("Visualizações interativas dos dados de produção ambulatorial do SUS.")
st.markdown("---")


@st.cache_resource
def get_conn():
    if not os.path.exists(DATABASE_PATH):
        st.error("Banco de dados não encontrado.")
        st.stop()
    return sqlite3.connect(DATABASE_PATH, check_same_thread=False)


conn = get_conn()

# Paleta de cores
COLORS = ["#1B4F72", "#2E86C1", "#3498DB", "#85C1E9", "#AED6F1",
          "#F39C12", "#E74C3C", "#27AE60", "#8E44AD", "#1ABC9C"]

# ============================================================
# 1. TOP 20 MUNICÍPIOS POR QUANTIDADE APROVADA
# ============================================================
st.markdown("## 1️⃣ Top 20 Municípios por Quantidade Aprovada")

top_mun_query = """
    SELECT
        municipio,
        uf,
        SUM(quantidade_aprovada) as total_qtd
    FROM producao_ambulatorial
    WHERE quantidade_aprovada > 0
    GROUP BY municipio, uf
    ORDER BY total_qtd DESC
    LIMIT 20
"""
top_mun = pd.read_sql_query(top_mun_query, conn)

if not top_mun.empty:
    top_mun["label"] = top_mun["municipio"] + " (" + top_mun["uf"] + ")"
    fig = px.bar(
        top_mun.sort_values("total_qtd"),
        x="total_qtd", y="label",
        orientation="h",
        color="total_qtd",
        color_continuous_scale="Blues",
        labels={"total_qtd": "Qtd. Aprovada", "label": "Município"},
        title="Top 20 Municípios - Quantidade Aprovada (Acumulado)"
    )
    fig.update_layout(template="plotly_white", height=600, showlegend=False)
    fig.update_coloraxes(showscale=False)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 2. EVOLUÇÃO TEMPORAL (QUANTIDADE E VALOR)
# ============================================================
st.markdown("## 2️⃣ Evolução Temporal - Quantidade e Valor Aprovados")

temporal_query = """
    SELECT
        periodo,
        SUM(quantidade_aprovada) as total_qtd,
        SUM(valor_aprovado) as total_valor
    FROM producao_ambulatorial
    GROUP BY periodo
    ORDER BY periodo
"""
temporal_df = pd.read_sql_query(temporal_query, conn)

if not temporal_df.empty:
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Quantidade Aprovada", "Valor Aprovado (R$)"),
        vertical_spacing=0.12
    )

    fig.add_trace(go.Scatter(
        x=temporal_df["periodo"], y=temporal_df["total_qtd"],
        mode="lines+markers+text",
        name="Quantidade",
        line=dict(color="#2E86C1", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(46,134,193,0.1)"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=temporal_df["periodo"], y=temporal_df["total_valor"],
        mode="lines+markers",
        name="Valor (R$)",
        line=dict(color="#E74C3C", width=3),
        marker=dict(size=8),
        fill="tozeroy",
        fillcolor="rgba(231,76,60,0.1)"
    ), row=2, col=1)

    fig.update_layout(template="plotly_white", height=700, showlegend=True)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 3. DISTRIBUIÇÃO POR REGIÃO (PIE CHART)
# ============================================================
st.markdown("## 3️⃣ Distribuição por Região")

col1, col2 = st.columns(2)

regiao_query = """
    SELECT regiao,
           SUM(quantidade_aprovada) as total_qtd,
           SUM(valor_aprovado) as total_valor
    FROM producao_ambulatorial
    WHERE regiao != ''
    GROUP BY regiao
    ORDER BY total_qtd DESC
"""
regiao_df = pd.read_sql_query(regiao_query, conn)

if not regiao_df.empty:
    with col1:
        fig = px.pie(
            regiao_df, values="total_qtd", names="regiao",
            title="Quantidade Aprovada por Região",
            color_discrete_sequence=COLORS,
            hole=0.35
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(template="plotly_white", height=450)
        st.plotly_chart(fig, width="stretch")

    with col2:
        fig = px.pie(
            regiao_df, values="total_valor", names="regiao",
            title="Valor Aprovado por Região",
            color_discrete_sequence=COLORS,
            hole=0.35
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(template="plotly_white", height=450)
        st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 4. HEATMAP - SUBGRUPOS POR UF
# ============================================================
st.markdown("## 4️⃣ Heatmap - Subgrupos por UF (Top 10 Subgrupos × Top 10 UFs)")

heatmap_query = """
    WITH top_subgrupos AS (
        SELECT subgrupo_procedimento
        FROM producao_ambulatorial
        WHERE quantidade_aprovada > 0
        GROUP BY subgrupo_procedimento
        ORDER BY SUM(quantidade_aprovada) DESC
        LIMIT 10
    ),
    top_ufs AS (
        SELECT uf
        FROM producao_ambulatorial
        WHERE quantidade_aprovada > 0 AND uf != ''
        GROUP BY uf
        ORDER BY SUM(quantidade_aprovada) DESC
        LIMIT 10
    )
    SELECT uf, subgrupo_procedimento,
           SUM(quantidade_aprovada) as total
    FROM producao_ambulatorial
    WHERE subgrupo_procedimento IN (SELECT subgrupo_procedimento FROM top_subgrupos)
      AND uf IN (SELECT uf FROM top_ufs)
    GROUP BY uf, subgrupo_procedimento
"""
heatmap_df = pd.read_sql_query(heatmap_query, conn)

if not heatmap_df.empty:
    pivot = heatmap_df.pivot_table(
        index="uf", columns="subgrupo_procedimento",
        values="total", fill_value=0
    )

    fig = px.imshow(
        pivot,
        labels=dict(x="Subgrupo", y="UF", color="Qtd. Aprovada"),
        color_continuous_scale="Blues",
        aspect="auto",
        title="Quantidade Aprovada: UF × Subgrupo de Procedimento"
    )
    fig.update_layout(template="plotly_white", height=500)
    fig.update_xaxes(tickangle=45)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 5. BOX PLOT - DISTRIBUIÇÃO POR REGIÃO
# ============================================================
st.markdown("## 5️⃣ Box Plot - Distribuição de Valores por Região")

variable_box = st.radio(
    "Variável:", ["Quantidade Aprovada", "Valor Aprovado"],
    horizontal=True, key="boxplot"
)
col_box = "quantidade_aprovada" if variable_box == "Quantidade Aprovada" else "valor_aprovado"

box_query = f"""
    SELECT regiao, {col_box} as valor
    FROM producao_ambulatorial
    WHERE {col_box} > 0 AND regiao != ''
    ORDER BY RANDOM()
    LIMIT 50000
"""
box_df = pd.read_sql_query(box_query, conn)

if not box_df.empty:
    fig = px.box(
        box_df, x="regiao", y="valor",
        color="regiao",
        color_discrete_sequence=COLORS,
        title=f"Distribuição de {variable_box} por Região",
        labels={"regiao": "Região", "valor": variable_box}
    )
    fig.update_layout(template="plotly_white", height=500, showlegend=False)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 6. TREEMAP - HIERARQUIA REGIÃO > UF
# ============================================================
st.markdown("## 6️⃣ Treemap - Hierarquia Região > UF")

treemap_query = """
    SELECT regiao, uf,
           SUM(quantidade_aprovada) as total_qtd
    FROM producao_ambulatorial
    WHERE regiao != '' AND uf != '' AND quantidade_aprovada > 0
    GROUP BY regiao, uf
    ORDER BY total_qtd DESC
"""
treemap_df = pd.read_sql_query(treemap_query, conn)

if not treemap_df.empty:
    fig = px.treemap(
        treemap_df,
        path=["regiao", "uf"],
        values="total_qtd",
        color="total_qtd",
        color_continuous_scale="Blues",
        title="Quantidade Aprovada - Região > UF"
    )
    fig.update_layout(template="plotly_white", height=600)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 7. SCATTER PLOT - QUANTIDADE VS VALOR
# ============================================================
st.markdown("## 7️⃣ Dispersão - Quantidade vs Valor Aprovado (por UF)")

scatter_query = """
    SELECT uf, regiao,
           SUM(quantidade_aprovada) as total_qtd,
           SUM(valor_aprovado) as total_valor
    FROM producao_ambulatorial
    WHERE uf != '' AND quantidade_aprovada > 0 AND valor_aprovado > 0
    GROUP BY uf, regiao
"""
scatter_df = pd.read_sql_query(scatter_query, conn)

if not scatter_df.empty:
    fig = px.scatter(
        scatter_df, x="total_qtd", y="total_valor",
        color="regiao",
        size="total_qtd",
        text="uf",
        color_discrete_sequence=COLORS,
        labels={
            "total_qtd": "Quantidade Aprovada",
            "total_valor": "Valor Aprovado (R$)",
            "regiao": "Região"
        },
        title="Correlação: Quantidade × Valor Aprovado por UF"
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(template="plotly_white", height=550)
    st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ============================================================
# 8. ÁREA EMPILHADA - EVOLUÇÃO POR REGIÃO
# ============================================================
st.markdown("## 8️⃣ Área Empilhada - Evolução por Região")

area_query = """
    SELECT periodo, regiao,
           SUM(quantidade_aprovada) as total_qtd
    FROM producao_ambulatorial
    WHERE regiao != '' AND quantidade_aprovada > 0
    GROUP BY periodo, regiao
    ORDER BY periodo, regiao
"""
area_df = pd.read_sql_query(area_query, conn)

if not area_df.empty:
    fig = px.area(
        area_df, x="periodo", y="total_qtd",
        color="regiao",
        color_discrete_sequence=COLORS,
        title="Evolução da Quantidade Aprovada por Região",
        labels={"total_qtd": "Qtd. Aprovada", "periodo": "Período", "regiao": "Região"}
    )
    fig.update_layout(template="plotly_white", height=500)
    st.plotly_chart(fig, width="stretch")

# ============================================================
# 9. BARRAS AGRUPADAS - TOP 10 SUBGRUPOS
# ============================================================
st.markdown("---")
st.markdown("## 9️⃣ Top 10 Subgrupos de Procedimento")

subgrupo_query = """
    SELECT subgrupo_procedimento,
           SUM(quantidade_aprovada) as total_qtd,
           SUM(valor_aprovado) as total_valor
    FROM producao_ambulatorial
    WHERE quantidade_aprovada > 0
    GROUP BY subgrupo_procedimento
    ORDER BY total_qtd DESC
    LIMIT 10
"""
subgrupo_df = pd.read_sql_query(subgrupo_query, conn)

if not subgrupo_df.empty:
    # Abreviar nomes longos
    subgrupo_df["nome_curto"] = subgrupo_df["subgrupo_procedimento"].str[:40]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Quantidade Aprovada", "Valor Aprovado (R$)")
    )

    fig.add_trace(go.Bar(
        y=subgrupo_df["nome_curto"][::-1],
        x=subgrupo_df["total_qtd"][::-1],
        orientation="h",
        marker_color="#2E86C1",
        name="Quantidade"
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        y=subgrupo_df["nome_curto"][::-1],
        x=subgrupo_df["total_valor"][::-1],
        orientation="h",
        marker_color="#E74C3C",
        name="Valor"
    ), row=1, col=2)

    fig.update_layout(template="plotly_white", height=500, showlegend=False)
    st.plotly_chart(fig, width="stretch")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #95A5A6; font-size: 0.85rem;">
    Fonte: DATASUS/TabNet - SIA/SUS | Projeto IESB - Matheus Lima Ribeiro
</div>
""", unsafe_allow_html=True)
