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

# NOVO: Define o sistema de progressão de apostas
# Opções: 'MARTINGALE' ou 'FIBONACCI'
SISTEMA_PROGRESSAO = 'MARTINGALE'

# NOVO: Configuração da Roda Europeia para a estratégia de vizinhos
RODA_EUROPEIA = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

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

# === VARIÁVEIS DE ESTADO AVANÇADO ===
ESTADOS = {
    'COR': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_COR, 'GANHO_FATOR': 2, 'FIB_INDEX': 2},
    'DUZIA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'FIB_INDEX': 2},
    'COLUNA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'FIB_INDEX': 2},
    # NOVO: Estratégia para apostar em números frios (straight up)
    'FRIO': {'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'GANHO_FATOR': 36, 'FIB_INDEX': 2, 'MIN_ATRASO': 15}, # Aposta após 15 giros sem sair
    # NOVO: Estratégia para apostar em vizinhos de um número quente
    'VIZINHOS': {'APOSTA_EM': [], 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'GANHO_FATOR': 36, 'FIB_INDEX': 2, 'NUM_VIZINHOS': 2}, # Aposta no número e 2 vizinhos de cada lado (total 5 números)
}

# NOVO: Gerenciamento de Banca
BANCA_INICIAL = 0.0
BANCA_ATUAL = 0.0

# Rastreamento de Frequência
NUMEROS_RASTREAMENTO = {str(i): 0 for i in range(37)} 
if TIPO_ROLETA == 'AMERICANA':
    NUMEROS_RASTREAMENTO['00'] = 0
TODOS_GIROS_HISTORICO = []

# ====================================================================
# === FUNÇÕES DE MAPEAMENTO E ESTATÍSTICA MATEMÁTICA =================
# ====================================================================

# Constantes Matemáticas
NUM_SLOTS = 37 if TIPO_ROLETA == 'EUROPEIA' else 38
HOUSE_EDGE_PER_SLOT = 1 / NUM_SLOTS
HOUSE_EDGE_EVEN_MONEY = (1 / NUM_SLOTS) if TIPO_ROLETA == 'EUROPEIA' else (2 / NUM_SLOTS)


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
        return {'COR': 'N/A', 'TERCO': 'N/A', 'COLUNA': 'N/A', 'NUM_GRUPO': 'INVALIDO'}

    if 1 <= n <= 12: d = 'D1'
    elif 13 <= n <= 24: d = 'D2'
    else: d = 'D3'
    
    if n % 3 == 1: c = 'C1'
    elif n % 3 == 2: c = 'C2'
    else: c = 'C3'
    
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
    
    frequencia_zero_total = (contagem.get('0', 0) + contagem.get('00', 0)) / total_giros
    frequencia_esperada_zero_total = HOUSE_EDGE_EVEN_MONEY 
    desvio_zero = frequencia_zero_total - frequencia_esperada_zero_total
    
    soma_desvios_quadrado = 0
    slots_para_chi2 = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA':
        slots_para_chi2.append('00')
        
    for slot in slots_para_chi2:
        ocorrencias = contagem.get(slot, 0)
        soma_desvios_quadrado += (ocorrencias - total_giros * frequencia_esperada_pleno)**2
    
    divisor_chi2 = total_giros * frequencia_esperada_pleno
    variancia_amostral_pleno = soma_desvios_quadrado / divisor_chi2 if divisor_chi2 != 0 else 0.0
    
    return {
        "total_giros": total_giros, "desvio_zero": desvio_zero, "chi2": variancia_amostral_pleno,
        "house_edge_global": HOUSE_EDGE_EVEN_MONEY
    }

def analisar_frequencia_numeros():
    """Identifica os 3 números mais frios (cold) e 3 mais quentes (hot) ignorando os Zeros."""
    frequencias = []
    for num, contagem in NUMEROS_RASTREAMENTO.items():
        if num not in ['0', '00']:
            frequencias.append((contagem, num))
            
    frequencias_ordenadas = sorted(frequencias, key=lambda x: x[0])
    top_frios = [num for _, num in frequencias_ordenadas[:3]]
    top_quentes = [num for _, num in frequencias_ordenadas[-3:]][::-1] 
    return top_frios, top_quentes

# NOVO: Função para obter a sequência de Fibonacci
_fib_cache = {0: 0, 1: 1}
def get_fibonacci(n):
    if n in _fib_cache:
        return _fib_cache[n]
    _fib_cache[n] = get_fibonacci(n - 1) + get_fibonacci(n - 2)
    return _fib_cache[n]

# ====================================================================
# === FUNÇÕES DE GESTÃO DE ESTRATÉGIAS (REFATORADO) ==================
# ====================================================================

