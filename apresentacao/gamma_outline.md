# Projeto: Análise da Produção Ambulatorial do SUS (SIA/SUS)
## IESB - Ciência de Dados e Inteligência Artificial

**Autor:** Matheus Lima Ribeiro
**Professor:** Sérgio da Costa Côrtes
**Data:** Abril de 2026

---

# Introdução: O SUS e o SIA/SUS
*   **O SUS:** O maior sistema público de saúde do mundo, garantindo acesso universal a ~190 milhões de brasileiros.
*   **SIA/SUS (Sistema de Informações Ambulatoriais):** Responsável pelo registro de toda a produção ambulatorial: consultas, exames, terapias e cirurgias de pequeno porte.
*   **Portal DATASUS/TabNet:** A fonte oficial de dados, porém com interface de extração complexa e lenta.
*   **Escopo do Projeto:** Cobertura de 25 meses (Janeiro/2024 a Janeiro/2026), abrangendo todos os municípios do Brasil.

---

# Objetivos do Projeto
### Objetivo Geral
Desenvolver um ecossistema integrado para a extração automatizada, armazenamento estruturado e visualização analítica dos dados do SIA/SUS.

### Objetivos Específicos
1.  **Extração de Alta Performance:** Superar a lentidão dos navegadores com um extrator HTTP puro.
2.  **Armazenamento Estruturado:** Banco de dados SQLite otimizado para consultas rápidas.
3.  **Visualização Inteligente:** Dashboard Streamlit com indicadores de BI e estatísticas avançadas.
4.  **Automação do Relatório:** Integração completa em LaTeX (Relatório e Apresentação).

---

# Arquitetura Técnica do Sistema
A arquitetura segue o fluxo de um pipeline moderno de dados:

1.  **Coleta (Web Scraper):** Robô em Python (Requests + Regex) para extração direta via POST.
2.  **Processamento (ETL):** Tratamento de dados brutos com Pandas, limpeza de encodings (Latin-1) e normalização.
3.  **Armazenamento (SQLite):** Base de dados com índices para performance e views de agregação regional.
4.  **Apresentação (Dashboard):** Streamlit + Plotly para análise interativa pelo usuário final.

---

# Engenharia de Extração (Scraper)
Para garantir a eficiência, o sistema realiza **50 extrações automatizadas**:
*   **Indicadores:** Quantidade Aprovada e Valor Aprovado.
*   **Periodicidade:** 25 meses consecutivos processados um a um.
*   **Inovação:** O sistema faz a descoberta de tokens de sessão do DATASUS em tempo real, evitando a necessidade de abrir navegadores pesados (como o Chrome/Selenium) para cada requisição.
*   **Resultado:** Redução de 90% no tempo total de coleta em comparação com métodos tradicionais.

---

# Estrutura do Banco de Dados
Os dados são organizados na tabela `producao_ambulatorial` com os seguintes campos:
*   `municipio` / `codigo_municipio`: Localização exata por IBGE.
*   `uf` / `regiao`: Enriquecimento geográfico para análise regional.
*   `subgrupo_procedimento`: Categoria do atendimento realizado.
*   `periodo`: Escala temporal mensal.
*   `quantidade_aprovada` / `valor_aprovado`: Métricas quantitativas e financeiras.

**Otimização:** Foram criados índices específicos para que o dashboard carregue instantaneamente, mesmo com milhares de registros.

---

# Funcionalidades do Dashboard Streamlit
Uma central de comando para os dados do SUS:
*   **Métricas em Tempo Real (KPIs):** Registros totais, valor aprovado e municípios ativos.
*   **Exploração de Dados:** Tabela interativa com filtros dinâmicos por Região, UF e Município.
*   **Análise Estatística:** Tendência central (Média/Mediana), Dispersão (Desvio Padrão) e Quartis.
*   **Galeria de Gráficos:** 9 tipos de visualizações (Heatmaps de calor, Treemaps de hierarquia, Boxplots por região, etc).

---

# Resultados: Distribuição Regional da Saúde
A análise dos 25 meses revelou:
*   **Liderança do Sudeste:** Maior volume de produção, reflexo da densidade populacional e infraestrutura hospitalar.
*   **Densidade no Nordeste:** Segunda região com maior volume de registros ambulatoriais.
*   **Disparidades:** Identificação clara de como a infraestrutura de saúde está distribuída pelo território nacional.
*   **Sazonalidade:** Flutuações na produção correlacionadas com períodos de férias e feriados nacionais.

---

# Conclusões e Trabalhos Futuros
### Principais Contribuições
*   Criação de uma ferramenta de "Business Intelligence" aberta para dados públicos.
*   Pipeline de dados 100% automatizado e reprodutível.
*   Estrutura escalável para outros sistemas do DATASUS (como o SIH ou SIM).

### Próximos Passos
1.  **Modelos Preditivos:** Usar os dados históricos para prever a demanda futura de procedimentos.
2.  **Análise Espacial:** Integração com mapas (Geopandas) para visualização de vazios assistenciais.
3.  **Deploy:** Publicação do dashboard na nuvem para acesso público.

---

# Referências Principais
*   DATASUS. Departamento de Informática do SUS.
*   MINISTÉRIO DA SAÚDE. Sistema de Informações Ambulatoriais do SUS (SIA/SUS).
*   Selenium & Streamlit Documentation.
*   MITCHELL, R. Web Scraping with Python. O'Reilly Media.
*   PAIM, J. et al. The Brazilian health system: history, advances, and challenges. The Lancet.
