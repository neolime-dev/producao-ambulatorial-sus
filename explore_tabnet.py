import requests
import re
import json

url_form = "http://tabnet.datasus.gov.br/cgi/deftohtm.exe?sia/cnv/qabr.def"
r = requests.get(url_form)
r.encoding = "iso-8859-1"
html = r.text

payload = {}

# Extrair inputs (hidden, text, checkbox, radio)
# Encontrar inputs e capturar name e value
inputs = re.findall(r'<input([^>]+)>', html, re.I)
for attrs in inputs:
    name_m = re.search(r'name="([^"]+)"', attrs, re.I)
    value_m = re.search(r'value="([^"]*)"', attrs, re.I)
    type_m = re.search(r'type="([^"]+)"', attrs, re.I)
    
    if name_m:
        name = name_m.group(1)
        val = value_m.group(1) if value_m else ""
        t = type_m.group(1).lower() if type_m else "text"
        
        if t in ('hidden', '텍', 'text'):
            payload[name] = val
        elif t == 'checkbox' and 'checked' in attrs.lower():
            payload[name] = val
        elif t == 'radio' and 'checked' in attrs.lower():
            payload[name] = val

# Extrair selects
selects = re.split(r'<select', html, flags=re.I)[1:]
for s_block in selects:
    name_m = re.search(r'name="([^"]+)"', s_block[:100], re.I)
    if name_m:
        name = name_m.group(1)
        # Buscar string de option ate o fechamento do select
        end_idx = s_block.lower().find('</select>')
        select_content = s_block[:end_idx] if end_idx != -1 else s_block
        
        # Procurar option selected
        sel_m = re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', select_content, re.I)
        if not sel_m:
            sel_m = re.search(r'<option[^>]*value="([^"]*)"', select_content, re.I)
            
        if sel_m:
            payload[name] = sel_m.group(1)
            
print("Default form state:")
print(json.dumps(payload, indent=2))


print("Default form state:")
print(json.dumps(payload, indent=2))

# Modifica os campos que queremos
payload['Linha'] = "Município"
payload['Coluna'] = "Subgrupo_proced."
payload['Incremento'] = "Qtd.aprovada"
payload['Arquivos'] = "qabr2401.dbf"
payload['formato'] = "prn"
payload['mostre'] = "Mostra"

print("Enviando payload modificado...")
post_url = "http://tabnet.datasus.gov.br/cgi/tabcgi.exe?sia/cnv/qabr.def"
resp = requests.post(post_url, data=payload)
resp.encoding = 'iso-8859-1'

txt = resp.text
print(f"Lenth response: {len(txt)}")
if "EConvertError" in txt:
    print("ERRO no servidor EConvertError")
elif "Tabela de conversao nao encontrada" in txt:
    print("ERRO no servidor: Tabela de conversao nao encontrada")
else:
    print("Sucesso!")
    import re
    m = re.search(r'<pre[^>]*>(.*?)</pre>', txt, re.S|re.I)
    if m:
        pre = re.sub(r'<[^>]+>', '', m.group(1))
        lines = [l for l in pre.split('\n') if ';' in l]
        print(f"Encontrou {len(lines)} registros.")
        if lines:
            print(lines[0])
            print(lines[1] if len(lines) > 1 else "")