def _gerenciar_aposta(estado: Dict[str, Any], resultado_caiu: str, tipo_aposta: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """
    Função unificada para gerenciar a progressão (Vitória, Derrota).
    Retorna (mensagem_feedback, sinal_ativo)
    """
    global BANCA_ATUAL
    mensagem = ""
    sinal_ativo = None
    
    alvo = estado['APOSTA_EM']
    valor_aposta_unitaria = estado['VALOR']
    ganho_fator = estado['GANHO_FATOR']

    # Se não há aposta ativa, não faz nada
    if not alvo:
        return "", None

    # Verifica se o alvo é uma lista (para vizinhos) ou valor único
    vitoria = (isinstance(alvo, list) and resultado_caiu in alvo) or (resultado_caiu == alvo)
    
    if vitoria:
        # Para vizinhos, a aposta é distribuída, então o valor base é menor
        total_apostado = valor_aposta_unitaria * len(alvo) if isinstance(alvo, list) else valor_aposta_unitaria
        ganho = (valor_aposta_unitaria * ganho_fator) - (total_apostado - valor_aposta_unitaria)
        BANCA_ATUAL += ganho
        mensagem += f"✅ VITÓRIA ({tipo_aposta.upper()})! Ganhos: R$ {ganho:.2f}. Banca: R$ {BANCA_ATUAL:.2f}. RESET.\n"
        estado['VALOR'] = APOSTA_INICIAL
        estado['PERDAS'] = 0
        estado['APOSTA_EM'] = None if tipo_aposta != 'VIZINHOS' else []
        estado['FIB_INDEX'] = 2
        return mensagem, None
    else: # Derrota
        total_perdido = valor_aposta_unitaria * len(alvo) if isinstance(alvo, list) else valor_aposta_unitaria
        BANCA_ATUAL -= total_perdido
        estado['PERDAS'] += 1
        
        # Lógica de Progressão
        if SISTEMA_PROGRESSAO == 'FIBONACCI':
            estado['FIB_INDEX'] += 1
            fib_val = get_fibonacci(estado['FIB_INDEX'])
            estado['VALOR'] = fib_val * APOSTA_INICIAL
        else: # Martingale
            estado['VALOR'] *= FATOR_MARTINGALE
        
        termo_resultado = "ZERO" if resultado_caiu in ('G', 'G00') else "DERROTA"
        mensagem += f"❌ {termo_resultado} ({tipo_aposta.upper()}). Perda R$ {total_perdido:.2f}. Banca: R$ {BANCA_ATUAL:.2f}. Próxima aposta: R$ {estado['VALOR']:.2f}\n"

        if estado['PERDAS'] > MAX_PERDAS_CONSECUTIVAS:
            mensagem += f"🚨 ALERTA ({tipo_aposta.upper()}): Limite de perdas atingido. RESET.\n"
            estado['VALOR'] = APOSTA_INICIAL
            estado['PERDAS'] = 0
            estado['APOSTA_EM'] = None if tipo_aposta != 'VIZINHOS' else []
            estado['FIB_INDEX'] = 2
            return mensagem, None
        
        sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], tipo_aposta)

    return mensagem, sinal_ativo

def analisar_sequencia_cor(estado_key: str, cor_caiu: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    estado = ESTADOS[estado_key]
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, cor_caiu, estado_key)
    
    if sinal_ativo: return msg_martingale, sinal_ativo 
    
    if estado['APOSTA_EM'] is None and len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        cor_referencia = estado['HISTORICO'][0]
        if all(c == cor_referencia for c in estado['HISTORICO'][:estado['MIN_SEQUENCIA']]) and cor_referencia in ('R', 'B'):
            estado['APOSTA_EM'] = 'B' if cor_referencia == 'R' else 'R'
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], estado_key)
            msg_martingale += f"💰 SINAL (COR): Sequência de {estado['MIN_SEQUENCIA']}x detectada. Iniciar aposta.\n"
            return msg_martingale, sinal_ativo
            
    return msg_martingale, None 

def analisar_sequencia_tercos_colunas(estado_key: str, resultado_terco: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    estado = ESTADOS[estado_key]
    todos_tercos = ['D1', 'D2', 'D3'] if estado_key == 'DUZIA' else ['C1', 'C2', 'C3']
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, resultado_terco, estado_key)
    
    if sinal_ativo: return msg_martingale, sinal_ativo 

    if estado['APOSTA_EM'] is None and len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
        recentes = estado['HISTORICO'][:estado['MIN_SEQUENCIA']]
        tercos_ausentes = [t for t in todos_tercos if t not in recentes]
        
        if len(tercos_ausentes) == 1:
            terco_sinal = tercos_ausentes[0]
            estado['APOSTA_EM'] = terco_sinal
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], estado_key)
            termo_sinal = NOMENCLATURA.get(terco_sinal).split('(')[0].strip()
            msg_martingale += f"💰 SINAL ({estado_key.upper()}): {termo_sinal} em atraso. Iniciar aposta.\n"
            return msg_martingale, sinal_ativo
            
    return msg_martingale, None

