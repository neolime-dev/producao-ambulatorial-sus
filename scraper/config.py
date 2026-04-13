"""
Configurações do Scraper DATASUS TabNet
Produção Ambulatorial (SIA/SUS) - Por local de atendimento - a partir de 2008
"""

# URL do formulário TabNet - Brasil por Região, UF e Município
TABNET_FORM_URL = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def"

# URL de submissão do formulário
TABNET_ACTION_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def"

# Diretório para salvar CSVs extraídos
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "csv")

# Configurações de timing (segundos)
DELAY_BETWEEN_REQUESTS = 4  # Delay entre requisições para não sobrecarregar o servidor
PAGE_LOAD_TIMEOUT = 60      # Timeout para carregamento de página
ELEMENT_WAIT_TIMEOUT = 30   # Timeout para aguardar elementos

# Períodos a extrair: Jan/2024 a Jan/2026 (25 meses)
# Formato dos arquivos no TabNet: qabrYYMM.dbf
PERIODOS = []
for year in [2024, 2025]:
    for month in range(1, 13):
        PERIODOS.append(f"qabr{year % 100:02d}{month:02d}.dbf")
# Adicionar Jan/2026
PERIODOS.append("qabr2601.dbf")

# Labels dos períodos para referência
PERIODO_LABELS = {}
meses = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
idx = 0
for year in [2024, 2025]:
    for month in range(1, 13):
        key = f"qabr{year % 100:02d}{month:02d}.dbf"
        PERIODO_LABELS[key] = f"{meses[month-1]}/{year}"
        idx += 1
PERIODO_LABELS["qabr2601.dbf"] = "Jan/2026"

# Conteúdos a extrair
CONTEUDOS = {
    "quantidade_aprovada": "Qtd.aprovada",
    "valor_aprovado": "Valor aprovado",
}

# Mapeamento de valores para os selects do formulário
FORM_VALUES = {
    "linha": "Município",           # Select name="Linha"
    "coluna": "Subgrupo proced.",    # Select name="Coluna" - texto exato do TabNet
}

# Database
DATABASE_PATH = os.path.join(BASE_DIR, "database", "producao_ambulatorial.db")
