import math
from collections import Counter
from typing import List, Tuple, Dict, Any

# ====================================================================
# === CONFIGURAÇÕES GERAIS ===========================================
# ====================================================================

# --- Configurações de Aposta e Risco ---
APOSTA_INICIAL_BASE = 0.50
FATOR_MARTINGALE = 2.0
MAX_PERDAS_CONSECUTIVAS = 4 
# Regra "La Partage": Se True, apostas 1:1 (cor, par/impar) perdem apenas metade no Zero.
LA_PARTAGE_ATIVO = True 

# --- Configurações das Estratégias ---
MIN_SEQUENCIA_COR_ETC = 3      # Sequência para apostas 1:1 (Cor, Par/Ímpar, Alto/Baixo)
MIN_SEQUENCIA_TERCO_COLUNA = 2 # Sequência para Dúzias e Colunas
MIN_ATRASO_NUMERO_FRIO = 37    # Nº de giros sem sair para apostar em um número frio

# --- Configuração da Roleta ---
# 'EUROPEIA' (37 slots: 0-36) ou 'AMERICANA' (38 slots: 0-36, 00)
TIPO_ROLETA = 'EUROPEIA' 

# ====================================================================
# === ESTRUTURAS DE DADOS E ESTADO ===================================
# ====================================================================

# --- Mapeamentos para Exibição ---
NOMENCLATURA = {
    'R': 'VERMELHO', 'B': 'PRETO', 'G': 'VERDE (ZERO)',
    'D1': "1ª DÚZIA (1-12)", 'D2': "2ª DÚZIA (13-24)", 'D3': "3ª DÚZIA (25-36)",
    'C1': "1ª COLUNA", 'C2': "2ª COLUNA", 'C3': "3ª COLUNA",
    'PAR': 'PAR', 'IMPAR': 'ÍMPAR',
    'BAIXO': 'BAIXO (1-18)', 'ALTO': 'ALTO (19-36)',
    'ZERO': 'ZERO',
}
NOMENCLATURA_ACAO = {
    'R': 'vermelho', 'B': 'preto', 'D1': "1ª dúzia", 'D2': "2ª dúzia", 'D3': "3ª dúzia",
    'C1': "1ª coluna", 'C2': "2ª coluna", 'C3': "3ª coluna", 'PAR': 'par', 'IMPAR': 'ímpar',
    'BAIXO': 'baixo (1-18)', 'ALTO': 'alto (19-36)'
}

