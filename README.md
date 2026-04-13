# Projeto DATASUS - Produção Ambulatorial (SIA/SUS)

**Disciplina:** Integração de Técnicas e Projeto de Sistemas Inteligentes  
**Aluno:** Matheus Lima Ribeiro  
**Professor:** Sérgio da Costa Côrtes  
**Instituição:** Centro Universitário IESB  
**Semestre:** 2026/1

## Descrição

Sistema integrado para extração automatizada, armazenamento e visualização de dados de Produção Ambulatorial do SUS (SIA/SUS) via portal DATASUS/TabNet.

### Especificações dos Dados
- **Sistema:** Produção Ambulatorial (SIA/SUS)
- **Tipo:** Por local de atendimento - a partir de 2008
- **Abrangência:** Brasil por Região, UF e Município
- **Linha:** Município
- **Coluna:** Subgrupo de Procedimento
- **Conteúdo:** Quantidade Aprovada / Valor Aprovado
- **Período:** Janeiro/2024 a Janeiro/2026 (25 meses)

## Estrutura do Projeto

```
IESB/
├── data/csv/              # CSVs extraídos do TabNet
├── database/
│   ├── db_setup.py        # Criação do banco de dados
│   ├── db_loader.py       # Pipeline de carga dos CSVs
│   └── producao_ambulatorial.db
├── scraper/
│   ├── config.py          # Configurações do scraper
│   ├── utils.py           # Funções auxiliares
│   └── tabnet_scraper.py  # Robô de extração (Selenium)
├── streamlit_app/
│   ├── app.py             # Dashboard principal
│   └── pages/
│       ├── 01_dados.py    # Lista dos dados
│       ├── 02_estatisticas.py  # Estatísticas descritivas
│       └── 03_graficos.py # Gráficos diversos
├── relatorio/             # Relatório técnico LaTeX
├── apresentacao/          # Apresentação Beamer
└── requirements.txt
```

## Instalação

```bash
# 1. Instalar dependências Python
pip install -r requirements.txt

# 2. Instalar Chrome/Chromium (necessário para Selenium)
# Arch Linux:
sudo pacman -S chromium
```

## Execução

```bash
# 1. Executar scraper (modo teste - 1 mês)
python -m scraper.tabnet_scraper --test

# 2. Executar scraper (todos os 25 meses)
python -m scraper.tabnet_scraper

# 3. Criar banco de dados
python database/db_setup.py

# 4. Carregar dados no banco
python database/db_loader.py

# 5. Consolidar quantidade e valor
python database/db_loader.py --merge

# 6. Iniciar aplicação Streamlit
streamlit run streamlit_app/app.py
```

## Compilação LaTeX

```bash
# Relatório
cd relatorio && pdflatex relatorio.tex && bibtex relatorio && pdflatex relatorio.tex && pdflatex relatorio.tex

# Apresentação
cd apresentacao && pdflatex apresentacao.tex
```

## Tecnologias

- **Python 3.11+**
- **Selenium** - Automação do navegador
- **Pandas** - Manipulação de dados
- **SQLite** - Banco de dados
- **Streamlit** - Aplicação web
- **Plotly** - Gráficos interativos
- **LaTeX (abntex2/Beamer)** - Documentação
