import requests
import json
import urllib.parse

TABNET_URL = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def"

payload = {
  "pesqmes2": "Digite o texto e ache facil",
  "pesqmes3": "Digite o texto e ache facil",
  "pesqmes4": "Digite o texto e ache facil",
  "pesqmes5": "Digite o texto e ache facil",
  "pesqmes6": "Digite o texto e ache facil",
  "pesqmes7": "Digite o texto e ache facil",
  "pesqmes8": "Digite o texto e ache facil",
  "pesqmes9": "Digite o texto e ache facil",
  "pesqmes10": "Digite o texto e ache facil",
  "pesqmes16": "Digite o texto e ache facil",
  "pesqmes18": "Digite o texto e ache facil",
  "pesqmes19": "Digite o texto e ache facil",
  "pesqmes22": "Digite o texto e ache facil",
  "pesqmes23": "Digite o texto e ache facil",
  "pesqmes27": "Digite o texto e ache facil",
  "pesqmes29": "Digite o texto e ache facil",
  "pesqmes30": "Digite o texto e ache facil",
  "pesqmes32": "Digite o texto e ache facil",
  "Linha": "Munic\u00edpio",
  "Coluna": "Subgrupo_proced.",
  "Incremento": "Qtd.aprovada",
  "Arquivos": "qabr2401.dbf",
  "SRegi\u00e3o": "TODAS_AS_CATEGORIAS__",
  "SUF": "TODAS_AS_CATEGORIAS__",
  "SMunic\u00edpio": "TODAS_AS_CATEGORIAS__",
  "SCapital": "TODAS_AS_CATEGORIAS__",
  "SRegi\u00e3o_de_Sa\u00fade_(CIR)": "TODAS_AS_CATEGORIAS__",
  "SMacrorregi\u00e3o_de_Sa\u00fade": "TODAS_AS_CATEGORIAS__",
  "SMicrorregi\u00e3o_IBGE": "TODAS_AS_CATEGORIAS__",
  "SRegi\u00e3o_Metropolitana_-_RIDE": "TODAS_AS_CATEGORIAS__",
  "STerrit\u00f3rio_da_Cidadania": "TODAS_AS_CATEGORIAS__",
  "SMesorregi\u00e3o_PNDR": "TODAS_AS_CATEGORIAS__",
  "SAmaz\u00f4nia_Legal": "TODAS_AS_CATEGORIAS__",
  "SSemi\u00e1rido": "TODAS_AS_CATEGORIAS__",
  "SFaixa_de_Fronteira": "TODAS_AS_CATEGORIAS__",
  "SZona_de_Fronteira": "TODAS_AS_CATEGORIAS__",
  "SMunic\u00edpio_de_extrema_pobreza": "TODAS_AS_CATEGORIAS__",
  "SProcedimento": "TODAS_AS_CATEGORIAS__",
  "SGrupo_procedimento": "TODAS_AS_CATEGORIAS__",
  "SSubgrupo_proced.": "TODAS_AS_CATEGORIAS__",
  "SForma_organiza\u00e7\u00e3o": "TODAS_AS_CATEGORIAS__",
  "SComplexidade": "TODAS_AS_CATEGORIAS__",
  "SFinanciamento": "TODAS_AS_CATEGORIAS__",
  "SRubrica_FAEC": "TODAS_AS_CATEGORIAS__",
  "SRegra_contratual": "TODAS_AS_CATEGORIAS__",
  "SCar\u00e1ter_Atendiment": "TODAS_AS_CATEGORIAS__",
  "SGest\u00e3o": "TODAS_AS_CATEGORIAS__",
  "SDocumento_registro": "TODAS_AS_CATEGORIAS__",
  "SEsfera_administrat": "TODAS_AS_CATEGORIAS__",
  "STipo_de_prestador": "TODAS_AS_CATEGORIAS__",
  "SNatureza_Jur\u00eddica": "TODAS_AS_CATEGORIAS__",
  "SEsfera_Jur\u00eddica": "TODAS_AS_CATEGORIAS__",
  "SAprova\u00e7\u00e3o_produ\u00e7\u00e3o": "TODAS_AS_CATEGORIAS__",
  "SProfissional_-_CBO": "TODAS_AS_CATEGORIAS__",
  "zeradas": "1",
  "formato": "prn",
  "mostre": "Mostra"
}

# The payload keys must be properly dynamically url encoded so iso-8859-1 handles special characters
# but requests handles dict automatically if we pass data=payload using correct logic.
# Wait, requests will urlencode using UTF-8 by default if we just pass a dict!!!
# TabNet expects iso-8859-1 !!

encoded_data = urllib.parse.urlencode(payload, encoding='iso-8859-1')

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Referer": "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def",
    "Content-Type": "application/x-www-form-urlencoded",
}

print("Enviando POST com iso-8859-1 urlencode...")
r = requests.post(TABNET_URL, data=encoded_data, headers=headers)
r.encoding = 'iso-8859-1'

print(f"Status: {r.status_code}")
print(f"Tamanho original: {len(r.text)}")

snippet = r.text[:500]
print("Snippet inicial:")
print(snippet)

if ";VEJA A " in r.text or "VEJA A" in r.text:
    print("ERRO: O TABNET LIMITOU OS DADOS.")
    
# Mostrar quantidade de linhas
linhas = [x for x in r.text.split('\n') if ';' in x]
print(f"Número de linhas: {len(linhas)}")
if len(linhas) > 2:
    print("Sucesso aparente!")
    print(linhas[1])
