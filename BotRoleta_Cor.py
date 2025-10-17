import sys
import math

# ====================================================================
# === 1. CONFIGURAÇÕES E PARÂMETROS GLOBAIS ==========================
# ====================================================================
APOSTA_INICIAL = 1.00 # Valor de aposta base
MAX_PERDAS_CONSECUTIVAS = 5 
FATOR_MARTINGALE = 2.0 # Fator de multiplicação da aposta após perda (2.0 = dobrar)

# Frequência esperada (1/37)
EXPECTATIVA_TEORICA_NUMERO = 1 / 37 
EXPECTATIVA_TEORICA_COR = 18 / 37
EXPECTATIVA_TEORICA_TERCO = 12 / 37

# Mapeamento e Definições de Grupos
CORES_NOMES = {'R': 'VERMELHO', 'B': 'PRETO', 'G': 'VERDE (ZERO)'}
TERCOS_MAPA = {
    'D1': "1ª DÚZIA (1-12)", 'D2': "2ª DÚZIA (13-24)", 'D3': "3ª DÚZIA (25-36)",
    'C1': "1ª COLUNA (1,4,7...)", 'C2': "2ª COLUNA (2,5,8...)", 'C3': "3ª COLUNA (3,6,9...)",
}

# Números por cor (para referência)
NUMEROS_VERMELHOS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
NUMEROS_PRETOS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

def get_tercos_colunas(num):
    """Mapeia o número para suas categorias principais."""
    if num == 0:
        return {'COR': 'G', 'TERCO': 'ZERO', 'COLUNA': 'ZERO'}
    
    if 1 <= num <= 12: d = 'D1'
    elif 13 <= num <= 24: d = 'D2'
    else: d = 'D3'
    
    if num % 3 == 1: c = 'C1'
    elif num % 3 == 2: c = 'C2'
    else: c = 'C3'
    
    cor = 'R' if num in NUMEROS_VERMELHOS else 'B'
    
    return {'COR': cor, 'TERCO': d, 'COLUNA': c}


# ====================================================================
# === 2. MÓDULO DE DADOS E ESTADO (Rastreamento Cirúrgico) ============
# ====================================================================

# Inicializa todos os 37 números (0-36) com contagem 0
NUMEROS_RASTREAMENTO = {i: 0 for i in range(37)} 
TOTAL_RODADAS = 0

# Estado para Martingale e Histórico
ESTADOS = {
    'COR': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0, 'MIN_SEQUENCIA': 3}, 
    'DUZIA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0},
    'COLUNA': {'HISTORICO': [], 'APOSTA_EM': None, 'VALOR': APOSTA_INICIAL, 'PERDAS': 0},
}

def registrar_resultado(num):
    """Atualiza todas as variáveis de estado com o novo resultado."""
    global TOTAL_RODADAS
    TOTAL_RODADAS += 1
    
    resultado_mapa = get_tercos_colunas(num)
    
    # Rastreamento de Frequência (Cold/Hot)
    NUMEROS_RASTREAMENTO[num] += 1
    
    # Atualiza Históricos
    ESTADOS['COR']['HISTORICO'].insert(0, resultado_mapa['COR'])
    ESTADOS['DUZIA']['HISTORICO'].insert(0, resultado_mapa['TERCO'])
    ESTADOS['COLUNA']['HISTORICO'].insert(0, resultado_mapa['COLUNA'])

    # Mantém o limite de histórico (30 rodadas para análise)
    for key in ESTADOS:
        ESTADOS[key]['HISTORICO'] = ESTADOS[key]['HISTORICO'][:30]
    
    return resultado_mapa

# ====================================================================
# === 3. MÓDULO ESTATÍSTICO (Análise de Desvio e Probabilidade) ======
# ====================================================================

def calcular_desvio_frequencia(contagem_real):
    """Calcula o desvio em relação à expectativa teórica em %."""
    if TOTAL_RODADAS == 0:
        return 0
    
    expectativa_num = TOTAL_RODADAS * EXPECTATIVA_TEORICA_NUMERO
    desvio = ((contagem_real - expectativa_num) / expectativa_num) * 100 if expectativa_num > 0 else 0
    return round(desvio, 2)