# --- Variáveis de Estado Globais ---
ESTADOS = {
    'COR':       {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'PAR_IMPAR': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'ALTO_BAIXO':{'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'DUZIA':     {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'TIPO': '2:1'},
    'COLUNA':    {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'TIPO': '2:1'},
    'FRIO':      {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_ATRASO_NUMERO_FRIO, 'GANHO_FATOR': 36, 'TIPO': '35:1'},
}
ESTRATEGIAS_ATIVAS = {key: False for key in ESTADOS}

# --- Gerenciamento de Banca e Histórico ---
BANCA_INICIAL = 0.0
BANCA_ATUAL = 0.0
TODOS_GIROS_HISTORICO = []
NUMEROS_RASTREAMENTO = {str(i): 0 for i in range(37)}
if TIPO_ROLETA == 'AMERICANA':
    NUMEROS_RASTREAMENTO['00'] = 0

# ====================================================================
# === FUNÇÕES DE MAPEAMENTO E ANÁLISE ================================
# ====================================================================

def get_mapeamento_numero(num_str: str) -> Dict[str, str]:
    """Mapeia um número para todas as suas categorias."""
    if num_str == '0':
        return {'COR': 'G', 'DUZIA': 'ZERO', 'COLUNA': 'ZERO', 'PARIDADE': 'ZERO', 'ALTURA': 'ZERO'}
    if num_str == '00':
        return {'COR': 'G', 'DUZIA': 'ZERO', 'COLUNA': 'ZERO', 'PARIDADE': 'ZERO', 'ALTURA': 'ZERO'}

    try:
        n = int(num_str)
        if not (1 <= n <= 36): return {}
    except ValueError:
        return {}

    # Cor
    VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    cor = 'R' if n in VERMELHOS else 'B'
    # Dúzia
    if 1 <= n <= 12: duzia = 'D1'
    elif 13 <= n <= 24: duzia = 'D2'
    else: duzia = 'D3'
    # Coluna
    if n % 3 == 1: coluna = 'C1'
    elif n % 3 == 2: coluna = 'C2'
    else: coluna = 'C3'
    # Paridade
    paridade = 'PAR' if n % 2 == 0 else 'IMPAR'
    # Altura
    altura = 'BAIXO' if 1 <= n <= 18 else 'ALTO'
    
    return {'COR': cor, 'DUZIA': duzia, 'COLUNA': coluna, 'PARIDADE': paridade, 'ALTURA': altura}

def analisar_frequencia_numeros() -> Tuple[List[str], List[str]]:
    """Identifica os 3 números mais frios (cold) e 3 mais quentes (hot), ignorando Zeros."""
    frequencias = [(cont, num) for num, cont in NUMEROS_RASTREAMENTO.items() if num not in ('0', '00')]
    if not frequencias: return [], []
    frequencias_ordenadas = sorted(frequencias)
    top_frios = [num for _, num in frequencias_ordenadas[:3]]
    top_quentes = [num for _, num in frequencias_ordenadas[-3:]][::-1]
    return top_frios, top_quentes

def calcular_forca_sinal(alvo: str, historico: List[str]) -> int:
    """Calcula a força de um sinal baseado em quão profundo no histórico está a última ocorrência."""
    forca = 0
    for item in historico:
        if item != alvo:
            forca += 1
        else:
            break
    return forca

# ====================================================================
# === LÓGICA CENTRAL DE APOSTAS ======================================
# ====================================================================

def _gerenciar_aposta(estado: Dict[str, Any], resultado_caiu: str, tipo_estrategia: str) -> Tuple[str, Any | None]:
    """Função unificada para gerenciar o ciclo de apostas (Vitória, Derrota, La Partage)."""
    global BANCA_ATUAL
    
    alvo = estado['APOSTA_EM']
    if not alvo:
        return "", None

    mensagem = ""
    sinal_ativo = None
    valor_aposta = estado['VALOR']
    
    # --- Verificação de Vitória ---
    if resultado_caiu == alvo:
        ganho = valor_aposta * estado['GANHO_FATOR']
        BANCA_ATUAL += ganho
        mensagem += f"✅ VITÓRIA ({tipo_estrategia})! Ganhos: R$ {ganho:.2f}. RESET.\n"
        estado['VALOR'] = APOSTA_INICIAL_BASE
        estado['PERDAS'] = 0
        estado['APOSTA_EM'] = None
        return mensagem, None

    # --- Verificação de Zero (com regra La Partage) ---
    if resultado_caiu == 'G' and estado['TIPO'] == '1:1' and LA_PARTAGE_ATIVO and TIPO_ROLETA == 'EUROPEIA':
        perda = valor_aposta / 2
        BANCA_ATUAL -= perda
        mensagem += f"🟡 LA PARTAGE ({tipo_estrategia}): Zero caiu. Meia perda (R$ {perda:.2f}). Aposta mantém o valor.\n"
        # A progressão Martingale NÃO avança. A aposta continua com o mesmo valor.
        sinal_ativo = (alvo, valor_aposta, tipo_estrategia, 0)
        return mensagem, sinal_ativo

    # --- Verificação de Derrota ---
    BANCA_ATUAL -= valor_aposta
    estado['PERDAS'] += 1
    estado['VALOR'] *= FATOR_MARTINGALE
    
    termo_derrota = "ZERO" if resultado_caiu == 'G' else "DERROTA"
    mensagem += f"❌ {termo_derrota} ({tipo_estrategia}). Perda R$ {valor_aposta:.2f}. Próxima aposta: R$ {estado['VALOR']:.2f}.\n"
    
    # --- Verificação de Limite de Perdas ---
    if estado['PERDAS'] > MAX_PERDAS_CONSECUTIVAS:
        mensagem += f"🚨 ALERTA ({tipo_estrategia}): Limite de perdas atingido. RESET.\n"
        estado['VALOR'] = APOSTA_INICIAL_BASE
        estado['PERDAS'] = 0
        estado['APOSTA_EM'] = None
        return mensagem, None
    
    sinal_ativo = (alvo, estado['VALOR'], tipo_estrategia, 0)
    return mensagem, sinal_ativo

def analisar_sequencia_simples(chave_estado: str, resultado_atual: str) -> Tuple[str, Any | None]:
    """Analisa sequências para apostas 1:1 (Cor, Par/Ímpar, Alto/Baixo)."""
    estado = ESTADOS[chave_estado]
    
    # 1. Gerencia aposta ativa, se houver
    msg, sinal_ativo = _gerenciar_aposta(estado, resultado_atual, chave_estado)
    if sinal_ativo: return msg, sinal_ativo
    
    # 2. Procura por um novo sinal para iniciar
    if estado['APOSTA_EM'] is None and len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        ref = estado['HISTORICO'][0]
        if ref != 'G' and ref != 'ZERO' and all(h == ref for h in estado['HISTORICO'][:estado['MIN_SEQUENCIA']]):
            # Determina o alvo oposto
            if chave_estado == 'COR': alvo = 'B' if ref == 'R' else 'R'
            elif chave_estado == 'PAR_IMPAR': alvo = 'IMPAR' if ref == 'PAR' else 'PAR'
            else: alvo = 'ALTO' if ref == 'BAIXO' else 'BAIXO'
            
            estado['APOSTA_EM'] = alvo
            msg += f"💰 SINAL ({chave_estado}): Sequência de {estado['MIN_SEQUENCIA']}x {NOMENCLATURA[ref]} detectada. Apostar em {NOMENCLATURA[alvo]}.\n"
            return msg, (alvo, estado['VALOR'], chave_estado, 0)
            
    return msg, None

def analisar_sequencia_tercos(chave_estado: str, resultado_atual: str) -> Tuple[str, Any | None]:
    """Analisa atraso para Dúzias ou Colunas."""
    estado = ESTADOS[chave_estado]
    todos_alvos = ['D1', 'D2', 'D3'] if chave_estado == 'DUZIA' else ['C1', 'C2', 'C3']

    # 1. Gerencia aposta ativa, se houver
    msg, sinal_ativo = _gerenciar_aposta(estado, resultado_atual, chave_estado)
    if sinal_ativo: return msg, sinal_ativo
    
    # 2. Procura por um novo sinal para iniciar
    if estado['APOSTA_EM'] is None and len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        recentes = {h for h in estado['HISTORICO'][:estado['MIN_SEQUENCIA']] if h in todos_alvos}
        ausentes = [t for t in todos_alvos if t not in recentes]
        
        if len(ausentes) == 1:
            alvo = ausentes[0]
            estado['APOSTA_EM'] = alvo
            forca = calcular_forca_sinal(alvo, estado['HISTORICO'])
            msg += f"💰 SINAL ({chave_estado}): {NOMENCLATURA[alvo]} em atraso. Força: {forca}/{len(estado['HISTORICO'])}. Iniciar aposta.\n"
            return msg, (alvo, estado['VALOR'], chave_estado, forca)
            
    return msg, None

def analisar_numeros_frios(num_str: str) -> Tuple[str, Any | None]:
    """Analisa o atraso do número mais frio."""
    chave_estado = 'FRIO'
    estado = ESTADOS[chave_estado]
    
    # 1. Gerencia aposta ativa, se houver
    msg, sinal_ativo = _gerenciar_aposta(estado, num_str, chave_estado)
    if sinal_ativo: return msg, sinal_ativo

    # 2. Procura por um novo sinal para iniciar
    if estado['APOSTA_EM'] is None and len(TODOS_GIROS_HISTORICO) >= estado['MIN_SEQUENCIA']:
        top_frios, _ = analisar_frequencia_numeros()
        if not top_frios: return "", None
        
        alvo = top_frios[0]
        try:
            # Atraso é a posição do número na lista invertida
            atraso = TODOS_GIROS_HISTORICO[::-1].index(alvo) + 1
        except ValueError:
            # Se nunca saiu, o atraso é o total de giros
            atraso = len(TODOS_GIROS_HISTORICO)
        
        if atraso >= estado['MIN_SEQUENCIA']:
            estado['APOSTA_EM'] = alvo
            msg += f"💰 SINAL ({chave_estado}): Número {alvo} está a {atraso} giros sem sair. Iniciar aposta.\n"
            return msg, (alvo, estado['VALOR'], chave_estado, atraso)

    return msg, None

# ====================================================================
# === FUNÇÃO PRINCIPAL E LOOP DE EXECUÇÃO ============================
# ====================================================================

def _atualizar_historicos(num_str: str):
    """Apenas atualiza os estados e históricos globais com um novo número."""
    mapa = get_mapeamento_numero(num_str)
    if not mapa:
        return # Ignora número inválido no processamento

    TODOS_GIROS_HISTORICO.append(num_str)
    NUMEROS_RASTREAMENTO[num_str] += 1
    
    ESTADOS['COR']['HISTORICO'].insert(0, mapa['COR'])
    ESTADOS['PAR_IMPAR']['HISTORICO'].insert(0, mapa['PARIDADE'])
    ESTADOS['ALTO_BAIXO']['HISTORICO'].insert(0, mapa['ALTURA'])
    ESTADOS['DUZIA']['HISTORICO'].insert(0, mapa['DUZIA'])
    ESTADOS['COLUNA']['HISTORICO'].insert(0, mapa['COLUNA'])

    # Mantém os históricos com no máximo 10 registros
    for key in ESTADOS:
        if 'HISTORICO' in ESTADOS[key]:
            ESTADOS[key]['HISTORICO'] = ESTADOS[key]['HISTORICO'][:10]

def aplicar_estrategias(num_str: str) -> str:
    """Função central que processa um número e aplica as estratégias ativas."""
    
    # 1. Validação
    mapa = get_mapeamento_numero(num_str)
    if not mapa:
        return f"ERRO: Número inválido ('{num_str}')."

    # 2. Atualiza históricos com o novo número
    _atualizar_historicos(num_str)
    
    # 3. Geração de Feedback do Giro Atual
    output = f"➡️ CAIU: {num_str} ({NOMENCLATURA[mapa['COR']]}, {NOMENCLATURA[mapa['PARIDADE']]}) | Banca: R$ {BANCA_ATUAL:.2f}\n"
    output += "--------------------------------------\n"
    
    # 4. Aplicação das Estratégias Ativas
    sinais_ativos = []
    mensagens = ""
    
    if ESTRATEGIAS_ATIVAS['COR']:
        msg, sinal = analisar_sequencia_simples('COR', mapa['COR'])
        mensagens += msg; sinais_ativos.append(sinal)
    if ESTRATEGIAS_ATIVAS['PAR_IMPAR']:
        msg, sinal = analisar_sequencia_simples('PAR_IMPAR', mapa['PARIDADE'])
        mensagens += msg; sinais_ativos.append(sinal)
    if ESTRATEGIAS_ATIVAS['ALTO_BAIXO']:
        msg, sinal = analisar_sequencia_simples('ALTO_BAIXO', mapa['ALTURA'])
        mensagens += msg; sinais_ativos.append(sinal)
    if ESTRATEGIAS_ATIVAS['DUZIA']:
        msg, sinal = analisar_sequencia_tercos('DUZIA', mapa['DUZIA'])
        mensagens += msg; sinais_ativos.append(sinal)
    if ESTRATEGIAS_ATIVAS['COLUNA']:
        msg, sinal = analisar_sequencia_tercos('COLUNA', mapa['COLUNA'])
        mensagens += msg; sinais_ativos.append(sinal)
    if ESTRATEGIAS_ATIVAS['FRIO']:
        msg, sinal = analisar_numeros_frios(num_str)
        mensagens += msg; sinais_ativos.append(sinal)

    output += mensagens

    # 5. Consolidação da Ação Final
    instrucoes_finais = []
    for sinal in filter(None, sinais_ativos):
        aposta_em, valor, tipo, forca = sinal
        termo = NOMENCLATURA_ACAO.get(aposta_em, aposta_em)
        
        if tipo in ['DUZIA', 'COLUNA']:
            instrucoes_finais.append(f"R$ {valor:.2f} na {termo} (Força: {forca})")
        elif tipo == 'FRIO':
            instrucoes_finais.append(f"R$ {valor:.2f} no número {aposta_em} (Atraso: {forca})")
        else: # Apostas 1:1
            preposicao = "no" if termo in ['vermelho', 'preto', 'par', 'ímpar', 'baixo (1-18)', 'alto (19-36)'] else "em"
            instrucoes_finais.append(f"R$ {valor:.2f} {preposicao} {termo}")

    final_order = " e ".join(instrucoes_finais) if instrucoes_finais else "Aguarde Sinal"
    output += f"🎯 AÇÃO: {final_order}\n"
    output += "--------------------------------------"
    return output

def configurar_e_preparar():
    """Coleta as configurações iniciais do usuário, incluindo o histórico."""
    global BANCA_INICIAL, BANCA_ATUAL
    
    print("\n[Assistente de Roleta v4 - Aquecimento Inteligente]")
    
    # Coleta da Banca Inicial
    while True:
        try:
            banca_str = input("Qual o valor da sua banca inicial? R$ ").strip().replace(',', '.')
            BANCA_INICIAL = float(banca_str)
            BANCA_ATUAL = BANCA_INICIAL
            print(f"Banca inicial de R$ {BANCA_ATUAL:.2f} definida.")
            break
        except ValueError:
            print("Valor inválido. Por favor, digite um número.")
    
    # Configuração das Estratégias
    print("\n--- Configuração das Estratégias (Responda com 'S' para Sim ou 'N' para Não) ---")
    for chave in ESTRATEGIAS_ATIVAS:
        while True:
            resposta = input(f"Ativar estratégia de '{chave}'? (S/N): ").strip().upper()
            if resposta in ['S', 'N']:
                ESTRATEGIAS_ATIVAS[chave] = (resposta == 'S')
                break
            else:
                print("Resposta inválida. Por favor, digite 'S' ou 'N'.")
    
    print("\nEstratégias ativas: " + ", ".join([k for k, v in ESTRATEGIAS_ATIVAS.items() if v]))
    if not any(ESTRATEGIAS_ATIVAS.values()):
        print("AVISO: Nenhuma estratégia foi ativada.")
    
    # Coleta do Histórico Inicial (Aquecimento)
    print("\n--- Aquecimento do Sistema (Insira os 12 últimos resultados) ---")
    historico_inicial = []
    valid_range = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_range.append('00')

    for i in range(12):
        while True:
            pos = f"{i+1}º"
            prompt = f"Digite o {pos} resultado (o mais recente primeiro): " if i == 0 else f"Digite o {pos} resultado: "
            num_str = input(prompt).strip().upper()
            if num_str in valid_range:
                historico_inicial.append(num_str)
                break
            else:
                print("Número inválido. Tente novamente.")

    # Processa o histórico na ordem correta (do mais antigo para o mais novo)
    for numero in reversed(historico_inicial):
        _atualizar_historicos(numero)

    print("\n✅ Sistema aquecido com 12 resultados. Pronto para iniciar!")
    print("--------------------------------------")


def main():
    """Função principal para rodar o assistente."""
    configurar_e_preparar()

    prompt_base = f"Qual o próximo número (ou 'SAIR')? "

    while True:
        try:
            prompt = input(prompt_base).strip().upper()
            if prompt == "SAIR":
                print("\nEncerrando Assistente.")
                resultado_final = BANCA_ATUAL - BANCA_INICIAL
                print(f"Banca Final: R$ {BANCA_ATUAL:.2f} | Resultado da Sessão: R$ {resultado_final:+.2f}")
                break
            
            feedback = aplicar_estrategias(prompt)
            print(feedback)
        
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando assistente.")
            break
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            break

if __name__ == "__main__":
    main()