# NOVO: Analisar estratégia de números frios
def analisar_numeros_frios(num_str: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    estado = ESTADOS['FRIO']
    msg, sinal_ativo = _gerenciar_aposta(estado, num_str, 'FRIO')

    if sinal_ativo: return msg, sinal_ativo

    if estado['APOSTA_EM'] is None and len(TODOS_GIROS_HISTORICO) > estado['MIN_ATRASO']:
        top_frios, _ = analisar_frequencia_numeros()
        numero_mais_frio = top_frios[0]
        
        # Verifica há quantos giros o número mais frio não sai
        try:
            ultimo_indice = TODOS_GIROS_HISTORICO[::-1].index(numero_mais_frio)
            if ultimo_indice >= estado['MIN_ATRASO']:
                 estado['APOSTA_EM'] = numero_mais_frio
                 sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], 'FRIO')
                 msg += f"💰 SINAL (FRIO): Número {numero_mais_frio} está a {ultimo_indice+1} giros sem sair. Iniciar aposta.\n"
                 return msg, sinal_ativo
        except ValueError: # Se o número nunca saiu
             estado['APOSTA_EM'] = numero_mais_frio
             sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], 'FRIO')
             msg += f"💰 SINAL (FRIO): Número {numero_mais_frio} nunca saiu. Iniciar aposta.\n"
             return msg, sinal_ativo

    return msg, None

# NOVO: Analisar estratégia de vizinhos
def get_vizinhos(numero_central_str: str, qtd_vizinhos: int) -> List[str]:
    try:
        idx_central = RODA_EUROPEIA.index(int(numero_central_str))
    except (ValueError, IndexError):
        return []
    
    vizinhos = []
    total_numeros = len(RODA_EUROPEIA)
    for i in range(idx_central - qtd_vizinhos, idx_central + qtd_vizinhos + 1):
        vizinhos.append(str(RODA_EUROPEIA[i % total_numeros]))
    return vizinhos

def analisar_vizinhos(num_str: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    if TIPO_ROLETA != 'EUROPEIA':
        return "Estratégia de vizinhos disponível apenas para Roleta Europeia.\n", None
    
    estado = ESTADOS['VIZINHOS']
    msg, sinal_ativo = _gerenciar_aposta(estado, num_str, 'VIZINHOS')

    if sinal_ativo: return msg, sinal_ativo

    if not estado['APOSTA_EM'] and len(TODOS_GIROS_HISTORICO) > 5:
        # Aposta nos vizinhos do último número que caiu (estratégia simples de "seguir o calor")
        vizinhos_aposta = get_vizinhos(num_str, estado['NUM_VIZINHOS'])
        if vizinhos_aposta:
            estado['APOSTA_EM'] = vizinhos_aposta
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], 'VIZINHOS')
            msg += f"💰 SINAL (VIZINHOS): Apostando no número {num_str} e seus vizinhos: {vizinhos_aposta}.\n"
            return msg, sinal_ativo

    return msg, None


