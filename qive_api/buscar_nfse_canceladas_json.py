import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import json
import time
import logging

data_hoje = datetime.now().strftime("%Y-%m-%d")
nome_log = f"{data_hoje}_testeqiveapi.log"

# configurar o estilo do log
logging.basicConfig(filename=f"./log/{nome_log}", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s", datefmt="%H:%M:%S")

logging.info("\n\n")
logging.info("#"*50)
logging.info(f"Iniciando novo processo - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Credenciais da API Arquivei
headers = {
    "X-API-ID": "b2d09779e1bb295256cd4e9feffaa5aecb2dfc47",
    "X-API-KEY": "5b84010e4e04fd0b4fd773596fdc3be57a42e278"    
}
BASE_URL = "https://api.arquivei.com.br"


def buscar_todas_notas_paginado(cnpj, created_from, created_to, tipo="received", max_paginas=None):
    """
    Busca TODAS as notas com paginação automática por cursor

    Args:
        cnpj: CNPJ para filtrar
        created_from: Data de RECEBIMENTO inicial (formato: YYYY-MM-DD)
        created_to: Data de RECEBIMENTO final (formato: YYYY-MM-DD)
        tipo: "received" ou "emitted"
        max_paginas: Limite de páginas (None = sem limite)

    Returns:
        Lista completa de notas em formato JSON
    """

    cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
    logging.info(f"CNPJ Limpo ({cnpj_limpo})")

    url = f"{BASE_URL}/v1/nfse/{tipo}"
    logging.info(f"URL de Consulta: {url}")

    # Parâmetros iniciais
    params = {
        "cnpj[]": cnpj_limpo,
        "created_at[from]": created_from,  # Data de RECEBIMENTO pelo Arquivei
        "created_at[to]": created_to,
        "cursor": 0,
        "limit": 50,
        "format_type": "json"  # Retorna em JSON simplificado
    }
    logging.info(f"Parâmetros Iniciais: {params}")

 
    todas_notas = []
    cursor_atual = 0
    pagina = 1

    logging.info("="*50)
    logging.info(f"BUSCANDO NOTAS FISCAIS ({tipo.upper()})")
    logging.info("="*50)
    logging.info(f"   CNPJ: {cnpj}")
    logging.info(f"   Data Recebimento Arquivei: {created_from} a {created_to}")
    logging.info(f"   Formato: JSON (simplificado)")
    logging.info(f"   Limite por página: 50 notas")
    logging.info("="*50)

    while True:
        # Verifica limite de páginas
        if max_paginas and pagina > max_paginas:
            logging.info(f"Limite de {max_paginas} páginas atingido")
            break

        logging.info(f" Página {pagina} (cursor: {cursor_atual})...")

        params["cursor"] = cursor_atual

        try:
            response = requests.get(url, params=params, headers=headers, timeout=60)            
            logging.info(f"Requisição URL: {response.url}")            
            response.raise_for_status()
            data = response.json()

            # Verifica se houve erro
            if data.get('status', {}).get('code') != 200:
                logging.info(f"Erro API: {data.get('status', {}).get('message')}")
                break

            notas = data.get('data', [])

            logging.info(f"Total de {len(notas)} notas")

            if not notas:
                logging.info("Nenhuma nota encontrada nesta página")
                break

            # Adiciona as notas à lista
            todas_notas.extend(notas)

            # Verifica se há próxima página
            if len(notas) < 50:
                logging.info(f"Última página atingida ({len(notas)} < 50)")
                break

            # Próximo cursor é sempre: cursor_atual + quantidade retornada
            cursor_atual += len(notas)
            pagina += 1

            # Pequeno delay para não sobrecarregar a API
            time.sleep(0.3)

        except requests.exceptions.Timeout:
            logging.info(f"Timeout na página {pagina}")
            break

        except requests.exceptions.HTTPError as e:
            logging.info(f"Erro HTTP {e.response.status_code}")
            try:
                erro_json = e.response.json()
                logging.info(f"Status Code: {response.status_code}")
                logging.info(f"   Mensagem: {erro_json.get('status', {}).get('message', 'Erro desconhecido')}")
            except:
                logging.info(f"   Resposta: {e.response.text[:200]}")
            break

        except Exception as e:
            logging.info(f"Erro: {e}")
            break

    logging.info("="*50)
    logging.info(f"RESUMO:")
    logging.info(f"   Total de notas: {len(todas_notas)}")
    logging.info(f"   Páginas processadas: {pagina}")
    logging.info("="*50)

    return todas_notas


def extrair_dados_nota_json(nota_json):
    """
    Extrai dados importantes da nota em formato JSON

    Args:
        nota_json: Nota em formato JSON (da API)

    Returns:
        Dict com dados formatados
    """

    try:
        logging.debug(f"Extraindo dados importantes da nota em formato JSON")
        xml_data = nota_json.get('xml', {})
        nfse = xml_data.get('Nfse', {})
        inf_nfse = nfse.get('InfNfse', {})

        # Dados básicos
        dados = {
            'id_arquivei': nota_json.get('id'),
            'numero': inf_nfse.get('Numero'),
            'codigo_verificacao': inf_nfse.get('CodigoVerificacao'),
            'data_emissao': inf_nfse.get('DataEmissao'),
        }

        # Valores
        valores = inf_nfse.get('ValoresNfse', {})
        dados['base_calculo'] = float(valores.get('BaseCalculo', 0))
        dados['aliquota'] = float(valores.get('Aliquota', 0))
        dados['valor_iss'] = float(valores.get('ValorIss', 0))
        dados['valor_servicos'] = float(valores.get(
            'ValorServicos', 0)) if 'ValorServicos' in valores else 0

        # Prestador
        prestador = inf_nfse.get('PrestadorServico', {})
        id_prestador = prestador.get('IdentificacaoPrestador', {})
        cpf_cnpj_prest = id_prestador.get('CpfCnpj', {})

        dados['cnpj_prestador'] = cpf_cnpj_prest.get('Cnpj', 'N/A')
        dados['nome_prestador'] = prestador.get('RazaoSocial', 'N/A')

        # Tomador
        tomador = inf_nfse.get('Tomador', {})
        id_tomador = tomador.get('IdentificacaoTomador', {})
        cpf_cnpj_tom = id_tomador.get('CpfCnpj', {})

        dados['cnpj_tomador'] = cpf_cnpj_tom.get('Cnpj', 'N/A')
        dados['nome_tomador'] = tomador.get('RazaoSocial', 'N/A')

        # Serviço
        declaracao = inf_nfse.get('DeclaracaoPrestacaoServico', {})
        inf_declaracao = declaracao.get('InfDeclaracaoPrestacaoServico', {})
        servico = inf_declaracao.get('Servico', {})

        dados['discriminacao'] = servico.get('Discriminacao', 'N/A')

        # Verifica cancelamento
        cancelamento = nfse.get('NfseCancelamento')
        dados['cancelada'] = cancelamento is not None

        if dados['cancelada']:
            confirmacao = cancelamento.get('Confirmacao', {})
            dados['data_cancelamento'] = confirmacao.get('DataHora', 'N/A')
            dados['status'] = 'CANCELADA'
        else:
            dados['data_cancelamento'] = None
            dados['status'] = 'ATIVA'

        return dados

    except Exception as e:
        logging.info(f"Erro ao extrair dados: {e}")
        return None


def buscar_nota_por_numero(numero_nota, cnpj, created_from, created_to, tipo="received"):
    """
    Busca uma nota específica pelo número

    Args:
        numero_nota: Número da nota fiscal
        cnpj: CNPJ para filtrar
        created_from: Data de recebimento inicial (YYYY-MM-DD)
        created_to: Data de recebimento final (YYYY-MM-DD)
        tipo: "received" ou "emitted"

    Returns:
        Dados da nota ou None
    """

    logging.info(f"BUSCANDO NOTA ESPECÍFICA")
    logging.info(f"   Número: {numero_nota}")
    logging.info(f"   CNPJ: {cnpj}")
    logging.info(f"   Período: {created_from} a {created_to}")

    # Busca todas as notas do período
    todas_notas = buscar_todas_notas_paginado(cnpj, created_from, created_to, tipo)

    if not todas_notas:
        logging.info("Nenhuma nota encontrada no período")
        return None

    logging.info(f"Procurando nota {numero_nota} entre {len(todas_notas)} notas...")

    # Procura a nota específica
    for nota_json in todas_notas:
        dados = extrair_dados_nota_json(nota_json)

        if dados and str(dados.get('numero')) == str(numero_nota):
            logging.info(f"NOTA ENCONTRADA!")
            return dados

    logging.info(f"Nota {numero_nota} não encontrada")
    return None


def exibir_nota(dados):
    """Exibe detalhes formatados da nota"""
    logging.info("Exibe detalhes formatados da nota")
    if not dados:
        return

    logging.info("="*50)
    logging.info(f"Status: {dados['status']}")
    logging.info("="*50)

    logging.info(f"DADOS DA NOTA:")
    logging.info(f"   ID Qive: {dados['id_arquivei']}")
    logging.info(f"   Número: {dados['numero']}")
    logging.info(f"   Código Verificação: {dados['codigo_verificacao']}")
    logging.info(f"   Data Emissão: {dados['data_emissao']}")

    if dados['cancelada']:
        logging.info(f"Data Cancelamento: {dados['data_cancelamento']}")

    logging.info(f"PRESTADOR:")
    logging.info(f"   Nome: {dados['nome_prestador']}")
    logging.info(f"   CNPJ: {dados['cnpj_prestador']}")

    logging.info(f"TOMADOR:")
    logging.info(f"   Nome: {dados['nome_tomador']}")
    logging.info(f"   CNPJ: {dados['cnpj_tomador']}")

    logging.info(f"VALORES:")
    logging.info(f"   Serviços: R$ {dados['valor_servicos']:,.2f}")
    logging.info(f"   Base Cálculo: R$ {dados['base_calculo']:,.2f}")
    logging.info(f"   Alíquota: {dados['aliquota']:.2f}%")
    logging.info(f"   ISS: R$ {dados['valor_iss']:,.2f}")   

    logging.info("="*50)


def buscar_eventos_cancelamento(cnpj=None, id_notas=None, tipo_evento="101101", limit=50):
    """
    Consulta diretamente o endpoint /v1/nfse/events da Qive (antigo Arquivei)
    para buscar eventos de cancelamento de NFS-e.

    Args:
        cnpj: (opcional) CNPJ para filtrar
        id_notas: (opcional) lista de IDs de notas específicas
        tipo_evento: código do tipo de evento (padrão: 101101 = Cancelamento)
        limit: quantidade máxima de registros por requisição

    Returns:
        Lista de eventos de cancelamento encontrados
    """
    logging.info("="*50)
    logging.info("BUSCANDO EVENTOS DE CANCELAMENTO (Qive API)")
    logging.info("="*50)

    url = f"{BASE_URL}/v1/nfse/events"

    params = {
        "type[]": tipo_evento,  # 101101 = cancelamento
        "limit": limit
    }

    if id_notas:
        params["id[]"] = id_notas

    if cnpj:
        cnpj_limpo = cnpj.replace(".", "").replace("/", "").replace("-", "")
        params["cnpj[]"] = cnpj_limpo

    try:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        logging.info(f"Requisição URL: {response.url}")

        response.raise_for_status()
        data = response.json()

        # Valida retorno
        if data.get("status", {}).get("code") != 200:
            logging.info(f"Erro na API: {data.get('status', {}).get('message')}")
            return []

        eventos = data.get("data", [])
        canceladas = []

        logging.info(f"Total de eventos retornados: {len(eventos)}")

        for ev in eventos:
            tipo = ev.get("type")
            if tipo == "101101":  # cancelamento confirmado
                canceladas.append(ev)
                logging.info(f"Nota cancelada encontrada: ID Qive {ev.get('id')}")

        logging.info(f"Total de notas canceladas: {len(canceladas)}")
        return canceladas

    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao consultar eventos: {e}")
        return []



# ============================================================
# EXEMPLOS DE USO
# ============================================================


if __name__ == "__main__":

    # Configurações
    cnpj_empresa = "02.990.234/0001-59"
    data_recebimento_inicio = "2025-11-01"  # Data que o Arquivei recebeu
    data_recebimento_fim = "2025-11-11"    
    numero_nota = "37"  # substitua pelo número real da nota
    
    logging.info("SISTEMA DE CONSULTA DE NFS-E - API ARQUIVEI\n")

    # ============================================================
    # EXEMPLO 1: Buscar nota específica por número
    # ============================================================
    logging.info("="*40)
    logging.info("EXEMPLO 1: Buscar nota específica pelo número")
    
    nota_especifica = buscar_nota_por_numero(
        numero_nota,  # Exemplo da sua resposta JSON
        cnpj=cnpj_empresa,
        created_from=data_recebimento_inicio,
        created_to=data_recebimento_fim,
        tipo="received"
    )


    if nota_especifica:
        exibir_nota(nota_especifica)
        logging.info(f"ID da nota (Qive): {nota_especifica['id_arquivei']}")


    # ============================================================
    # EXEMPLO 2: Buscar nota cancela via endpoint específico
    # ============================================================
    logging.info("="*50)
    logging.info("EXEMPLO 2: Buscar eventos de cancelamento via endpoint específico")
    
    id_nota = nota_especifica['id_arquivei']
    #id_nota = "cacfcbd19ebc7a3a510e763c0fb7539290262d48"  # substitua pelo ID real da nota

    notas_canceladas = buscar_eventos_cancelamento(
        cnpj=cnpj_empresa,
        id_notas=[id_nota],
        limit=50
    )


    if notas_canceladas:
        # A função já retorna a lista em data[]
        cancelada = any(ev.get("type") == "101101" for ev in notas_canceladas)

        if cancelada:
            logging.info(f"Nota {id_nota} está CANCELADA (evento 101101 encontrado).")
        else:
            logging.info(f"Nota {id_nota} NÃO está cancelada (nenhum evento 101101 encontrado).")

    else:
        logging.info("Nenhum evento retornado pela API (nota não cancelada ou não encontrada).")
