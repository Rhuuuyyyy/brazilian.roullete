import math
from collections import Counter
from typing import List, Tuple, Dict, Any
import sys

# ====================================================================
# === CONFIGURAÇÕES DA ESTRATÉGIA (BASEADO NO MODELO DO USUÁRIO) =====
# ====================================================================

# Constantes de Configuração
APOSTA_INICIAL = 0.50
FATOR_MARTINGALE = 2.0
MAX_PERDAS_CONSECUTIVAS = 4 
MIN_SEQUENCIA_COR = 3           # Número de resultados iguais para acionar a aposta de COR (Martingale 3x)
MIN_SEQUENCIA_TERCO_COLUNA = 2  # Resultados para acionar a aposta de ATRASO (Estratégia 2/3)

# NOVO: Define o tipo de roleta. 'EUROPEIA' (37 slots: 0-36) ou 'AMERICANA' (38 slots: 0-36, 00)
TIPO_ROLETA = 'EUROPEIA' 

# Mapeamento Unificado de Nomes/Termos para Feedback e Mapeamento
NOMENCLATURA = {
    'R': 'VERMELHO', 'B': 'PRETO', 'G': 'VERDE (ZERO)', 'G00': 'VERDE (ZERO DUPLO)',
    'D1': "1ª DÚZIA (1-12)", 'D2': "2ª DÚZIA (13-24)", 'D3': "3ª DÚZIA (25-36)",
    'C1': "1ª COLUNA (1,4,7...)", 'C2': "2ª COLUNA (2,5,8...)", 'C3': "3ª COLUNA (3,6,9...)",
    'ZERO': 'ZERO (0)', 'ZEROD': 'ZERO DUPLO (00)', 'PAR': 'PAR', 'IMPAR': 'ÍMPAR'
}

# Mapeamento SIMPLIFICADO para a ORDEM FINAL (AÇÃO)
NOMENCLATURA_ACAO = {
    'R': 'vermelho', 'B': 'preto', 
    'D1': "1ª dúzia", 'D2': "2ª dúzia", 'D3': "3ª dúzia",
    'C1': "1ª coluna", 'C2': "2ª coluna", 'C3': "3ª coluna",
}

# === VARIÁVEIS DE ESTADO AVANÇADO (Gerenciado globalmente, mas recomendado para refatoração OO) ===
ESTADOS = {
    'COR': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR, 'GANHO_FATOR': 2},
    'DUZIA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3},
    'COLUNA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3},
}

# Rastreamento de Frequência (Inclui 37 slots para EUROPEIA, 38 para AMERICANA: 0 a 36 e '00')
NUMEROS_RASTREAMENTO = {i: 0 for i in range(37)} 
if TIPO_ROLETA == 'AMERICANA':
    NUMEROS_RASTREAMENTO['00'] = 0
TODOS_GIROS_HISTORICO = []

# ====================================================================
# === FUNÇÕES DE MAPEAMENTO E ESTATÍSTICA MATEMÁTICA =================
# ====================================================================

# Constantes Matemáticas (atualizadas com base no TIPO_ROLETA)
NUM_SLOTS = 37 if TIPO_ROLETA == 'EUROPEIA' else 38
# Probabilidade esperada de um número PLENO (1/37 ou 1/38)
HOUSE_EDGE_PER_SLOT = 1 / NUM_SLOTS
# House Edge de apostas de dinheiro par (1/37 ou 2/38)
HOUSE_EDGE_EVEN_MONEY = (NUM_SLOTS - 2 * 18) / NUM_SLOTS