def aplicar_estrategia_avancada(num_str: str):
    """
    Função principal que gerencia todas as estratégias e retorna a ordem de ação concisa.
    """
    valid_numbers = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_numbers.append('00')
    if num_str not in valid_numbers:
        return f"ERRO: Número inválido ('{num_str}')."

    resultado_mapa = get_tercos_colunas(num_str)
    
    global NUMEROS_RASTREAMENTO, TODOS_GIROS_HISTORICO
    NUMEROS_RASTREAMENTO[num_str] = NUMEROS_RASTREAMENTO.get(num_str, 0) + 1
    TODOS_GIROS_HISTORICO.append(num_str)
    
    ESTADOS['COR']['HISTORICO'].insert(0, resultado_mapa['COR'])
    ESTADOS['DUZIA']['HISTORICO'].insert(0, resultado_mapa['TERCO'])
    ESTADOS['COLUNA']['HISTORICO'].insert(0, resultado_mapa['COLUNA'])

    for key in ['COR', 'DUZIA', 'COLUNA']:
        ESTADOS[key]['HISTORICO'] = ESTADOS[key]['HISTORICO'][:10]

    output_result = f"➡️ CAIU: {num_str} - {NOMENCLATURA.get(resultado_mapa['COR'])} | DÚZIA: {NOMENCLATURA.get(resultado_mapa['TERCO'])} | COLUNA: {NOMENCLATURA.get(resultado_mapa['COLUNA'])}\n"
    output_result += "--------------------------------------\n"
    
    sinais_ativos = []
    
    msg_cor, sinal_cor = analisar_sequencia_cor('COR', resultado_mapa['COR'])
    if sinal_cor: sinais_ativos.append(sinal_cor)

    msg_duzia, sinal_duzia = analisar_sequencia_tercos_colunas('DUZIA', resultado_mapa['TERCO'])
    if sinal_duzia: sinais_ativos.append(sinal_duzia)

    msg_coluna, sinal_coluna = analisar_sequencia_tercos_colunas('COLUNA', resultado_mapa['COLUNA'])
    if sinal_coluna: sinais_ativos.append(sinal_coluna)
    
    msg_frio, sinal_frio = analisar_numeros_frios(num_str)
    if sinal_frio: sinais_ativos.append(sinal_frio)

    msg_vizinhos, sinal_vizinhos = analisar_vizinhos(num_str)
    if sinal_vizinhos: sinais_ativos.append(sinal_vizinhos)
        
    output_result += msg_cor + msg_duzia + msg_coluna + msg_frio + msg_vizinhos
    
    instrucoes_finais = [] 
    for aposta_em, valor, tipo in sinais_ativos:
        if tipo in ['DUZIA', 'COLUNA']:
            termo_alvo = NOMENCLATURA_ACAO.get(aposta_em, aposta_em)
            instrucoes_finais.append(f"R$ {valor:.2f} na {termo_alvo}") 
        elif tipo == 'COR':
            cor_mapa = NOMENCLATURA_ACAO.get(aposta_em)
            instrucoes_finais.append(f"R$ {valor:.2f} no {cor_mapa}")
        elif tipo == 'FRIO':
            instrucoes_finais.append(f"R$ {valor:.2f} no número {aposta_em}")
        elif tipo == 'VIZINHOS':
            # Valor é unitário, então multiplicamos pela quantidade de números
            total_aposta = valor * len(aposta_em)
            instrucoes_finais.append(f"R$ {total_aposta:.2f} nos vizinhos ({valor:.2f} em cada um de {aposta_em})")

    final_order = " e ".join(instrucoes_finais) if instrucoes_finais else "Aguarde Sinal"
        
    output_result += f"🎯 AÇÃO: {final_order}\n"
    output_result += "--------------------------------------"
    
    return output_result


def main():
    global BANCA_INICIAL, BANCA_ATUAL
    print("\n[Assistente de Roleta Ativo]")

    while True:
        try:
            banca_str = input("Qual o valor da sua banca inicial? R$ ").strip()
            BANCA_INICIAL = float(banca_str.replace(',', '.'))
            BANCA_ATUAL = BANCA_INICIAL
            print(f"Banca inicial de R$ {BANCA_ATUAL:.2f} definida.")
            break
        except ValueError:
            print("Valor inválido. Por favor, digite um número.")

    prompt_base = "Qual número caiu (0-36"
    if TIPO_ROLETA == 'AMERICANA': prompt_base += " ou 00"
    prompt_base += ")? Digite 'HISTORICO' ou 'SAIR': "

    while True:
        try:
            prompt = input(prompt_base).strip().upper()
            
            if prompt == "SAIR":
                lucro_prejuizo = BANCA_ATUAL - BANCA_INICIAL
                print("\nEncerrando Assistente.")
                print(f"Banca Final: R$ {BANCA_ATUAL:.2f} | Resultado da sessão: R$ {lucro_prejuizo:.2f}")
                break
            
            if prompt == "HISTORICO":
                print(f"Histórico Completo ({len(TODOS_GIROS_HISTORICO)} giros):")
                print(" -> ".join(TODOS_GIROS_HISTORICO))
                continue

            # Validação do número
            valid_numbers = [str(i) for i in range(37)]
            if TIPO_ROLETA == 'AMERICANA': valid_numbers.append('00')
            
            if prompt in valid_numbers:
                feedback = aplicar_estrategia_avancada(prompt)
                print(feedback)
            else:
                print("ERRO: Entrada inválida. Digite um número válido, 'HISTORICO' ou 'SAIR'.")
                
        except EOFError:
            print("\nEncerrando por fim de arquivo.")
            break
        except Exception as e:
            print(f"Ocorreu um erro inesperado: {e}")
            break

if __name__ == "__main__":
    main()
