import math
from collections import Counter
from typing import List, Tuple, Dict, Any

# ====================================================================
# === CONFIGURAÇÕES GERAIS ===========================================
# ====================================================================

# --- Configurações de Aposta e Risco ---
APOSTA_INICIAL_BASE = 0.50
FATOR_MARTINGALE = 2.0
MAX_APOSTA_VALOR = 2.00  # Teto máximo para qualquer aposta.
MAX_PERDAS_CONSECUTIVAS = 4 # <--- MUDANÇA: Agora será respeitado rigorosamente (total de 4 apostas perdidas)
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
# <--- MUDANÇA: 'PERDAS' agora rastreia o valor monetário perdido no ciclo.
# <--- MUDANÇA: 'PERDAS_CONSECUTIVAS' rastreia a contagem de perdas.
ESTADOS = {
    'COR':       {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'PAR_IMPAR': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'ALTO_BAIXO':{'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'},
    'DUZIA':     {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'TIPO': '2:1'},
    'COLUNA':    {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'TIPO': '2:1'},
    'FRIO':      {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL_BASE, 'PERDAS_CONSECUTIVAS': 0, 'PERDAS_CICLO_VALOR': 0.0, 'MIN_SEQUENCIA': MIN_ATRASO_NUMERO_FRIO, 'GANHO_FATOR': 36, 'TIPO': '35:1'},
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
    if num_str == '0' or num_str == '00':
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
    try:
        # index() retorna a primeira ocorrência, que é o atraso.
        return historico.index(alvo)
    except ValueError:
        # Se o alvo não está no histórico, a força é o tamanho do histórico.
        return len(historico)

# ====================================================================
# === LÓGICA CENTRAL DE APOSTAS ======================================
# ====================================================================

def _resetar_estado_aposta(estado: Dict[str, Any]) -> None:
    """Função auxiliar para resetar o estado de uma estratégia."""
    estado['VALOR'] = APOSTA_INICIAL_BASE
    estado['PERDAS_CONSECUTIVAS'] = 0
    estado['PERDAS_CICLO_VALOR'] = 0.0
    estado['APOSTA_EM'] = None

# <--- MUDANÇA: Função _gerenciar_aposta totalmente reescrita para ser mais "cuidadosa"
def _gerenciar_aposta(estado: Dict[str, Any], resultado_caiu: str, tipo_estrategia: str) -> Tuple[str, Any | None]:
    """Função unificada para gerenciar o ciclo de apostas (Vitória, Derrota, La Partage) com gestão de risco."""
    global BANCA_ATUAL

    alvo = estado['APOSTA_EM']
    if not alvo:
        return "", None

    mensagem = ""
    sinal_ativo = None
    valor_aposta = estado['VALOR']

    # --- 1. Verificação de Vitória ---
    if resultado_caiu == alvo:
        lucro_bruto = valor_aposta * (estado['GANHO_FATOR'] - 1)
        BANCA_ATUAL += lucro_bruto
        lucro_liquido_ciclo = lucro_bruto - estado['PERDAS_CICLO_VALOR']
        
        mensagem += f"✅ VITÓRIA ({tipo_estrategia})! Lucro: R$ {lucro_bruto:.2f}. "
        mensagem += f"Resultado do Ciclo: R$ {lucro_liquido_ciclo:+.2f}. RESET.\n"
        
        _resetar_estado_aposta(estado)
        return mensagem, None

    # --- 2. Verificação de Zero (com regra La Partage) ---
    if resultado_caiu in ('G', 'ZERO') and estado['TIPO'] == '1:1' and LA_PARTAGE_ATIVO and TIPO_ROLETA == 'EUROPEIA':
        perda = valor_aposta / 2
        BANCA_ATUAL -= perda
        estado['PERDAS_CICLO_VALOR'] += perda
        
        mensagem += f"🟡 LA PARTAGE ({tipo_estrategia}): Zero caiu. Meia perda (R$ {perda:.2f}). "
        mensagem += f"Total perdido no ciclo: R$ {estado['PERDAS_CICLO_VALOR']:.2f}. Aposta mantém o valor.\n"
        
        # A progressão Martingale NÃO avança. A aposta continua com o mesmo valor.
        # Mas verificamos se a banca ainda permite a *próxima* aposta
        proxima_aposta_final = min(valor_aposta, BANCA_ATUAL)
        estado['VALOR'] = proxima_aposta_final
        sinal_ativo = (alvo, proxima_aposta_final, tipo_estrategia, 0)
        
        if proxima_aposta_final < valor_aposta:
             mensagem += f"⚠️ ALERTA ({tipo_estrategia}): Banca insuficiente para próxima aposta. Apostando R$ {proxima_aposta_final:.2f} (todo o saldo).\n"
        
        return mensagem, sinal_ativo

    # --- 3. Verificação de Derrota ---
    BANCA_ATUAL -= valor_aposta
    estado['PERDAS_CONSECUTIVAS'] += 1
    estado['PERDAS_CICLO_VALOR'] += valor_aposta

    termo_derrota = "ZERO" if resultado_caiu in ('G', 'ZERO') else "DERROTA"
    mensagem += f"❌ {termo_derrota} ({tipo_estrategia}). Perda R$ {valor_aposta:.2f}. Total perdido no ciclo: R$ {estado['PERDAS_CICLO_VALOR']:.2f}.\n"

    # --- 4. Lógica de "Cuidado" (Verificação de Limites e Recuperação) ---

    # Verificação 1: Limite de Perdas Consecutivas
    if estado['PERDAS_CONSECUTIVAS'] >= MAX_PERDAS_CONSECUTIVAS:
        mensagem += f"🚨 ALERTA ({tipo_estrategia}): Limite de {MAX_PERDAS_CONSECUTIVAS} perdas atingido. RESET.\n"
        _resetar_estado_aposta(estado)
        return mensagem, None

    # Cálculo da Próxima Aposta
    proxima_aposta_calculada = valor_aposta * FATOR_MARTINGALE
    lucro_potencial_calculado = proxima_aposta_calculada * (estado['GANHO_FATOR'] - 1)

    # Verificação 2: Capacidade de Recuperação do Martingale (sem teto)
    # O lucro da próxima aposta cobre o total já perdido?
    if lucro_potencial_calculado < estado['PERDAS_CICLO_VALOR']:
        mensagem += f"🚨 ALERTA ({tipo_estrategia}): Próxima aposta (R$ {proxima_aposta_calculada:.2f}) não cobriria perdas (R$ {estado['PERDAS_CICLO_VALOR']:.2f}). RESET.\n"
        _resetar_estado_aposta(estado)
        return mensagem, None

    # Verificação 3: Aplicando o Teto de Aposta
    proxima_aposta_teto = min(proxima_aposta_calculada, MAX_APOSTA_VALOR)
    if proxima_aposta_teto < proxima_aposta_calculada:
        mensagem += f"⚠️ AVISO ({tipo_estrategia}): Aposta limitada a R$ {proxima_aposta_teto:.2f} pelo teto (seria R$ {proxima_aposta_calculada:.2f}).\n"

    # Verificação 4: Capacidade de Recuperação com Teto (O PONTO MAIS CRÍTICO)
    lucro_potencial_teto = proxima_aposta_teto * (estado['GANHO_FATOR'] - 1)
    if lucro_potencial_teto < estado['PERDAS_CICLO_VALOR']:
        mensagem += f"🚨 ALERTA ({tipo_estrategia}): Aposta com Teto (R$ {proxima_aposta_teto:.2f}) não cobriria perdas (R$ {estado['PERDAS_CICLO_VALOR']:.2f}). RESET.\n"
        _resetar_estado_aposta(estado)
        return mensagem, None

    # Verificação 5: Verificação da Banca (All-In Cego)
    proxima_aposta_final = min(proxima_aposta_teto, BANCA_ATUAL)
    if proxima_aposta_final < proxima_aposta_teto:
        mensagem += f"⚠️ ALERTA ({tipo_estrategia}): Banca insuficiente. Apostando R$ {proxima_aposta_final:.2f} (todo o saldo).\n"

    # Se a banca for zero ou negativa, não há o que fazer.
    if proxima_aposta_final <= 0:
        mensagem += f"🚨 ALERTA ({tipo_estrategia}): Banca zerada. Ciclo RESETADO.\n"
        _resetar_estado_aposta(estado)
        return mensagem, None

    # --- 5. Definir Próxima Aposta ---
    estado['VALOR'] = proxima_aposta_final
    mensagem += f"📈 Próxima aposta ({tipo_estrategia}): R$ {estado['VALOR']:.2f}.\n"
    sinal_ativo = (alvo, estado['VALOR'], tipo_estrategia, 0)
    return mensagem, sinal_ativo


def analisar_sequencia_simples(chave_estado: str, resultado_atual: str) -> Tuple[str, Any | None]:
    """Analisa sequências para apostas 1:1 (Cor, Par/Ímpar, Alto/Baixo)."""
    estado = ESTADOS[chave_estado]

    # 1. Gerencia aposta ativa, se houver
    msg, sinal_ativo = _gerenciar_aposta(estado, resultado_atual, chave_estado)
    if estado['APOSTA_EM']: return msg, sinal_ativo

    # 2. Procura por um novo sinal para iniciar
    if len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        ref = estado['HISTORICO'][0]
        sequencia_recente = estado['HISTORICO'][:estado['MIN_SEQUENCIA']]
        if ref not in ('G', 'ZERO') and all(h == ref for h in sequencia_recente):
            # Determina o alvo oposto
            if chave_estado == 'COR': alvo = 'B' if ref == 'R' else 'R'
            elif chave_estado == 'PAR_IMPAR': alvo = 'IMPAR' if ref == 'PAR' else 'PAR'
            else: alvo = 'ALTO' if ref == 'BAIXO' else 'BAIXO'

            # <--- MUDANÇA: Verifica se a banca permite a aposta inicial
            valor_aposta = min(estado['VALOR'], BANCA_ATUAL)
            if valor_aposta < estado['VALOR']:
                msg += f"⚠️ ALERTA ({chave_estado}): Banca (R$ {BANCA_ATUAL:.2f}) menor que aposta inicial. Ajustando.\n"
            
            if valor_aposta <= 0:
                 msg += f"🚨 ALERTA ({chave_estado}): Banca zerada. Impossível iniciar aposta.\n"
                 return msg, None

            estado['APOSTA_EM'] = alvo
            estado['VALOR'] = valor_aposta # <--- MUDANÇA
            msg += f"💰 SINAL ({chave_estado}): Sequência de {estado['MIN_SEQUENCIA']}x {NOMENCLATURA[ref]} detectada. Apostar R$ {valor_aposta:.2f} em {NOMENCLATURA[alvo]}.\n"
            return msg, (alvo, valor_aposta, chave_estado, 0)

    return msg, None

# <--- MUDANÇA: Lógica de Terços reescrita para ser mais precisa
def analisar_sequencia_tercos(chave_estado: str, resultado_atual: str) -> Tuple[str, Any | None]:
    """Analisa atraso para Dúzias ou Colunas, apostando no mais atrasado."""
    estado = ESTADOS[chave_estado]
    todos_alvos = ['D1', 'D2', 'D3'] if chave_estado == 'DUZIA' else ['C1', 'C2', 'C3']

    # 1. Gerencia aposta ativa, se houver
    msg, sinal_ativo = _gerenciar_aposta(estado, resultado_atual, chave_estado)
    if estado['APOSTA_EM']: return msg, sinal_ativo

    # 2. Procura por um novo sinal para iniciar
    # Aposta no terço com o maior atraso, se o atraso for >= MIN_SEQUENCIA
    if len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        
        # Calcula o atraso de todos os alvos
        atrasos = [(calcular_forca_sinal(t, estado['HISTORICO']), t) for t in todos_alvos]
        atrasos.sort(reverse=True) # Ordena do maior atraso para o menor
        
        maior_atraso, alvo = atrasos[0]

        if maior_atraso >= estado['MIN_SEQUENCIA']:
            
            # <--- MUDANÇA: Verifica se a banca permite a aposta inicial
            valor_aposta = min(estado['VALOR'], BANCA_ATUAL)
            if valor_aposta < estado['VALOR']:
                msg += f"⚠️ ALERTA ({chave_estado}): Banca (R$ {BANCA_ATUAL:.2f}) menor que aposta inicial. Ajustando.\n"

            if valor_aposta <= 0:
                 msg += f"🚨 ALERTA ({chave_estado}): Banca zerada. Impossível iniciar aposta.\n"
                 return msg, None

            estado['APOSTA_EM'] = alvo
            estado['VALOR'] = valor_aposta # <--- MUDANÇA
            msg += f"💰 SINAL ({chave_estado}): {NOMENCLATURA[alvo]} é o mais atrasado ({maior_atraso} giros). Iniciar aposta R$ {valor_aposta:.2f}.\n"
            return msg, (alvo, valor_aposta, chave_estado, maior_atraso)

    return msg, None

def analisar_numeros_frios(num_str: str) -> Tuple[str, Any | None]:
    """Analisa o atraso do número mais frio."""
    chave_estado = 'FRIO'
    estado = ESTADOS[chave_estado]

    # 1. Gerencia aposta ativa, se houver. Para números, o resultado é o próprio número.
    msg, sinal_ativo = _gerenciar_aposta(estado, num_str, chave_estado)
    if estado['APOSTA_EM']: return msg, sinal_ativo

    # 2. Procura por um novo sinal para iniciar
    top_frios, _ = analisar_frequencia_numeros()
    if not top_frios: return "", None

    alvo = top_frios[0]
    try:
        atraso = TODOS_GIROS_HISTORICO[::-1].index(alvo)
    except ValueError:
        atraso = len(TODOS_GIROS_HISTORICO)

    if atraso >= estado['MIN_SEQUENCIA']:
        
        # <--- MUDANÇA: Verifica se a banca permite a aposta inicial
        valor_aposta = min(estado['VALOR'], BANCA_ATUAL)
        if valor_aposta < estado['VALOR']:
            msg += f"⚠️ ALERTA ({chave_estado}): Banca (R$ {BANCA_ATUAL:.2f}) menor que aposta inicial. Ajustando.\n"

        if valor_aposta <= 0:
             msg += f"🚨 ALERTA ({chave_estado}): Banca zerada. Impossível iniciar aposta.\n"
             return msg, None

        estado['APOSTA_EM'] = alvo
        estado['VALOR'] = valor_aposta # <--- MUDANÇA
        msg += f"💰 SINAL ({chave_estado}): Número {alvo} está a {atraso} giros sem sair. Iniciar aposta R$ {valor_aposta:.2f}.\n"
        return msg, (alvo, valor_aposta, chave_estado, atraso)

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
    if num_str in NUMEROS_RASTREAMENTO:
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

    # 2. Atualiza históricos com o novo número ANTES de processar apostas
    _atualizar_historicos(num_str)

    # 3. Geração de Feedback do Giro Atual
    output = f"➡️ CAIU: {num_str} ({NOMENCLATURA.get(mapa.get('COR'), '?')}, {NOMENCLATURA.get(mapa.get('PARIDADE'), '?')}) | Banca: R$ {BANCA_ATUAL:.2f}\n"
    output += "--------------------------------------\n"

    # 4. Aplicação das Estratégias Ativas
    sinais_ativos = []
    mensagens = ""
    
    # Mapeamento para evitar repetição de código
    estrategias_map = {
        'COR': (analisar_sequencia_simples, 'COR', mapa['COR']),
        'PAR_IMPAR': (analisar_sequencia_simples, 'PAR_IMPAR', mapa['PARIDADE']),
        'ALTO_BAIXO': (analisar_sequencia_simples, 'ALTO_BAIXO', mapa['ALTURA']),
        'DUZIA': (analisar_sequencia_tercos, 'DUZIA', mapa['DUZIA']),
        'COLUNA': (analisar_sequencia_tercos, 'COLUNA', mapa['COLUNA']),
        'FRIO': (analisar_numeros_frios, num_str, None) # Argumento diferente para 'FRIO'
    }

    for nome_estrategia, (funcao, arg1, arg2) in estrategias_map.items():
        if ESTRATEGIAS_ATIVAS[nome_estrategia]:
            if nome_estrategia == 'FRIO':
                msg, sinal = funcao(arg1) # Chama analisar_numeros_frios(num_str)
            else:
                msg, sinal = funcao(arg1, arg2) # Chama analisar_...('CHAVE', resultado)
            mensagens += msg
            if sinal:
                sinais_ativos.append(sinal)

    output += mensagens

    # 5. Consolidação da Ação Final
    instrucoes_finais = []
    for sinal in sinais_ativos:
        aposta_em, valor, tipo, forca = sinal
        termo = NOMENCLATURA_ACAO.get(aposta_em, aposta_em)

        if tipo in ['DUZIA', 'COLUNA']:
            instrucoes_finais.append(f"R$ {valor:.2f} na {termo} (Atraso: {forca})")
        elif tipo == 'FRIO':
            instrucoes_finais.append(f"R$ {valor:.2f} no número {aposta_em} (Atraso: {forca})")
        else: # Apostas 1:1
            instrucoes_finais.append(f"R$ {valor:.2f} no {termo}")

    final_order = " e ".join(instrucoes_finais) if instrucoes_finais else "Aguarde Sinal"
    output += f"🎯 AÇÃO: {final_order}\n"
    output += "--------------------------------------"
    return output

def configurar_e_preparar():
    """Coleta as configurações iniciais do usuário, incluindo o histórico."""
    global BANCA_INICIAL, BANCA_ATUAL

    print("\n[Assistente de Roleta v5 - Gestão de Risco Avançada]")
    print("--------------------------------------------------")
    print("Configurações de Risco Atuais:")
    print(f"  - Aposta Base: R$ {APOSTA_INICIAL_BASE:.2f}")
    print(f"  - Fator Martingale: {FATOR_MARTINGALE}x")
    print(f"  - Teto de Aposta: R$ {MAX_APOSTA_VALOR:.2f}")
    print(f"  - Máx. Perdas por Ciclo: {MAX_PERDAS_CONSECUTIVAS}")
    print(f"  - La Partage (Europeia): {'Ativo' if LA_PARTAGE_ATIVO else 'Inativo'}")
    print("--------------------------------------------------")


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

    estrategias_selecionadas = [k for k, v in ESTRATEGIAS_ATIVAS.items() if v]
    if estrategias_selecionadas:
        print("\nEstratégias ativas: " + ", ".join(estrategias_selecionadas))
    else:
        print("\nAVISO: Nenhuma estratégia foi ativada.")

    # Coleta do Histórico Inicial (Aquecimento)
    print("\n--- Aquecimento do Sistema (Insira os 12 últimos resultados) ---")
    historico_inicial = []
    valid_range = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_range.append('00')

    for i in range(12):
        while True:
            pos = f"{i+1}º"
            prompt = f"Digite o {pos} resultado (o mais recente primeiro): " if i == 0 else f"Digite o {pos} resultado: "
            num_str = input(prompt).strip()
            if num_str in valid_range:
                historico_inicial.append(num_str)
                break
            else:
                print(f"Número inválido para roleta {TIPO_ROLETA}. Tente novamente.")

    # Processa o histórico na ordem correta (do mais antigo para o mais novo)
    print("\nProcessando histórico...")
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
            prompt = input(prompt_base).strip()
            if prompt.upper() == "SAIR":
                print("\nEncerrando Assistente.")
                resultado_final = BANCA_ATUAL - BANCA_INICIAL
                print(f"Banca Final: R$ {BANCA_ATUAL:.2f} | Resultado da Sessão: R$ {resultado_final:+.2f}")
                break
            
            if BANCA_ATUAL <= 0:
                 print(f"🚨 BANCA ZERADA (R$ {BANCA_ATUAL:.2f}). Encerrando sessão.")
                 break

            feedback = aplicar_estrategias(prompt)
            print(feedback)

        except (EOFError, KeyboardInterrupt):
            print("\n\nEncerrando assistente.")
            resultado_final = BANCA_ATUAL - BANCA_INICIAL
            print(f"Banca Final: R$ {BANCA_ATUAL:.2f} | Resultado da Sessão: R$ {resultado_final:+.2f}")
            break
        except Exception as e:
            print(f"\nOcorreu um erro inesperado: {e}")
            break

if __name__ == "__main__":
    main()