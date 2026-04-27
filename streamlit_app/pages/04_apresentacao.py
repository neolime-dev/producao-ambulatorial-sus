"""
Página: Guia de Apresentação
Focada em fornecer insights rápidos e uma narrativa para a apresentação em aula.
"""

import os
import sys
import sqlite3
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from scraper.config import DATABASE_PATH

st.set_page_config(page_title="Guia de Apresentação - SIA/SUS", page_icon="🎤", layout="wide")

# CSS para a página de apresentação
st.markdown("""
<style>
    .insight-card {
        background-color: #F0F9FF;
        border-left: 5px solid #0EA5E9;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .insight-title {
        font-weight: 700;
        color: #0369A1;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }
    .narrative-text {
        font-style: italic;
        color: #475569;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("# 🎤 Guia de Apresentação")
st.markdown("Este guia foi criado para auxiliar na narrativa durante a apresentação em sala de aula.")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎯 Pontos Chave para Abordar")
    
    with st.expander("1. O Desafio Técnico (Web Scraping)", expanded=True):
        st.markdown("""
        <div class="insight-card">
            <div class="insight-title">Superando a Tecnologia Legada</div>
            <p>O TabNet do DATASUS utiliza uma tecnologia dos anos 90. O maior desafio não foi apenas baixar os dados, mas realizar a <b>engenharia reversa</b> do protocolo HTTP POST para evitar o uso de ferramentas lentas como o Selenium.</p>
            <p class="narrative-text">"Conseguimos reduzir o tempo de extração de minutos para segundos ao tratar diretamente com requisições ISO-8859-1."</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("2. Volume e Escala", expanded=True):
        st.markdown("""
        <div class="insight-card">
            <div class="insight-title">Big Data na Saúde Pública</div>
            <p>Estamos lidando com mais de <b>14.5 milhões de registros</b>. Isso exige uma modelagem de banco de dados (SQLite) eficiente com índices otimizados para que o Dashboard seja instantâneo.</p>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("3. Insights de Negócio / Gestão", expanded=True):
        st.markdown("""
        <div class="insight-card">
            <div class="insight-title">Desigualdade Regional</div>
            <p>Os dados mostram claramente a concentração de procedimentos no Sudeste. Isso pode ser usado para discutir <b>políticas de descentralização</b> do SUS.</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    st.markdown("### 📊 Quick Stats (Real-time)")
    
    # Conexão com suporte a Lite
    lite_path = os.path.join(os.path.dirname(DATABASE_PATH), "lite_producao_ambulatorial.db")
    if os.path.exists(DATABASE_PATH):
        conn = sqlite3.connect(DATABASE_PATH)
    else:
        conn = sqlite3.connect(lite_path)
    
    total_val = pd.read_sql_query("SELECT SUM(valor_aprovado) FROM producao_ambulatorial", conn).iloc[0, 0]
    total_qtd = pd.read_sql_query("SELECT SUM(quantidade_aprovada) FROM producao_ambulatorial", conn).iloc[0, 0]
    
    st.metric("Custo Total (24-26)", f"R$ {total_val/1e9:.2f} Bi")
    st.metric("Procedimentos", f"{total_qtd/1e6:.1f} Mi")
    
    st.markdown("---")
    st.markdown("### 🛠️ Tecnologias Utilizadas")
    st.code("""
- Python (Requests, Regex)
- SQLite (Persistência)
- Streamlit (Interface)
- Plotly (Gráficos)
- LaTeX/Beamer (Documentação)
    """)

st.markdown("---")
st.info("💡 **Dica:** Durante a apresentação, alterne para o 'Modo Apresentação' na barra lateral da Home para um efeito visual impactante.")