def get_tercos_colunas(num: str) -> Dict[str, str]:
    """Mapeia o resultado (str) para suas categorias (Cor, Dúzia, Coluna)."""
    
    if num == '0':
        return {'COR': 'G', 'TERCO': 'ZERO', 'COLUNA': 'ZERO', 'NUM_GRUPO': '0'}
    if num == '00':
        return {'COR': 'G00', 'TERCO': 'ZEROD', 'COLUNA': 'ZEROD', 'NUM_GRUPO': '00'}

    try:
        n = int(num)
    except ValueError:
        return {'COR': 'N/A', 'TERCO': 'N/A', 'COLUNA': 'N/A', 'NUM_GRUPO': 'INVALIDO'}

    if not (1 <= n <= 36):
        # Isso não deve acontecer com a validação do input, mas é um guarda.
        return {'COR': 'N/A', 'TERCO': 'N/A', 'COLUNA': 'N/A', 'NUM_GRUPO': 'INVALIDO'}

    # === Mapeamento de Posição ===
    
    # Dúzias
    if 1 <= n <= 12: d = 'D1'
    elif 13 <= n <= 24: d = 'D2'
    else: d = 'D3'
    
    # Colunas (C1: 1, 4, 7... | C2: 2, 5, 8... | C3: 3, 6, 9...)
    if n % 3 == 1: c = 'C1'
    elif n % 3 == 2: c = 'C2'
    else: c = 'C3' # 3, 6, 9, 12...
    
    # Cor (Vermelho/Preto) - Lista CANÔNICA dos Vermelhos
    VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    cor = 'R' if n in VERMELHOS else 'B'
    
    return {'COR': cor, 'TERCO': d, 'COLUNA': c, 'NUM_GRUPO': num}

def calcular_estatisticas_basicas() -> Dict[str, float]:
    """Calcula estatísticas de House Edge, Desvio do Zero e Qui-quadrado (Chi²)."""
    
    total_giros = len(TODOS_GIROS_HISTORICO)
    
    if total_giros == 0:
        return {"total_giros": 0, "chi2": 0.0, "desvio_zero": 0.0, "house_edge_global": HOUSE_EDGE_EVEN_MONEY}
    
    contagem = Counter(TODOS_GIROS_HISTORICO)
    frequencia_esperada_pleno = 1 / NUM_SLOTS
    
    # 1. Desvio do Zero (Desvio da Proporção de 'G' e 'G00')
    frequencia_zero_total = (contagem.get('0', 0) + contagem.get('00', 0)) / total_giros
    # A frequência esperada total de slots de House Edge é 1/37 (Europeia) ou 2/38 (Americana)
    frequencia_esperada_zero_total = HOUSE_EDGE_EVEN_MONEY * 2 # Aposta de Cor Cobre 18/37
    
    desvio_zero = frequencia_zero_total - frequencia_esperada_zero_total
    
    # 2. Teste Qui-quadrado (χ²) para todos os slots (0-36 e 00, se aplicável)
    soma_desvios_quadrado = 0
    
    # Itera sobre todos os slots possíveis (0-36 e '00')
    slots_para_chi2 = list(range(37)) # 0 a 36
    if TIPO_ROLETA == 'AMERICANA':
        slots_para_chi2.append('00')
        
    for slot in slots_para_chi2:
        ocorrencias = contagem.get(str(slot), 0) if isinstance(slot, int) else contagem.get(slot, 0)
        soma_desvios_quadrado += (ocorrencias - total_giros * frequencia_esperada_pleno)**2
    
    divisor_chi2 = total_giros * frequencia_esperada_pleno
    variancia_amostral_pleno = soma_desvios_quadrado / divisor_chi2 if divisor_chi2 != 0 else 0.0
    
    return {
        "total_giros": total_giros,
        "desvio_zero": desvio_zero,
        "chi2": variancia_amostral_pleno,
        "house_edge_global": HOUSE_EDGE_EVEN_MONEY
    }

def analisar_frequencia_numeros():
    """Identifica os 3 números mais frios (cold) e 3 mais quentes (hot) ignorando os Zeros."""
    
    frequencias = []
    for num, contagem in NUMEROS_RASTREAMENTO.items():
        if num != 0 and num != '00': # Ignora Zeros
            frequencias.append((contagem, num))
            
    frequencias_ordenadas = sorted(frequencias, key=lambda x: x[0])

    top_frios = [num for contagem, num in frequencias_ordenadas[:3]]
    top_quentes = [num for contagem, num in frequencias_ordenadas[-3:]][::-1] 

    return top_frios, top_quentes

