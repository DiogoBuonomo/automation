import requests

# Configurações
cnpj_limpo = "03081788000104"
created_from = "2025-10-01"  # Data que o Arquivei recebeu
created_to = "2025-10-04"
numero_nota = "3482343"

#url = "https://api.arquivei.com.br/v1/nfse/events"
url = "https://api.arquivei.com.br/v1/nfse/received"

headers = {
    "X-API-ID": "b2d09779e1bb295256cd4e9feffaa5aecb2dfc47",
    "X-API-KEY": "5b84010e4e04fd0b4fd773596fdc3be57a42e278"
    
}

params = {
        "cnpj[]": cnpj_limpo,
        "created_at[from]": created_from,  # Data de RECEBIMENTO pelo Arquivei
        "created_at[to]": created_to,
        "cursor": 0,
        "limit": 1,
        "format_type": "json"  # Retorna em JSON simplificado
}

response = requests.get(url, headers=headers, params=params)

print(response.text)

data = response.json()
print(data)