def analisar_frequencia_e_desvio():
    """Identifica os desvios de frequência para todos os grupos."""
    if TOTAL_RODADAS < 30:
        return {} # Não faz análise estatística sem histórico

    analise_grupos = {}
    
    # Analisa Terços (Dúzias e Colunas)
    for tipo_terco in ['DUZIA', 'COLUNA']:
        tercos = ['D1', 'D2', 'D3'] if tipo_terco == 'DUZIA' else ['C1', 'C2', 'C3']
        expectativa_terco = TOTAL_RODADAS * EXPECTATIVA_TEORICA_TERCO
        
        for terco in tercos:
            contagem = ESTADOS[tipo_terco]['HISTORICO'].count(terco)
            desvio = ((contagem - expectativa_terco) / expectativa_terco) * 100 if expectativa_terco > 0 else 0
            analise_grupos[terco] = {'contagem': contagem, 'desvio': round(desvio, 2)}

    # Analisa Cores
    expectativa_cor = TOTAL_RODADAS * EXPECTATIVA_TEORICA_COR
    for cor in ['R', 'B']:
        contagem = ESTADOS['COR']['HISTORICO'].count(cor)
        desvio = ((contagem - expectativa_cor) / expectativa_cor) * 100 if expectativa_cor > 0 else 0
        analise_grupos[cor] = {'contagem': contagem, 'desvio': round(desvio, 2)}
        
    return analise_grupos

def analisar_numeros_frios_quentes():
    """Identifica os 3 números mais frios (cold) e 3 mais quentes (hot) com desvio."""
    frequencias = [(contagem, num) for num, contagem in NUMEROS_RASTREAMENTO.items()]
    frequencias_sem_zero = sorted([f for f in frequencias if f[1] != 0], key=lambda x: x[0])
    
    top_frios = [{'num': num, 'desvio': calcular_desvio_frequencia(contagem)} 
                 for contagem, num in frequencias_sem_zero[:3]]
    
    top_quentes = [{'num': num, 'desvio': calcular_desvio_frequencia(contagem)} 
                   for contagem, num in frequencias_sem_zero[-3:]][::-1]

    return top_frios, top_quentes

# ====================================================================
# === 4. MÓDULO DE ESTRATÉGIAS (Identificação de Vantagem) ===========
# ====================================================================

def gerenciar_martingale(estado_key, resultado_caiu, aposta_certa):
    """Gerencia a sequência de Martingale para um estado (Cor/Duzia/Coluna)."""
    estado = ESTADOS[estado_key]
    mensagem = ""
    
    if estado['APOSTA_EM']:
        payout = 3 if estado_key in ['DUZIA', 'COLUNA'] else 2 # Terço 3x, Cor 2x
        
        if aposta_certa:
            ganho = estado['VALOR'] * payout
            mensagem += f"✅ {estado_key.upper()}: VITÓRIA! Ganhos de R$ {ganho:.2f}. RESET.\n"
            
            estado['VALOR'] = APOSTA_INICIAL
            estado['PERDAS'] = 0
            estado['APOSTA_EM'] = None 
            
        elif resultado_caiu == 'G': # Zero (Verde)
            mensagem += f"🟡 {estado_key.upper()}: ZERO CAIU. Perda. Dobrando aposta.\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
            
        else:
            # DERROTA
            mensagem += f"❌ {estado_key.upper()}: DERROTA. Caiu {resultado_caiu}. Dobrando aposta.\n"
            estado['PERDAS'] += 1
            estado['VALOR'] *= FATOR_MARTINGALE
            
        # Verifica o limite de perdas
        if estado['PERDAS'] > MAX_PERDAS_CONSECUTIVAS:
            mensagem += f"🚨 {estado_key.upper()}: LIMITE de perdas atingido. Voltando à base.\n"
            estado['VALOR'] = APOSTA_INICIAL
            estado['PERDAS'] = 0
            estado['APOSTA_EM'] = None
        
        if estado['APOSTA_EM']:
            mensagem += f"➡️ PRÓXIMA AÇÃO: Aposte R$ {estado['VALOR']:.2f} no {TERCOS_MAPA.get(estado['APOSTA_EM'], CORES_NOMES.get(estado['APOSTA_EM']))}.\n"
        
    return mensagem