# ====================================================================
# === FUNÇÕES DE GESTÃO DE MARTINGALE E ATRASO (REFATORADO) ==========
# ====================================================================

def formatar_historico(historico):
    """Formata o histórico para exibição no console."""
    return " | ".join([NOMENCLATURA.get(c, c) for c in historico])

def _gerenciar_aposta(estado: Dict[str, Any], resultado_caiu: str, tipo_aposta: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """
    Função unificada para gerenciar o Martingale (Vitória, Derrota, Zero, Limite).
    Retorna (mensagem_feedback, sinal_ativo)
    """
    mensagem = ""
    sinal_ativo = None
    
    alvo = estado['APOSTA_EM']
    valor = estado['VALOR']
    ganho_fator = estado['GANHO_FATOR']

    if alvo:
        
        # 1. VERIFICAÇÃO DE VITÓRIA
        if resultado_caiu == alvo:
            ganho = valor * ganho_fator
            # Feedback simplificado
            mensagem += f"✅ VITÓRIA ({tipo_aposta.upper()})! Ganhos: R$ {ganho:.2f}. RESET.\n"
            estado['VALOR'] = APOSTA_INICIAL
            estado['PERDAS'] = 0
            estado['APOSTA_EM'] = None
            return mensagem, None
        
        # 2. VERIFICAÇÃO DE ZERO (PERDA e DOBRA)
        elif resultado_caiu in ('G', 'G00'):
            mensagem += f"🟡 ZERO ({tipo_aposta.upper()}) CAIU. Perda. Fator: {estado['PERDAS'] + 1}x -> {estado['PERDAS'] + 2}x\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
            
        # 3. VERIFICAÇÃO DE DERROTA (PERDA e DOBRA)
        else:
            # Não exibe o termo do resultado para não poluir a saída
            mensagem += f"❌ DERROTA ({tipo_aposta.upper()}). Perda. Fator: {estado['PERDAS'] + 1}x -> {estado['PERDAS'] + 2}x\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
        
        # 4. TRATAMENTO APÓS PERDA (Continuar Aposta no Alvo)
        if estado['APOSTA_EM'] and estado['PERDAS'] > 0:
            if estado['PERDAS'] > MAX_PERDAS_CONSECUTIVAS:
                mensagem += f"🚨 ALERTA ({tipo_aposta.upper()}): Limite de perdas atingido ({MAX_PERDAS_CONSECUTIVAS}x). RESET.\n"
                estado['VALOR'] = APOSTA_INICIAL
                estado['PERDAS'] = 0
                estado['APOSTA_EM'] = None
                return mensagem, None
            
            # Sinal Ativo
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], tipo_aposta)

    return mensagem, sinal_ativo

def analisar_sequencia_cor(estado_key: str, cor_caiu: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """Analisa a sequência simples (Cor) e gera sinal Martingale (3x)."""
    estado = ESTADOS[estado_key]
    
    # 1. GERENCIAR MARTINGALE PENDENTE
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, cor_caiu, estado_key)
    
    if sinal_ativo:
        return msg_martingale, sinal_ativo 
    
    # 2. DEFINIÇÃO DO PRÓXIMO SINAL (Se não houver aposta pendente)
    if estado['APOSTA_EM'] is None and len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        
        cor_referencia = estado['HISTORICO'][0]
        sequencia = 0
        
        # Conta a sequência da cor mais recente
        for cor_hist in estado['HISTORICO']:
            if cor_hist == cor_referencia:
                sequencia += 1
            else:
                break
        
        if sequencia >= estado['MIN_SEQUENCIA'] and cor_referencia in ('R', 'B'):
            # Aposta na cor oposta (Martingale contra a streak)
            estado['APOSTA_EM'] = 'B' if cor_referencia == 'R' else 'R' 
            
            # Sinal Ativo
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], estado_key)
            msg_martingale += f"💰 SINAL ({estado_key.upper()}): Sequência de {sequencia}x detectada. Iniciar Martingale.\n"
            return msg_martingale, sinal_ativo
            
        else:
            return msg_martingale, None # Aguardando sinal
            
    elif estado['APOSTA_EM'] is None:
        return msg_martingale, None # Aguardando histórico
        
    return msg_martingale, None 

