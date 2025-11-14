import srscloud_integration as srsi
from datetime import datetime, timedelta, date
import json

token = ''
maquina = ''
workflow = 'relatorios'
tarefa = 'atividade'


srs = srsi.SRS(token=token,maquina=maquina,workflow=workflow,tarefa=tarefa,logFile='debug')

inicio = srs.execucaoIniciar() 
configuracao = inicio.get('Configuracao', {})
formatoExcel = configuracao['FormatoExcel']
enviarEmail = configuracao['EnviarEmail']
usuarioEnvioEmail = configuracao['UsuarioEnvioEmail']
enviarAnexo = configuracao['EnviarAnexo']

if not srs.filaId: 
    #execução agendada
    #define o rage de datas para o mes anterior completo para criar uma fila
    hoje = date.today()
    dataFim = hoje.replace(day=1)
    dataFim = dataFim - timedelta(days=1)
    dataIni = dataFim.replace(day=1)
    workflow = ''
    ref = f"rATV_mensal_{dataIni.year}-{dataIni.month}"
    par = {'DataInicio': dataIni.strftime('%Y-%m-%d %H:%M:%S'),
        'DataFim': dataFim.strftime('%Y-%m-%d %H:%M:%S')}
    srs.filaInserir(referencia=ref, parametrosEntrada=par, inserirExecutando=True)
else: 
    #execução manual
    fila = srs.filaProximo()
    ref = fila['Fila'][0]['Referencia']
    dataIni = fila['Fila'][0]['ParametrosEntrada']['DataInicio']
    dataFim = fila['Fila'][0]['ParametrosEntrada']['DataFim']
    workflow = fila['Fila'][0]['ParametrosEntrada'].get('AliasWorkflow', '')
    dataIni = datetime.strptime(dataIni, '%Y-%m-%d %H:%M:%S')
    dataFim = datetime.strptime(dataFim, '%Y-%m-%d %H:%M:%S')

#inicialização dos parametros: 
pagina = 0
limite = 1000 #limite máximo permitido pela API
colunas = []
tamanhoColunas = []
for coluna in formatoExcel:
    colunas.append(coluna['Coluna'])
    tamanhoColunas.append(coluna['Tamanho'])

r = 0 
# funciona para: 
#    relatorio_atividade
#    relatorio_auditoria
#    relatorio_maquina
#    relatorio_sistema
#    relatorio_execucao
#    relatorio_andamento
#    relatorio_agente_ia
#    relatorio_botstore
resultado = srs.relatorio(relatorio='relatorio_atividade', 
                          dataInicio=dataIni, dataFim=dataFim, workflowAlias=workflow, pagina=pagina, limite=limite)
relatorio = resultado['Dados']
r = len(relatorio)
while len(relatorio) == limite: #enquanto retornar o limite, tem mais paginas
    pagina +=1
    resultado = srs.relatorio(relatorio='relatorio_atividade', dataInicio=dataIni, dataFim=dataFim, workflowAlias=workflow, pagina=pagina, limite=limite)
    relatorio += resultado['Dados']


nome_arquivo = f'c:/Automate Brasil/relatorios/{ref}.json'

with open(nome_arquivo, 'w', encoding='utf-8') as f:
    json.dump(relatorio, f, ensure_ascii=False, indent=4)

# Atualiza a fila com o resultado
mensagem = f"Relatorio de Atividades gerado com sucesso: {r} registradas"
srs.filaAtualizar(parametrosSaida={'Retorno': mensagem, 'ArquivoLocal': nome_arquivo}, mensagem=mensagem)

# Envia email de notificação
assunto = f'Seu relatorio de atividades {ref} já esta disponível.'
mensagem2 = f"Seu relatório de atividades do SRS do período de {dataIni} até {dataFim}, com {r} linhas já está disponivel."
srs.enviarNotificacao(canal=['Email', 'Portal'], assunto=assunto, 
                    mensagem=mensagem2, destino=[{'Token':srs.token}])

srs.execucaoFinalizar()
