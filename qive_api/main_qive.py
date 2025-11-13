import os
import logging
from datetime import datetime
from lib_api_qive import QiveAPI


def configurar_logs():    
    log_dir = "./log"
    os.makedirs(log_dir, exist_ok=True)
    nome_log = datetime.now().strftime("%Y-%m-%d_qive.log")
    caminho_log = os.path.join(log_dir, nome_log)

    logging.basicConfig(
        filename=caminho_log,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s",
        datefmt="%H:%M:%S",
        force=True
    )

    # Exibir logs também no console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s - %(lineno)d - %(message)s"))
    logging.getLogger().addHandler(console)

    logging.debug("Log configurado com sucesso.")
    logging.debug(f"Arquivo de log: {os.path.abspath(caminho_log)}")


def main():
    configurar_logs()

    logging.info("\n>>>>>>>>>>>>>  INICIANDO PROCESSO QIVE  <<<<<<<<<<<<<\n")

    qive = QiveAPI(
        api_id="b2d09779e1bb295256cd4e9feffaa5aecb2dfc47",
        api_key="5b84010e4e04fd0b4fd773596fdc3be57a42e278"
    )

    
    while True:
        print("\n" + "=" * 60)
        print("MENU PRINCIPAL - API QIVE/ARQUIVEI")
        print("=" * 60)
        print("1 - Buscar nota específica (NFSe)")
        print("2 - Buscar nota NFSe cancelada")
        print("3 - Buscar PDF (NFe)")
        print("4 - Baixar XML (NFe)")
        print("5 - Baixar PDF (NFSe)")
        print("6 - Baixar XML (NFSe)")
        print("7 - Buscar nota NFe cancelada")
        print("0 - Sair")

        opcao = input("\nEscolha uma opção: ").strip()
        logging.info(f"Opção selecionada: {opcao}\n")

        # Configurações
        cnpj_empresa = "02.990.234/0001-59"                             # CNPJ da empresa
        data_recebimento_inicio = "2025-11-01"                          # Data que o Arquivei recebeu
        data_recebimento_fim = "2025-11-11"                             # Data que o Arquivei recebeu

        if opcao == "0":
            print("Encerrando o sistema...")
            break

        elif opcao == "1":
            # ============================================================
            # EXEMPLO 1: Buscar nota NFS-e específica por número
            # ============================================================
            logging.info("="*40)
            logging.info("EXEMPLO 1: Buscar nota específica pelo número")
            numero_nota = input("Digite o número da nota: ").strip()

            nota_especifica = qive.buscar_nfse_nota_por_numero(
                numero_nota,  # Exemplo da sua resposta JSON
                cnpj=cnpj_empresa,
                created_from=data_recebimento_inicio,
                created_to=data_recebimento_fim,
                tipo="received"
            )

            if nota_especifica:
                qive.exibir_nota(nota_especifica)
                logging.info(f"ID da nota (Qive): {nota_especifica['id_arquivei']}")

        elif opcao == "2":
            # ============================================================
            # EXEMPLO 2: Buscar nota NFS-e cancelada via endpoint específico
            # ============================================================
            logging.info("="*50)
            logging.info("EXEMPLO 2: Buscar eventos de cancelamento via endpoint específico")
            
            id_nota = input("Digite o ID da nota para verificar cancelamento: ").strip()      
            notas_canceladas = qive.buscar_nfse_cancelada(
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

        elif opcao == "3":
            # ======================================================================
            # EXEMPLO 3: Buscar nota NF-e por chave de acesso e baixar DANFE (PDF)
            # ======================================================================
            logging.info("="*50)
            logging.info("EXEMPLO 3: Baixar DANFE (PDF) de NFe pela chave de acesso")

            chave_nfe = "35251111402660000115550010005374891742251316"  # substitua pela chave real da NFe
            pasta = f"./danfe"
            nome_arquivo = f"DANFE_{chave_nfe}.pdf"

            # Chamada da função
            caminho = qive.baixar_nfe_pdf(
                chave_nfe,
                nome_arquivo,
                pasta
            )
            
            # Validação do resultado
            if caminho:
                logging.info(f"DANFE disponível em: {caminho}")
            else:
                logging.info("Não foi possível baixar o DANFE.")

        elif opcao == "4":
            # ======================================================================
            # EXEMPLO 4: Buscar nota NF-e por chave de acesso e baixar DANFE (XML)
            # ======================================================================
            logging.info("="*50)
            logging.info("EXEMPLO 3: Baixar DANFE (XML) de NFe pela chave de acesso")

            chave_nfe = "35250942153323000165550010000226231892892185"  # substitua pela chave real da NFe
            pasta_xml = f"./danfe_xml"
            nome_arquivo_xml = f"DANFE_{chave_nfe}.xml"

            # Chamada da função
            caminho = qive.baixar_nfe_xml(
                chave_nfe,
                nome_arquivo_xml,
                pasta_xml
            )
            
            # Validação do resultado
            if caminho:
                logging.info(f"DANFE disponível em: {caminho}")
            else:
                logging.info("Não foi possível baixar o DANFE.")

        elif opcao == "5":
            # ======================================================================
            # EXEMPLO 5: Buscar nota NFS-e por chave de acesso e baixar DANFE (PDF)
            # ======================================================================
            logging.info("="*50)
            logging.info("EXEMPLO 3: Baixar DANFSE (PDF) pelo ID da NFS-e")

            id_nfse = "e2bcc8786d49c820b0b986b8ada2be304ef90880"  # substitua pelo ID real da NFS-e
            pasta = f"./danfse"
            nome_arquivo = f"DANFSE_{id_nfse}.pdf"

            # Chamada da função
            caminho = qive.baixar_nfse_pdf(
                id_nfse,
                nome_arquivo,
                pasta
            )
            
            # Validação do resultado
            if caminho:
                logging.info(f"DANFSE disponível em: {caminho}")
            else:
                logging.info("Não foi possível baixar o DANFSE.")

        elif opcao == "6":
            # ======================================================================
            # EXEMPLO 6: Buscar nota NFS-e por ID e baixar XML
            # ======================================================================
            logging.info("="*50)
            logging.info("EXEMPLO 6: Baixar XML da NFS-e pelo ID da NFS-e")

            id_nfse = "e2bcc8786d49c820b0b986b8ada2be304ef90880"        
            pasta_xml = f"./danfse_xml"
            nome_arquivo_xml = f"DANFE_{id_nfse}.xml"

            # Chamada da função
            caminho = qive.baixar_nfse_xml(
                id_nfse,
                nome_arquivo_xml,
                pasta_xml
            )
            
            # Validação do resultado
            if caminho:
                logging.info(f"DANFE disponível em: {caminho}")
            else:
                logging.info("Não foi possível baixar o DANFE.")

        elif opcao == "7":
            # ============================================================
            # EXEMPLO 7: Buscar nota NF-e cancelada via endpoint específico
            # ============================================================
            logging.info("="*50)
            logging.info("EXEMPLO 7: Buscar nota NF-e cancelada via endpoint específico")
            
            access_key = input("Digite o access_key da nota para verificar cancelamento: ").strip()      
            notas_canceladas = qive.buscar_nfe_cancelada(
                access_key=[access_key],
                limit=50
            )

            if notas_canceladas:
                # A função já retorna a lista em data[]
                cancelada = any(ev.get("type") == "110111" for ev in notas_canceladas)
                if cancelada:
                    logging.info(f"Nota {access_key} está CANCELADA (evento 101101 encontrado).")
                else:
                    logging.info(f"Nota {access_key} NÃO está cancelada (nenhum evento 101101 encontrado).")

            else:
                logging.info("Nenhum evento retornado pela API (nota não cancelada ou não encontrada).")


if __name__ == "__main__":    
    main()
    logging.shutdown()