def analisar_sequencia_tercos_colunas(estado_key: str, resultado_terco: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """Analisa a sequência de Terços (D1/D2/D3) ou Colunas (C1/C2/C3) - Estratégia de Atraso (2/3)."""
    
    estado = ESTADOS[estado_key]
    todos_tercos = ['D1', 'D2', 'D3'] if estado_key == 'DUZIA' else ['C1', 'C2', 'C3']

    # 1. GERENCIAR MARTINGALE PENDENTE
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, resultado_terco, estado_key)
    
    if sinal_ativo:
        return msg_martingale, sinal_ativo 

    # 2. DEFINIÇÃO DO PRÓXIMO SINAL (Aposta no Terço/Coluna em Atraso)
    if estado['APOSTA_EM'] is None:
        
        if len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
            
            recentes = estado['HISTORICO'][:estado['MIN_SEQUENCIA']]
            contagem_recente = Counter(t for t in recentes if t in todos_tercos)
            tercos_ausentes = [t for t in todos_tercos if t not in contagem_recente]
            
            # Sinal: Se APENAS UM terço/coluna está ausente (Estratégia 2/3)
            if len(tercos_ausentes) == 1:
                terco_sinal = tercos_ausentes[0]
                estado['APOSTA_EM'] = terco_sinal
                
                # Sinal Ativo
                sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], estado_key)
                termo_sinal = NOMENCLATURA.get(terco_sinal).split('(')[0].strip()
                msg_martingale += f"💰 SINAL ({estado_key.upper()}): {termo_sinal} em atraso. Iniciar Martingale.\n"
                
                return msg_martingale, sinal_ativo
            else:
                return msg_martingale, None # Aguardando sinal

        elif estado['APOSTA_EM'] is None:
            return msg_martingale, None # Aguardando histórico
            
    return msg_martingale, None


