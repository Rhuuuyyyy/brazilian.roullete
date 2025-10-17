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

# Mapeamento Unificado de Nomes/Termos
NOMENCLATURA = {
    'R': 'VERMELHO', 'B': 'PRETO', 'G': 'VERDE (ZERO)', 'G00': 'VERDE (ZERO DUPLO)',
    'D1': "1ª DÚZIA (1-12)", 'D2': "2ª DÚZIA (13-24)", 'D3': "3ª DÚZIA (25-36)",
    'C1': "1ª COLUNA (1,4,7...)", 'C2': "2ª COLUNA (2,5,8...)", 'C3': "3ª COLUNA (3,6,9...)",
    'ZERO': 'ZERO (0)', 'ZEROD': 'ZERO DUPLO (00)', 'PAR': 'PAR', 'IMPAR': 'ÍMPAR'
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
            mensagem += f"✅ VITÓRIA no {NOMENCLATURA.get(alvo)}. Ganhos de R$ {ganho:.2f}. RESET.\n"
            estado['VALOR'] = APOSTA_INICIAL
            estado['PERDAS'] = 0
            estado['APOSTA_EM'] = None
            return mensagem, None
        
        # 2. VERIFICAÇÃO DE ZERO (PERDA e DOBRA)
        elif resultado_caiu in ('G', 'G00'):
            mensagem += "🟡 ZERO (VERDE) CAIU. Considerado PERDA. Risco de 0/00.\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
            
        # 3. VERIFICAÇÃO DE DERROTA (PERDA e DOBRA)
        else:
            termo_resultado = NOMENCLATURA.get(resultado_caiu, resultado_caiu)
            mensagem += f"❌ DERROTA! Caiu {termo_resultado}. Próximo Fator.\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
        
        # 4. TRATAMENTO APÓS PERDA (Continuar Aposta no Alvo)
        if estado['APOSTA_EM'] and estado['PERDAS'] > 0:
            if estado['PERDAS'] > MAX_PERDAS_CONSECUTIVAS:
                mensagem += f"🚨 ALERTA: Limite de perdas atingido ({MAX_PERDAS_CONSECUTIVAS}x). Voltando à aposta inicial.\n"
                estado['VALOR'] = APOSTA_INICIAL
                estado['PERDAS'] = 0
                estado['APOSTA_EM'] = None
                return mensagem, None
            
            # Recomenda a aposta para recuperar a perda
            probabilidade_real = (18 / NUM_SLOTS) if tipo_aposta == 'COR' else (12 / NUM_SLOTS)
            termo_alvo = NOMENCLATURA.get(estado['APOSTA_EM'], estado['APOSTA_EM'])
            mensagem += f"➡️ PRÓXIMA AÇÃO: Aposte R$ {estado['VALOR']:.2f} no {termo_alvo}.\n"
            mensagem += f"   (Probabilidade real de vitória: {probabilidade_real * 100:.2f}%)"
            sinal_ativo = (estado['APOSTA_EM'], estado['VALOR'], tipo_aposta)

    return mensagem, sinal_ativo

def analisar_sequencia_cor(estado_key: str, cor_caiu: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """Analisa a sequência simples (Cor) e gera sinal Martingale (3x)."""
    estado = ESTADOS[estado_key]
    mensagem = f"\n[Análise {estado_key.upper()}] Histórico: {formatar_historico(estado['HISTORICO'][:5])}...\n"
    
    # 1. GERENCIAR MARTINGALE PENDENTE
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, cor_caiu, estado_key)
    mensagem += msg_martingale
    
    if sinal_ativo:
        return mensagem, sinal_ativo 
    
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
            probabilidade_real = 18 / NUM_SLOTS
            
            mensagem += f"💰 SINAL DETECTADO: {sequencia}x {NOMENCLATURA.get(cor_referencia)} consecutivos.\n"
            mensagem += f"🎯 APOSTE AGORA: R$ {estado['VALOR']:.2f} no {NOMENCLATURA.get(estado['APOSTA_EM'])}.\n"
            mensagem += f"   (Probabilidade real de vitória: {probabilidade_real * 100:.2f}% - A sequência não altera a probabilidade!)\n"
            return mensagem, (estado['APOSTA_EM'], estado['VALOR'], estado_key)
            
        else:
            mensagem += "😴 Aguardando sinal de Cor.\n"
            
    elif estado['APOSTA_EM'] is None:
        mensagem += f"📚 Aguardando histórico suficiente ({estado['MIN_SEQUENCIA']}+) de Cor.\n"
        
    return mensagem, None 

def analisar_sequencia_tercos_colunas(estado_key: str, resultado_terco: str) -> Tuple[str, Tuple[Any, float, str] | None]:
    """Analisa a sequência de Terços (D1/D2/D3) ou Colunas (C1/C2/C3) - Estratégia de Atraso (2/3)."""
    
    estado = ESTADOS[estado_key]
    todos_tercos = ['D1', 'D2', 'D3'] if estado_key == 'DUZIA' else ['C1', 'C2', 'C3']
    mensagem = f"\n[Análise {estado_key.upper()}] Histórico: {formatar_historico(estado['HISTORICO'][:5])}...\n"

    # 1. GERENCIAR MARTINGALE PENDENTE
    msg_martingale, sinal_ativo = _gerenciar_aposta(estado, resultado_terco, estado_key)
    mensagem += msg_martingale
    
    if sinal_ativo:
        return mensagem, sinal_ativo 

    # 2. DEFINIÇÃO DO PRÓXIMO SINAL (Aposta no Terço/Coluna em Atraso)
    if estado['APOSTA_EM'] is None:
        
        if len(estado['HISTORICO']) >= estado['MIN_SEQUENCIA']:
            
            recentes = estado['HISTORICO'][:estado['MIN_SEQUENCIA']]
            
            # Contagem dos terços/colunas que caíram recentemente (ignorando Zero)
            contagem_recente = Counter(t for t in recentes if t in todos_tercos)

            # Terços que faltaram nos últimos N resultados
            tercos_ausentes = [t for t in todos_tercos if t not in contagem_recente]
            
            # Sinal: Se APENAS UM terço/coluna está ausente nos últimos N resultados,
            # ou seja, 2 dos 3 terços caíram.
            if len(tercos_ausentes) == 1:
                terco_sinal = tercos_ausentes[0]
                estado['APOSTA_EM'] = terco_sinal
                probabilidade_real = 12 / NUM_SLOTS
                
                termo_sinal = NOMENCLATURA.get(terco_sinal)
                mensagem += f"💰 SINAL DETECTADO: 2 dos 3 Terços/Colunas caíram ({list(contagem_recente.keys())}). {termo_sinal} está em atraso.\n"
                mensagem += f"🎯 APOSTE AGORA: R$ {estado['VALOR']:.2f} no {termo_sinal}.\n"
                mensagem += f"   (Probabilidade real de vitória: {probabilidade_real * 100:.2f}% - A sequência não altera a probabilidade!)\n"
                
                return mensagem, (estado['APOSTA_EM'], estado['VALOR'], estado_key)
            else:
                mensagem += "😴 Aguardando sinal de Terço/Coluna em atraso.\n"

        elif estado['APOSTA_EM'] is None:
            mensagem += f"📚 Aguardando {estado['MIN_SEQUENCIA']}+ resultados para análise de Terços/Colunas.\n"
            
    return mensagem, None


def aplicar_estrategia_avancada(num_str: str):
    """
    Função principal que gerencia todas as estratégias simultaneamente e consolida o feedback.
    """
    # Validação de entrada
    valid_numbers = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_numbers.append('00')

    if num_str not in valid_numbers:
        return f"ERRO: Número inválido ('{num_str}'). Digite um número de 0 a 36 ou '00' (se for americana)."

    resultado_mapa = get_tercos_colunas(num_str)
    
    # 1. Rastreamento e Registro
    global NUMEROS_RASTREAMENTO
    global TODOS_GIROS_HISTORICO
    
    # Atualiza o rastreamento de frequência
    NUMEROS_RASTREAMENTO[num_str] = NUMEROS_RASTREAMENTO.get(num_str, 0) + 1
    TODOS_GIROS_HISTORICO.append(num_str)
    
    # Atualiza Históricos de Estado
    ESTADOS['COR']['HISTORICO'].insert(0, resultado_mapa['COR'])
    ESTADOS['DUZIA']['HISTORICO'].insert(0, resultado_mapa['TERCO'])
    ESTADOS['COLUNA']['HISTORICO'].insert(0, resultado_mapa['COLUNA'])

    for key in ESTADOS:
        ESTADOS[key]['HISTORICO'] = ESTADOS[key]['HISTORICO'][:10]

    mensagem_geral = f"=========================================================\n"
    mensagem_geral += f"➡️ RESULTADO: {num_str} - {NOMENCLATURA.get(resultado_mapa['COR'])} | DÚZIA: {NOMENCLATURA.get(resultado_mapa['TERCO'])} | COLUNA: {NOMENCLATURA.get(resultado_mapa['COLUNA'])}\n"
    mensagem_geral += f"=========================================================\n"

    sinais_ativos = []

    # 2. Analisar e gerenciar estados
    msg_cor, sinal_cor = analisar_sequencia_cor('COR', resultado_mapa['COR'])
    mensagem_geral += msg_cor
    if sinal_cor:
        sinais_ativos.append(sinal_cor)

    msg_duzia, sinal_duzia = analisar_sequencia_tercos_colunas('DUZIA', resultado_mapa['TERCO'])
    mensagem_geral += msg_duzia
    if sinal_duzia:
        sinais_ativos.append(sinal_duzia)

    msg_coluna, sinal_coluna = analisar_sequencia_tercos_colunas('COLUNA', resultado_mapa['COLUNA'])
    mensagem_geral += msg_coluna
    if sinal_coluna:
        sinais_ativos.append(sinal_coluna)
        
    # 3. CONSOLIDAR A AÇÃO MAIS IMPORTANTE E GERAR INSTRUÇÃO FINAL
    top_frios, top_quentes = analisar_frequencia_numeros()
    
    mensagem_geral += "\n--- CONSOLIDAÇÃO DE AÇÕES ---\n"
    mensagem_geral += f"❄️ NÚMEROS FRIOS (Baixa Frequência): {top_frios}\n"
    mensagem_geral += f"🔥 NÚMEROS QUENTES (Alta Frequência): {top_quentes}\n"
    mensagem_geral += "--------------------------------------\n"

    instrucoes_finais = [] # Lista para construir a ORDEM FINAL detalhada
    sinais_2_por_1 = [s for s in sinais_ativos if s[2] in ['DUZIA', 'COLUNA']]
    sinais_1_por_1 = [s for s in sinais_ativos if s[2] == 'COR']
    
    # 1. Processar todos os sinais de Dúzia/Coluna (2:1)
    for aposta_em, valor, tipo in sinais_2_por_1:
        estado = ESTADOS[tipo]
        terco_mapa = NOMENCLATURA.get(aposta_em, aposta_em)
        delay = estado['PERDAS'] # Número de perdas consecutivas (atraso)

        # Instrução Principal Martingale (Dúzia/Coluna) - MAIS ESPECÍFICA
        instrucoes_finais.append(f"MARTINGALE (2:1): R$ {estado['VALOR']:.2f} NO {terco_mapa} ({tipo.upper()}) | ATRASO: {delay}x")
        mensagem_geral += f"🔥 Ação Ativa (x3): R$ {estado['VALOR']:.2f} no {terco_mapa} ({tipo.upper()}) | Fator Martingale: {delay+1}x\n"
        
        # Sugestão de Cobertura Fria (Apenas se for Dúzia e houver atraso real)
        if tipo == 'DUZIA' and delay > 0:
            limites_duzia = {'D1': (1, 12), 'D2': (13, 24), 'D3': (25, 36)}
            min_num, max_num = limites_duzia[aposta_em]
            # Filtra os números frios que caem no terço sendo apostado
            frios_no_terco = [n for n in top_frios if isinstance(n, int) and min_num <= n <= max_num]
            
            if frios_no_terco:
                instrucoes_finais.append(f"COBERTURA PLENO: R$ {APOSTA_INICIAL:.2f} NOS FRIOS {frios_no_terco}")
                mensagem_geral += f"  > Sugestão: Cobertura (x36) nos frios {frios_no_terco}\n"

    # 2. Processar todos os sinais de Cor (1:1)
    for aposta_em, valor, tipo in sinais_1_por_1:
        estado = ESTADOS[tipo]
        cor_mapa = NOMENCLATURA.get(estado['APOSTA_EM'])
        delay = estado['PERDAS'] # Número de perdas consecutivas (atraso)

        instrucoes_finais.append(f"MARTINGALE (1:1): R$ {estado['VALOR']:.2f} NO {cor_mapa} (COR) | ATRASO: {delay}x")
        mensagem_geral += f"🟡 Ação Ativa (x2): R$ {estado['VALOR']:.2f} no {cor_mapa} (COR) | Fator Martingale: {delay+1}x\n"
    
    # 3. Se não houver Martingale, a instrução é AGUARDE
    if not instrucoes_finais:
        instrucoes_finais.append("AGUARDE O PRÓXIMO SINAL")
        mensagem_geral += "🔄 Não há sinal ativo de Martingale no momento.\n"
        
        # Sugerir monitoramento de frios
        estatisticas = calcular_estatisticas_basicas()
        if estatisticas['total_giros'] > 10 and top_frios:
              instrucoes_finais.append(f"MONITORE: Pleno mínimo (R$ {APOSTA_INICIAL:.2f}) nos frios {top_frios}")
              mensagem_geral += f"   > Sugestão: Monitore os frios {top_frios} com aposta mínima de R$ {APOSTA_INICIAL:.2f}.\n"


    # Final Order String generation
    final_order = " | ".join(instrucoes_finais)

    # 4. Análise Matemática Profissional
    estatisticas = calcular_estatisticas_basicas()
    house_edge_percent = estatisticas['house_edge_global'] * 100
    
    mensagem_geral += "\n--- ANÁLISE DE ALTO NÍVEL (MATEMÁTICA) ---\n"
    mensagem_geral += f"⚠️ RISCO: Expectativa Negativa: {-house_edge_percent:.2f}% (House Edge)\n"
    
    if estatisticas['total_giros'] > 0:
        # AVISO: A estratégia codifica a Falácia do Jogador. A EV é SEMPRE negativa!
        mensagem_geral += f"Giros Totais: {estatisticas['total_giros']}\n"
        mensagem_geral += f"Desvio Zero (E): {estatisticas['desvio_zero'] * 100:.2f}% (Se +, Zero(s) caiu mais que o esperado)\n"
        mensagem_geral += f"Variância Amostral (χ²): {estatisticas['chi2']:.2f} (Medida de desvio de uniformidade)\n"
    
    mensagem_geral += "--------------------------------------\n"
    
    # 5. ORDEM FINAL OBRIGATÓRIA (Foco da Saída)
    mensagem_geral += f"=========================================================\n"
    mensagem_geral += f"🎯 ORDEM FINAL (AÇÃO URGENTE): {final_order}\n"
    mensagem_geral += f"========================================================="

    return mensagem_geral


def main():
    print("=========================================================")
    print("==== ASSISTENTE DE ESTRATÉGIAS DE ROLETA (INTERATIVO) =====")
    print("=========================================================")
    print(f"ATENÇÃO: Roleta configurada como {TIPO_ROLETA} (Slots: {NUM_SLOTS})")
    
    # Aviso de Risco Crítico
    print("\n⚠️ ALERTA DE RISCO: TODAS as estratégias (Martingale/Atraso) na roleta têm EXPECTATIVA DE VALOR NEGATIVA devido ao House Edge. Use com responsabilidade.")
    
    print("\nComandos: Digite o NÚMERO que caiu (0-36, ou 00 se for americana) ou SAIR.\n")

    valid_input_prompt = "Qual número caiu na roleta (0-36"
    if TIPO_ROLETA == 'AMERICANA':
        valid_input_prompt += " ou 00"
    valid_input_prompt += ") ou SAIR? "

    while True:
        try:
            prompt = input(valid_input_prompt).strip().upper()
            
            if prompt == "SAIR":
                print("\nEncerrando Assistente. Tenha um ótimo dia!")
                break
            
            # Validação para '00' na roleta americana
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