def detectar_sinal_atraso(estado_key):
    """Detecta aposta em atraso (2/3) ou sequência de Cor (3x)."""
    estado = ESTADOS[estado_key]
    sinal = None
    
    # Se já houver aposta pendente (Martingale em andamento), não cria novo sinal
    if estado['APOSTA_EM']:
        return sinal

    if estado_key in ['DUZIA', 'COLUNA']:
        # Estratégia 2/3 (DUZIA/COLUNA)
        tercos = ['D1', 'D2', 'D3'] if estado_key == 'DUZIA' else ['C1', 'C2', 'C3']
        
        if len(estado['HISTORICO']) >= 2:
            # Filtra 'ZERO' do histórico para não atrapalhar o cálculo do atraso 2/3
            recentes_validos = [r for r in estado['HISTORICO'][:2] if r != 'ZERO']
            tercos_recentes_set = set(recentes_validos)

            # Só detecta o atraso se houver pelo menos 2 resultados válidos e eles forem diferentes
            if len(recentes_validos) >= 2 and len(tercos_recentes_set) >= 2:
                terco_ausente = [t for t in tercos if t not in tercos_recentes_set]
            
                if len(terco_ausente) == 1:
                    terco_sinal = terco_ausente[0]
                    estado['APOSTA_EM'] = terco_sinal
                    sinal = (terco_sinal, estado['VALOR'], estado_key, 'ATRASO 2/3')
                
    elif estado_key == 'COR':
        # Estratégia de Sequência (COR)
        if len(estado['HISTORICO']) >= estado.get('MIN_SEQUENCIA', 3): # Usando .get com fallback
            sequencia = 0
            cor_referencia = estado['HISTORICO'][0]
            
            for cor_hist in estado['HISTORICO']:
                if cor_hist == cor_referencia:
                    sequencia += 1
                else:
                    break
            
            if sequencia >= estado.get('MIN_SEQUENCIA', 3) and cor_referencia in ('R', 'B'):
                cor_apostada = 'B' if cor_referencia == 'R' else 'R' 
                estado['APOSTA_EM'] = cor_apostada
                sinal = (cor_apostada, estado['VALOR'], estado_key, 'SEQUÊNCIA 3X')
                
    return sinal


# ====================================================================
# === 5. DECISÃO CENTRAL (ENGINE) ====================================
# ====================================================================