def aplicar_estrategia_avancada(num_str: str):
    """
    Função principal que gerencia todas as estratégias e retorna a ordem de ação concisa.
    """
    # Validação de entrada
    valid_numbers = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_numbers.append('00')

    if num_str not in valid_numbers:
        return f"ERRO: Número inválido ('{num_str}'). Digite um número de 0 a 36 ou '00' (se for americana)."

    resultado_mapa = get_tercos_colunas(num_str)
    
    # 1. Rastreamento e Registro (Utiliza TODO O HISTÓRICO, atendendo à precisão)
    global NUMEROS_RASTREAMENTO
    global TODOS_GIROS_HISTORICO
    
    NUMEROS_RASTREAMENTO[num_str] = NUMEROS_RASTREAMENTO.get(num_str, 0) + 1
    TODOS_GIROS_HISTORICO.append(num_str)
    
    ESTADOS['COR']['HISTORICO'].insert(0, resultado_mapa['COR'])
    ESTADOS['DUZIA']['HISTORICO'].insert(0, resultado_mapa['TERCO'])
    ESTADOS['COLUNA']['HISTORICO'].insert(0, resultado_mapa['COLUNA'])

    for key in ESTADOS:
        ESTADOS[key]['HISTORICO'] = ESTADOS[key]['HISTORICO'][:10]

    # Mensagem de resultado atual (Apenas feedback de entrada)
    output_result = f"➡️ CAIU: {num_str} - {NOMENCLATURA.get(resultado_mapa['COR'])} | DÚZIA: {NOMENCLATURA.get(resultado_mapa['TERCO'])} | COLUNA: {NOMENCLATURA.get(resultado_mapa['COLUNA'])}\n"
    output_result += "--------------------------------------\n"
    
    sinais_ativos = []
    
    # 2. Analisar e gerenciar estados (Coletando mensagens de feedback e sinais ativos)
    msg_cor, sinal_cor = analisar_sequencia_cor('COR', resultado_mapa['COR'])
    if sinal_cor: sinais_ativos.append(sinal_cor)

    msg_duzia, sinal_duzia = analisar_sequencia_tercos_colunas('DUZIA', resultado_mapa['TERCO'])
    if sinal_duzia: sinais_ativos.append(sinal_duzia)

    msg_coluna, sinal_coluna = analisar_sequencia_tercos_colunas('COLUNA', resultado_mapa['COLUNA'])
    if sinal_coluna: sinais_ativos.append(sinal_coluna)
        
    output_result += msg_cor + msg_duzia + msg_coluna
    
    # 3. CONSOLIDAÇÃO SIMPLES DA ORDEM FINAL (APENAS A AÇÃO)
    top_frios, _ = analisar_frequencia_numeros()
    
    instrucoes_finais = [] 
    sinais_2_por_1 = [s for s in sinais_ativos if s[2] in ['DUZIA', 'COLUNA']]
    sinais_1_por_1 = [s for s in sinais_ativos if s[2] == 'COR']
    
    # Processar Dúzia/Coluna (Ex: R$ 1.00 na 1ª dúzia)
    for aposta_em, valor, tipo in sinais_2_por_1:
        termo_alvo = NOMENCLATURA_ACAO.get(aposta_em, aposta_em)
        # Apostas em dúzias/colunas usam 'na'
        instrucoes_finais.append(f"R$ {valor:.2f} na {termo_alvo}") 

    # Processar Cor (Ex: R$ 1.00 no preto)
    for aposta_em, valor, tipo in sinais_1_por_1:
        cor_mapa = NOMENCLATURA_ACAO.get(aposta_em)
        # Apostas em cor usam 'no'
        instrucoes_finais.append(f"R$ {valor:.2f} no {cor_mapa}")

    # Sugerir cobertura de frios (Se não houver Martingale ativo)
    estatisticas = calcular_estatisticas_basicas()
    if not sinais_ativos and estatisticas['total_giros'] > 10 and top_frios:
          instrucoes_finais.append(f"Monitorar Frios R$ {APOSTA_INICIAL:.2f}: {top_frios}")
    
    final_order = " e ".join(instrucoes_finais)
    
    if not final_order:
        final_order = "Aguarde Sinal"
        
    # Retorna o feedback operacional + Ação final
    output_result += f"🎯 AÇÃO: {final_order}\n"
    output_result += "--------------------------------------"
    
    return output_result


def main():
    # Removendo todos os prints de introdução para um console limpo
    print("\n[Assistente de Roleta Ativo]")

    valid_input_prompt = "Qual número caiu (0-36"
    if TIPO_ROLETA == 'AMERICANA':
        valid_input_prompt += " ou 00"
    valid_input_prompt += ") ou SAIR? "

    while True:
        try:
            prompt = input(valid_input_prompt).strip().upper()
            
            if prompt == "SAIR":
                print("\nEncerrando Assistente.")
                break
            
            if TIPO_ROLETA == 'AMERICANA' and prompt == '00':
                num_str = '00'
            else:
                try:
                    num = int(prompt)
                    if 0 <= num <= 36:
                        num_str = str(num)
                    else:
                        print("ERRO: Número fora do range (0 a 36).")
                        continue
                except ValueError:
                    print("ERRO: Entrada inválida. Digite um número válido (0-36 ou 00) ou SAIR.")
                    continue
            
            # Chama a função e imprime o resultado conciso
            feedback = aplicar_estrategia_avancada(num_str)
            print(feedback)
                
        except EOFError:
            print("\nEncerrando por fim de arquivo.")
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            break

if __name__ == "__main__":
    main()
