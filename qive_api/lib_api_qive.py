import os
import requests
import json
import base64
import logging
import time



class QiveAPI:
    def __init__(self, api_id, api_key, log_dir="./log"):
        self.base_url = "https://api.arquivei.com.br"
        self.headers = {
            "X-API-ID": api_id,
            "X-API-KEY": api_key
        }

        logging.info("QiveAPI inicializada")


    def buscar_nfse_todas_notas_paginado(self, cnpj, created_from, created_to, tipo="received", max_paginas=None):
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

        url = f"{self.base_url}/v1/nfse/{tipo}"
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
                response = requests.get(url, params=params, headers=self.headers, timeout=60)            
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


    def extrair_dados_nota_json(self, nota_json):
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


    def buscar_nfse_nota_por_numero(self, numero_nota, cnpj, created_from, created_to, tipo="received"):
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
        todas_notas = self.buscar_nfse_todas_notas_paginado(cnpj, created_from, created_to, tipo)

        if not todas_notas:
            logging.info("Nenhuma nota encontrada no período")
            return None

        logging.info(f"Procurando nota {numero_nota} entre {len(todas_notas)} notas...")

        # Procura a nota específica
        for nota_json in todas_notas:
            dados = self.extrair_dados_nota_json(nota_json)

            if dados and str(dados.get('numero')) == str(numero_nota):
                logging.info(f"NOTA ENCONTRADA!")
                return dados

        logging.info(f"Nota {numero_nota} não encontrada")
        return None


    def exibir_nota(self, dados):
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


    def buscar_nfse_cancelada(self, cnpj=None, id_notas=None, tipo_evento="101101", limit=50):
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

        url = f"{self.base_url}/v1/nfse/events"

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
            response = requests.get(url, headers=self.headers, params=params, timeout=60)
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


    def buscar_nfe_cancelada(self, cnpj=None, access_key=None, tipo_evento="110111", limit=50):
        """
        Busca eventos de cancelamento (type=110111) de NF-e via API Qive/Arquivei.

        Args:
            cnpj (str|None): CNPJ da empresa (opcional)
            access_key (list|None): Lista de access_key das NF-e a consultar
            tipo_evento (str): Tipo de evento (padrão: "110111" = cancelamento)
            limit (int): Quantidade de registros por página
            cursor (str|None): Cursor de paginação (opcional)

        Returns:
            list|None: Lista de eventos encontrados ou None se falhar
        """
        try:
            logging.info("=" * 80)
            logging.info("🔍 BUSCANDO EVENTOS DE CANCELAMENTO (NF-e)")
            logging.info("=" * 80)

            url = f"{self.base_url}/v2/nfe/events"

            params = {
                "type[]": tipo_evento,
                "limit": limit,
                "access_key": access_key
            }
            
            if cnpj:
                params["cnpj[]"] = cnpj.replace(".", "").replace("/", "").replace("-", "")

            logging.info(f"Requisição URL: {url}")
            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            response.raise_for_status()

            data_json = response.json()

            status = data_json.get("status", {})
            if status.get("code") != 200:
                logging.error(f"Erro na resposta: {status.get('message')}")
                return None

            eventos = data_json.get("data", [])
            if not eventos:
                logging.info("Nenhum evento encontrado para os filtros informados.")
                return []

            logging.info(f"{len(eventos)} evento(s) encontrado(s).")
            return eventos

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")

        return None


    def baixar_nfe_pdf(self, access_key, nome_arquivo=None, pasta="./danfe"):
        """
        Busca o DANFe (PDF) por access_key, decodifica base64 e salva em disco.
        Cria a pasta se não existir.

        Args:
            access_key (str): chave de acesso da NFe (44 dígitos)
            nome_arquivo (str|None): nome do arquivo (ex: "meu_arquivo.pdf"). 
                                    Se None, será usado "DANFE_<access_key>.pdf".
            pasta (str): diretório onde salvar o PDF (ex: "./danfes" ou "C:/meus/arquivos").

        Retorna:
            str|None: caminho completo do arquivo salvo ou None em caso de erro.
        """
        try:
            logging.info(f"Buscando DANFE para chave: {access_key}")
            url = f"{self.base_url}/v1/nfe/danfe"
            params = {"access_key": access_key}
            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            logging.info(f"Requisição URL: {response.url}")
            response.raise_for_status()
            data = response.json()

            status_code = data.get("status", {}).get("code")
            if status_code != 200:
                logging.error(f"Erro API ao baixar DANFE: {data.get('status', {}).get('message')}")
                return None

            pdf_base64 = data.get("data", {}).get("encoded_pdf")
            if not pdf_base64:
                logging.error("Campo 'encoded_pdf' vazio ou inexistente.")
                return None

            # prepara nome e pasta
            if not nome_arquivo:
                nome_arquivo = f"DANFE_{access_key}.pdf"
            
            # garante extensão .pdf
            if not nome_arquivo.lower().endswith(".pdf"):
                nome_arquivo = nome_arquivo + ".pdf"

            # cria pasta se necessário
            os.makedirs(pasta, exist_ok=True)

            caminho_completo = os.path.join(pasta, nome_arquivo)

            # decodifica e salva
            pdf_bytes = base64.b64decode(pdf_base64)
            with open(caminho_completo, "wb") as f:
                f.write(pdf_bytes)

            logging.info(f"DANFE salvo com sucesso: {caminho_completo}")
            return caminho_completo

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
        except Exception as e:
            logging.error(f"Erro ao salvar DANFE: {e}")

        return None


    def baixar_nfe_xml(self, access_key, nome_arquivo=None, pasta="./danfe_xml"):
        """
        Baixa o XML de uma NFe via API Qive (endpoint /v1/nfe/received)
        e salva o conteúdo decodificado do campo Base64 'xml'.

        Args:
            access_key (str): Chave de acesso da NFe (44 dígitos)
            nome_arquivo (str|None): Nome do arquivo XML (opcional)
            pasta (str): Diretório de destino (padrão: ./xml)

        Returns:
            str|None: Caminho completo do arquivo salvo ou None se falhar
        """
        try:
            logging.info("=" * 60)
            logging.info(f"BUSCANDO XML DA NFe - CHAVE: {access_key}")
            logging.info("=" * 60)

            url = f"{self.base_url}/v1/nfe/received"
            params = {
                "access_key[]": access_key,
                "format_type": "xml"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            logging.info(f"Requisição URL: {response.url}")
            response.raise_for_status()

            data_json = response.json()

            status = data_json.get("status", {})
            if status.get("code") != 200:
                logging.error(f"Erro na resposta: {status.get('message')}")
                return None

            notas = data_json.get("data", [])
            if not notas:
                logging.warning("Nenhum resultado encontrado para a chave informada.")
                return None

            item = notas[0]
            xml_base64 = item.get("xml")

            if not xml_base64:
                logging.error("Campo 'xml' não encontrado na resposta.")
                return None

            # Decodifica Base64
            try:
                xml_bytes = base64.b64decode(xml_base64)
                xml_str = xml_bytes.decode("utf-8")
            except Exception as e:
                logging.error(f"Erro ao decodificar XML base64: {e}")
                return None

            # Define nome e pasta
            if not nome_arquivo:
                nome_arquivo = f"NFE_{access_key}.xml"
            if not nome_arquivo.lower().endswith(".xml"):
                nome_arquivo += ".xml"

            os.makedirs(pasta, exist_ok=True)
            caminho_arquivo = os.path.join(pasta, nome_arquivo)

            # Salva o XML
            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(xml_str)

            logging.info(f"XML salvo com sucesso em: {caminho_arquivo}")
            return caminho_arquivo

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
        except json.JSONDecodeError:
            logging.error("Resposta da API não está em formato JSON válido.")
        except Exception as e:
            logging.error(f"Erro ao processar XML: {e}")

        return None


    def baixar_nfse_pdf(self, id_nfse, nome_arquivo=None, pasta="./danfse"):
        """
        Baixa o DANFSe (PDF) de uma NFS-e via API Qive/Arquivei
        e salva o arquivo PDF decodificado a partir de base64.

        Args:
            id_nfse (str): ID da NFS-e
            nome_arquivo (str|None): Nome do arquivo PDF (opcional)
            pasta (str): Diretório onde salvar (padrão: ./pdfs)

        Returns:
            str|None: Caminho do arquivo PDF salvo ou None em caso de erro
        """
        try:
            logging.info(f"Solicitando DANFSe (PDF) - ID: {id_nfse}")

            url = f"{self.base_url}/v1/nfse/danfse"
            params = {"id": id_nfse}

            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            response.raise_for_status()
            data_json = response.json()

            if data_json.get("status", {}).get("code") != 200:
                logging.error(f"Erro: {data_json.get('status', {}).get('message')}")
                return None

            data = data_json.get("data", {})
            encoded_pdf = data.get("encoded_pdf")

            if not encoded_pdf:
                logging.error("Campo 'encoded_pdf' não encontrado na resposta.")
                return None

            # Decodifica o PDF
            pdf_bytes = base64.b64decode(encoded_pdf)

            # Define nome e pasta
            if not nome_arquivo:
                nome_arquivo = f"NFS-e_{id_nfse}.pdf"
            if not nome_arquivo.lower().endswith(".pdf"):
                nome_arquivo += ".pdf"

            os.makedirs(pasta, exist_ok=True)
            caminho_arquivo = os.path.join(pasta, nome_arquivo)

            with open(caminho_arquivo, "wb") as f:
                f.write(pdf_bytes)

            logging.info(f"PDF salvo com sucesso em: {caminho_arquivo}")
            return caminho_arquivo

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
        except Exception as e:
            logging.error(f"Erro ao salvar PDF: {e}")

        return None


    def baixar_nfse_xml(self, id_nfse, nome_arquivo=None, pasta="./danfse_xml"):
        """
        Baixa o XML de uma NFS-e via API Qive/Arquivei e salva o arquivo localmente.

        Args:
            id_nfse (str): ID da NFS-e
            nome_arquivo (str|None): Nome do arquivo XML (opcional)
            pasta (str): Diretório de destino (padrão: ./danfse_xml)

        Returns:
            str|None: Caminho do XML salvo ou None se falhar
        """
        try:
            logging.info(f"Solicitando XML da NFS-e - ID: {id_nfse}")

            url = f"{self.base_url}/v1/nfse/received"
            params = {
                "id[]": id_nfse,
                "format_type": "xml"
            }

            response = requests.get(url, headers=self.headers, params=params, timeout=60)
            response.raise_for_status()
            data_json = response.json()

            if data_json.get("status", {}).get("code") != 200:
                logging.error(f"Erro: {data_json.get('status', {}).get('message')}")
                return None

            data = data_json.get("data", [])
            if not data:
                logging.warning("Nenhum XML encontrado para o ID informado.")
                return None

            xml_base64 = data[0].get("xml")
            if not xml_base64:
                logging.error("Campo 'xml' não encontrado no retorno da API.")
                return None

            # Decodifica o XML
            xml_bytes = base64.b64decode(xml_base64)
            xml_str = xml_bytes.decode("utf-8")

            # Define nome e pasta
            if not nome_arquivo:
                nome_arquivo = f"NFS-e_{id_nfse}.xml"
            if not nome_arquivo.lower().endswith(".xml"):
                nome_arquivo += ".xml"

            os.makedirs(pasta, exist_ok=True)
            caminho_arquivo = os.path.join(pasta, nome_arquivo)

            with open(caminho_arquivo, "w", encoding="utf-8") as f:
                f.write(xml_str)

            logging.info(f"XML salvo com sucesso em: {caminho_arquivo}")
            return caminho_arquivo

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição: {e}")
        except Exception as e:
            logging.error(f"Erro ao salvar XML: {e}")

        return None