def processar_rodada(num):
    """Processa o resultado, atualiza estados e gera recomendações."""
    global TOTAL_RODADAS
    
    # 1. Registrar o Resultado
    resultado_mapa = registrar_resultado(num)
    
    mensagem_geral = f"=========================================================\n"
    mensagem_geral += f"➡️ RESULTADO: {num} (Rodada #{TOTAL_RODADAS}) - {CORES_NOMES.get(resultado_mapa['COR'])} | DÚZIA: {TERCOS_MAPA.get(resultado_mapa['TERCO'])} | COLUNA: {TERCOS_MAPA.get(resultado_mapa['COLUNA'])}\n"
    mensagem_geral += f"=========================================================\n"
    
    # 2. Gerenciar Martingale e Perdas
    sinais_ativos = []
    log_martingale = ""
    
    for key, estado in ESTADOS.items():
        if estado['APOSTA_EM']:
            # CORREÇÃO: Mapear 'DUZIA' para 'TERCO' e 'COLUNA' para 'COLUNA' no resultado_mapa
            resultado_categoria = None
            if key == 'COR':
                resultado_categoria = resultado_mapa['COR']
            elif key == 'DUZIA':
                resultado_categoria = resultado_mapa['TERCO']
            elif key == 'COLUNA':
                resultado_categoria = resultado_mapa['COLUNA']
                
            aposta_certa = (estado['APOSTA_EM'] == resultado_categoria)
            log_martingale += gerenciar_martingale(key, resultado_mapa['COR'], aposta_certa)
            
            if estado['APOSTA_EM']: # Se a aposta ainda está ativa (Martingale continua)
                sinais_ativos.append((estado['APOSTA_EM'], estado['VALOR'], key, 'MARTINGALE'))
        
    mensagem_geral += "\n--- GERENCIAMENTO DE MARTINGALE ---\n"
    mensagem_geral += log_martingale if log_martingale else "Nenhuma aposta pendente para gerenciar.\n"
    
    # 3. Detectar Novos Sinais
    log_sinais = ""
    if not sinais_ativos:
        for key in ESTADOS:
            sinal = detectar_sinal_atraso(key) # Não precisa passar o resultado, ele usa o HISTORICO
            if sinal:
                sinais_ativos.append(sinal)
                log_sinais += f"💰 SINAL DETECTADO ({sinal[3]}): Aposte R$ {sinal[1]:.2f} no {TERCOS_MAPA.get(sinal[0], CORES_NOMES.get(sinal[0]))}.\n"
    
    mensagem_geral += "\n--- DETECÇÃO DE SINAIS ---\n"
    mensagem_geral += log_sinais if log_sinais else "Nenhum novo sinal de atraso encontrado.\n"
    
    # 4. Análise Estatística e Recomendações Finais
    analise_grupos = analisar_frequencia_e_desvio()
    top_frios, top_quentes = analisar_numeros_frios_quentes()
    
    mensagem_geral += "\n--- ANÁLISE PROFISSIONAL ---\n"
    mensagem_geral += f"TOTAL DE RODADAS: {TOTAL_RODADAS}\n"
    mensagem_geral += f"❄️ NÚMEROS FRIOS (Para Cobertura): {top_frios}\n"
    mensagem_geral += f"🔥 NÚMEROS QUENTES: {top_quentes}\n"
    
    mensagem_geral += "\n* DESVIO DE FREQUÊNCIA (Em %): \n"
    for grupo, dados in analise_grupos.items():
        if grupo in TERCOS_MAPA:
            nome_grupo = TERCOS_MAPA[grupo]
        elif grupo in CORES_NOMES:
            nome_grupo = CORES_NOMES[grupo]
        else:
            nome_grupo = grupo
            
        mensagem_geral += f"  > {nome_grupo} ({dados['contagem']}x): {dados['desvio']}% {'(OPORTUNIDADE DE ATRASO)' if dados['desvio'] < -20 else ''}\n"
        
    mensagem_geral += "\n--- RECOMENDAÇÃO FINAL ---\n"
    
    if sinais_ativos:
        # Prioriza Terço/Coluna por ter maior payout (3x)
        prioridade = next((s for s in sinais_ativos if s[2] in ['DUZIA', 'COLUNA']), sinais_ativos[0])
        aposta_em, valor, tipo, tecnica = prioridade
        
        nome_aposta = TERCOS_MAPA.get(aposta_em, CORES_NOMES.get(aposta_em))
        
        mensagem_geral += f"🎯 JOGADA DE VALOR: Aposte R$ {valor:.2f} no {nome_aposta} ({tipo.upper()}).\n"
        mensagem_geral += f"  > TÉCNICA: {tecnica} \n"
        
        # Sugestão de Cobertura nos Frios
        if tipo in ['DUZIA', 'COLUNA']:
            limites_duzia = {'D1': (1, 12), 'D2': (13, 24), 'D3': (25, 36)}
            min_num, max_num = limites_duzia.get(aposta_em, (0, 36))
            
            frios_no_terco = [f['num'] for f in top_frios if min_num <= f['num'] <= max_num]
            
            if frios_no_terco:
                mensagem_geral += f"  > COBERTURA CIRÚRGICA: Sugira R$ {APOSTA_INICIAL/2:.2f} nos Frios do Terço: {frios_no_terco}\n"
                
    else:
        mensagem_geral += "🔄 AGUARDAR: Oportunidades estatísticas ausentes. Não há edge no momento.\n"

    return mensagem_geral

def main():
    print("=========================================================")
    print("==== ASSISTENTE DE ANÁLISE PROFISSIONAL DE ROLETA =======")
    print("=========================================================")
    print("Módulo de Análise Estatística, Sequência e Atraso (Entrada Manual).")
    print("Comandos: Digite o NÚMERO que caiu (0-36) ou SAIR.\n")

    while True:
        try:
            prompt = input("Qual número caiu na roleta (0-36) ou SAIR? ").strip().upper()
            
            if prompt == "SAIR":
                print("\nEncerrando Assistente. Tenha um ótimo dia!")
                break
            
            try:
                num = int(prompt)
                if 0 <= num <= 36:
                    feedback = processar_rodada(num)
                    print(feedback)
                else:
                    print("ERRO: Número fora do range (0 a 36).")
            except ValueError:
                print("ERRO: Entrada inválida. Digite um número de 0 a 36.")

        except EOFError:
            print("\nEncerrando por fim de arquivo.")
            break
        except Exception as e:
            print(f"Ocorreu um erro: {e}")
            break

if __name__ == "__main__":
    main()
