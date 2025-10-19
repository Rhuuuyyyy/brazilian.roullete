import math
import re
import time
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional

# --- Novas Bibliotecas para OCR e Automação ---
import mss
import pytesseract
from PIL import Image
import keyboard
import pyautogui

# ====================================================================
# === CONFIGURAÇÃO DO TESSERACT (LEIA O COMENTÁRIO!) ==================
# ====================================================================

# 1. Esta linha é crucial.
# 2. Verifique o caminho exato onde instalou o Tesseract-OCR.
# 3. O caminho padrão é 'C:\Program Files\Tesseract-OCR\tesseract.exe'.
# 4. Se o seu for diferente, ATUALIZE A LINHA ABAIXO.
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ====================================================================
# === PEÇA 1: O MOTOR DA ROLETA (CÓDIGO 1, CORRIGIDO) =================
# ====================================================================

# --- Configurações de Aposta e Risco ---
APOSTA_INICIAL_BASE = 0.50
FATOR_MARTINGALE = 2.0
MAX_APOSTA_VALOR = 2.00
MAX_PERDAS_CONSECUTIVAS = 4
LA_PARTAGE_ATIVO = True

# --- Configurações das Estratégias ---
MIN_SEQUENCIA_COR_ETC = 3
MIN_SEQUENCIA_TERCO_COLUNA = 2
MIN_ATRASO_NUMERO_FRIO = 37

# --- Configuração da Roleta ---
TIPO_ROLETA = 'EUROPEIA'

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

class RoletaHelper:
    """Classe com métodos estáticos de apoio, sem estado."""
    VERMELHOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

    @staticmethod
    def get_mapeamento_numero(num_str: str) -> Dict[str, str]:
        if num_str in ('0', '00'):
            return {'COR': 'G', 'DUZIA': 'ZERO', 'COLUNA': 'ZERO', 'PARIDADE': 'ZERO', 'ALTURA': 'ZERO', 'NUMERO': num_str}

        try:
            n = int(num_str)
            if not (1 <= n <= 36): return {}
        except (ValueError, TypeError):
            return {}

        cor = 'R' if n in RoletaHelper.VERMELHOS else 'B'
        duzia = 'D1' if 1 <= n <= 12 else ('D2' if 13 <= n <= 24 else 'D3')
        coluna = 'C1' if n % 3 == 1 else ('C2' if n % 3 == 2 else 'C3')
        paridade = 'PAR' if n % 2 == 0 else 'IMPAR'
        altura = 'BAIXO' if 1 <= n <= 18 else 'ALTO'

        return {'COR': cor, 'DUZIA': duzia, 'COLUNA': coluna, 'PARIDADE': paridade, 'ALTURA': altura, 'NUMERO': num_str}

class Banca:
    """Encapsula o gerenciamento do saldo."""
    def __init__(self, valor_inicial: float):
        self.valor_inicial = valor_inicial
        self.valor_atual = valor_inicial

    def creditar_lucro(self, valor: float):
        self.valor_atual += valor

    def debitar_aposta(self, valor: float):
        self.valor_atual -= valor

    def get_saldo(self) -> float:
        return self.valor_atual

class Estrategia(ABC):
    """Classe base abstrata para todas as estratégias de apostas."""
    def __init__(self, nome: str, config: Dict[str, Any]):
        self.nome = nome
        self.config = config
        self.historico: List[str] = []
        self.aposta_em: Optional[str] = None
        self.valor = config.get('APOSTA_INICIAL_BASE', APOSTA_INICIAL_BASE)
        self.perdas = 0
        self.ativo = False

    def reset(self):
        self.valor = self.config.get('APOSTA_INICIAL_BASE', APOSTA_INICIAL_BASE)
        self.perdas = 0
        self.aposta_em = None

    def atualizar_historico(self, resultado_categoria: str):
        self.historico.insert(0, resultado_categoria)
        self.historico = self.historico[:15]

    def _gerenciar_aposta_ativa(self, resultado_categoria: str, banca: Banca) -> Tuple[str, Optional[Tuple]]:
        if not self.aposta_em:
            return "", None

        mensagem = ""
        sinal_ativo = None
        valor_aposta_atual = self.valor

        if resultado_categoria == self.aposta_em:
            lucro = valor_aposta_atual * (self.config['GANHO_FATOR'] - 1)
            banca.creditar_lucro(lucro)
            mensagem += f"✅ VITÓRIA ({self.nome})! Lucro: R$ {lucro:.2f}. RESET.\n"
            self.reset()
            return mensagem, None

        is_zero = resultado_categoria in ('G', 'ZERO')
        if is_zero and self.config['TIPO'] == '1:1' and LA_PARTAGE_ATIVO and TIPO_ROLETA == 'EUROPEIA':
            perda = valor_aposta_atual / 2
            banca.debitar_aposta(perda)
            mensagem += f"🟡 LA PARTAGE ({self.nome}): Zero caiu. Meia perda (R$ {perda:.2f}). Aposta mantém o valor.\n"
            sinal_ativo = (self.aposta_em, self.valor, self.nome, 0)
            return mensagem, sinal_ativo

        banca.debitar_aposta(valor_aposta_atual)
        self.perdas += 1
        proxima_aposta_calculada = self.valor * FATOR_MARTINGALE
        self.valor = min(proxima_aposta_calculada, MAX_APOSTA_VALOR)
        termo_derrota = "ZERO" if is_zero else "DERROTA"
        mensagem += f"❌ {termo_derrota} ({self.nome}). Perda R$ {valor_aposta_atual:.2f}. Próxima aposta: R$ {self.valor:.2f}.\n"

        if self.perdas > MAX_PERDAS_CONSECUTIVAS:
            mensagem += f"🚨 ALERTA ({self.nome}): Limite de perdas atingido. RESET.\n"
            self.reset()
            return mensagem, None

        sinal_ativo = (self.aposta_em, self.valor, self.nome, 0)
        return mensagem, sinal_ativo

    @abstractmethod
    def analisar_e_processar(self, mapa_resultado: Dict[str, str], banca: Banca, historico_global: List[str]) -> Tuple[str, Optional[Tuple]]:
        pass

class EstrategiaSequenciaSimples(Estrategia):
    def __init__(self, nome: str, chave_mapa: str, opostos: Dict[str,str]):
        super().__init__(nome, {'MIN_SEQUENCIA': MIN_SEQUENCIA_COR_ETC, 'GANHO_FATOR': 2, 'TIPO': '1:1'})
        self.chave_mapa = chave_mapa
        self.opostos = opostos

    def analisar_e_processar(self, mapa_resultado: Dict[str, str], banca: Banca, historico_global: List[str]) -> Tuple[str, Optional[Tuple]]:
        resultado_categoria = mapa_resultado[self.chave_mapa]
        self.atualizar_historico(resultado_categoria)
        msg, sinal_ativo = self._gerenciar_aposta_ativa(resultado_categoria, banca)
        if self.aposta_em:
            return msg, sinal_ativo

        if len(self.historico) >= self.config['MIN_SEQUENCIA']:
            ref = self.historico[0]
            if ref in self.opostos and all(h == ref for h in self.historico[:self.config['MIN_SEQUENCIA']]):
                alvo = self.opostos[ref]
                self.aposta_em = alvo
                msg += f"💰 SINAL ({self.nome}): Sequência de {self.config['MIN_SEQUENCIA']}x {NOMENCLATURA[ref]} detectada. Apostar em {NOMENCLATURA[alvo]}.\n"
                return msg, (alvo, self.valor, self.nome, 0)
        return msg, None

class EstrategiaTercos(Estrategia):
    def __init__(self, nome: str, chave_mapa: str, todos_alvos: List[str]):
        super().__init__(nome, {'MIN_SEQUENCIA': MIN_SEQUENCIA_TERCO_COLUNA, 'GANHO_FATOR': 3, 'TIPO': '2:1'})
        self.chave_mapa = chave_mapa
        self.todos_alvos = todos_alvos

    def analisar_e_processar(self, mapa_resultado: Dict[str, str], banca: Banca, historico_global: List[str]) -> Tuple[str, Optional[Tuple]]:
        resultado_categoria = mapa_resultado[self.chave_mapa]
        self.atualizar_historico(resultado_categoria)
        msg, sinal_ativo = self._gerenciar_aposta_ativa(resultado_categoria, banca)
        if self.aposta_em:
            return msg, sinal_ativo
        
        if len(self.historico) >= self.config['MIN_SEQUENCIA']:
            ultimos_resultados = {h for h in self.historico[:self.config['MIN_SEQUENCIA']] if h in self.todos_alvos}
            ausentes = [t for t in self.todos_alvos if t not in ultimos_resultados]
            if len(ausentes) == 1:
                alvo = ausentes[0]
                self.aposta_em = alvo
                try:
                    forca = self.historico.index(alvo)
                except ValueError:
                    forca = len(self.historico)
                msg += f"💰 SINAL ({self.nome}): {NOMENCLATURA[alvo]} em atraso de {forca} giros. Iniciar aposta.\n"
                return msg, (alvo, self.valor, self.nome, forca)
        return msg, None

class EstrategiaNumeroFrio(Estrategia):
    def __init__(self, nome: str):
         super().__init__(nome, {'MIN_SEQUENCIA': MIN_ATRASO_NUMERO_FRIO, 'GANHO_FATOR': 36, 'TIPO': '35:1'})

    def analisar_e_processar(self, mapa_resultado: Dict[str, str], banca: Banca, historico_global: List[str]) -> Tuple[str, Optional[Tuple]]:
        num_str = mapa_resultado['NUMERO']
        msg, sinal_ativo = self._gerenciar_aposta_ativa(num_str, banca)
        if self.aposta_em:
            return msg, sinal_ativo

        contagens = {str(i): 0 for i in range(37)}
        if TIPO_ROLETA == 'AMERICANA': contagens['00'] = 0
        for num in historico_global:
            if num in contagens:
                contagens[num] += 1
        
        frequencias = [(cont, num) for num, cont in contagens.items() if num not in ('0', '00')]
        if not frequencias: return "", None
        
        alvo = sorted(frequencias)[0][1]
        try:
            atraso = historico_global[::-1].index(alvo)
        except ValueError:
            atraso = len(historico_global)

        if atraso >= self.config['MIN_SEQUENCIA']:
            self.aposta_em = alvo
            msg += f"💰 SINAL ({self.nome}): Número {alvo} está a {atraso} giros sem sair. Iniciar aposta.\n"
            return msg, (alvo, self.valor, self.nome, atraso)
        return msg, None

class MotorRoleta:
    def __init__(self, banca_inicial: float):
        self.banca = Banca(banca_inicial)
        self.historico_global: List[str] = []
        self.estrategias: Dict[str, Estrategia] = {
            'COR': EstrategiaSequenciaSimples('COR', 'COR', {'R': 'B', 'B': 'R'}),
            'PAR_IMPAR': EstrategiaSequenciaSimples('PAR_IMPAR', 'PARIDADE', {'PAR': 'IMPAR', 'IMPAR': 'PAR'}),
            'ALTO_BAIXO': EstrategiaSequenciaSimples('ALTO_BAIXO', 'ALTURA', {'ALTO': 'BAIXO', 'BAIXO': 'ALTO'}),
            'DUZIA': EstrategiaTercos('DUZIA', 'DUZIA', ['D1', 'D2', 'D3']),
            'COLUNA': EstrategiaTercos('COLUNA', 'COLUNA', ['C1', 'C2', 'C3']),
            'FRIO': EstrategiaNumeroFrio('FRIO')
        }

    def ativar_estrategia(self, nome: str, status: bool):
        if nome in self.estrategias:
            self.estrategias[nome].ativo = status

    def alimentar_historico_inicial(self, numeros: List[str]):
        for num in numeros:
            self._atualizar_historicos(num)
            mapa = RoletaHelper.get_mapeamento_numero(num)
            if not mapa: continue
            for est in ['COR', 'PAR_IMPAR', 'ALTO_BAIXO', 'DUZIA', 'COLUNA']:
                if est in self.estrategias:
                    chave_mapa = {'COR':'COR', 'PAR_IMPAR':'PARIDADE', 'ALTO_BAIXO':'ALTURA', 'DUZIA':'DUZIA', 'COLUNA':'COLUNA'}[est]
                    self.estrategias[est].atualizar_historico(mapa[chave_mapa])
        print(f"\n✅ Sistema aquecido com {len(numeros)} resultados. Pronto para iniciar!")
        print("--------------------------------------")

    def _atualizar_historicos(self, num_str: str):
        self.historico_global.append(num_str)

    def processar_giro(self, num_str: str) -> str:
        mapa = RoletaHelper.get_mapeamento_numero(num_str)
        if not mapa:
            return f"ERRO: Número inválido ('{num_str}')."
        self._atualizar_historicos(num_str)
        output = f"➡️ CAIU: {num_str} ({NOMENCLATURA.get(mapa.get('COR'), '?')}, {NOMENCLATURA.get(mapa.get('PARIDADE'), '?')}) | Banca: R$ {self.banca.get_saldo():.2f}\n"
        output += "--------------------------------------\n"
        sinais_ativos = []
        mensagens = ""
        for nome, estrategia in self.estrategias.items():
            if estrategia.ativo:
                msg, sinal = estrategia.analisar_e_processar(mapa, self.banca, self.historico_global)
                mensagens += msg
                if sinal:
                    sinais_ativos.append(sinal)
        output += mensagens
        instrucoes_finais = []
        for aposta_em, valor, tipo, forca in sinais_ativos:
            termo = NOMENCLATURA_ACAO.get(aposta_em, aposta_em)
            if tipo in ['DUZIA', 'COLUNA', 'FRIO']:
                extra_info = f" (Atraso: {forca})"
                if tipo == 'FRIO':
                    instrucoes_finais.append(f"R$ {valor:.2f} no número {aposta_em}{extra_info}")
                else:
                    instrucoes_finais.append(f"R$ {valor:.2f} na {termo}{extra_info}")
            else:
                instrucoes_finais.append(f"R$ {valor:.2f} no {termo}")
        final_order = " e ".join(instrucoes_finais) if instrucoes_finais else "Aguarde Sinal"
        output += f"🎯 AÇÃO: {final_order}\n"
        output += "--------------------------------------"
        return output

def configurar_e_preparar() -> Optional[MotorRoleta]:
    print("\n[Assistente de Roleta v6 - Busca Agressiva Ativada]")
    banca_inicial = 0.0
    while True:
        try:
            banca_str = input("Qual o valor da sua banca inicial? R$ ").strip().replace(',', '.')
            banca_inicial = float(banca_str)
            break
        except ValueError:
            print("Valor inválido. Por favor, digite um número.")
    motor = MotorRoleta(banca_inicial)
    print("\n--- Configuração das Estratégias (S/N) ---")
    for chave in motor.estrategias:
        while True:
            resposta = input(f"Ativar estratégia '{chave}'? (S/N): ").strip().upper()
            if resposta in ['S', 'N']:
                motor.ativar_estrategia(chave, resposta == 'S')
                break
            else:
                print("Resposta inválida.")
    print("\n--- Aquecimento do Sistema (12 últimos resultados) ---")
    historico_inicial = []
    valid_range = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_range.append('00')
    for i in range(12):
        while True:
            num_str = input(f"Digite o {i+1}º resultado (o mais recente primeiro): ").strip()
            if num_str in valid_range:
                historico_inicial.append(num_str)
                break
            else:
                print(f"Número inválido para roleta {TIPO_ROLETA}.")
    motor.alimentar_historico_inicial(list(reversed(historico_inicial)))
    return motor

# ====================================================================
# === PEÇA 2: O CALIBRADOR INTERATIVO ================================
# ====================================================================

def obter_regiao_interativa():
    print("\n--- Calibração da Região de Leitura ---")
    print("\n1. Mova o rato para o canto SUPERIOR ESQUERDO da área e pressione 'r'.")
    keyboard.wait('r')
    x1, y1 = pyautogui.position()
    print(f"-> Ponto 1 salvo: ({x1}, {y1})")
    time.sleep(0.5)
    print("\n2. Mova o rato para o canto INFERIOR DIREITO da área e pressione 'r'.")
    keyboard.wait('r')
    x2, y2 = pyautogui.position()
    print(f"-> Ponto 2 salvo: ({x2}, {y2})")
    print("\n-------------------------------------------")
    left, top = min(x1, x2), min(y1, y2)
    width, height = abs(x2 - x1), abs(y2 - y1)
    if width == 0 or height == 0:
        print("ERRO: A largura e a altura não podem ser zero.")
        return None
    regiao_mss = {'top': top, 'left': left, 'width': width, 'height': height}
    print(f"✅ Calibração Concluída! Região: {regiao_mss}")
    return regiao_mss

# ====================================================================
# === PEÇA 3: O MONITOR DE OCR E O LOOP PRINCIPAL ====================
# ====================================================================

def processar_imagem_para_ocr(img_pil: Image.Image, threshold: int = 95) -> Image.Image:
    """
    VERSÃO v6 (Parâmetro de Qualidade): Aceita um 'threshold' para testar diferentes filtros.
    """
    try:
        ZOOM_FACTOR = 7
        width, height = img_pil.size
        if width == 0 or height == 0: return img_pil
        img_zoomed = img_pil.convert('L').resize(
            (width * ZOOM_FACTOR, height * ZOOM_FACTOR),
            Image.LANCZOS
        )
        img_bw = img_zoomed.point(lambda x: 255 if x > threshold else 0, '1')
        return img_bw
    except Exception as e:
        print(f"[ERRO no processar_imagem_para_ocr]: {e}")
        return img_pil

def tentar_leitura_agressiva(img_pil: Image.Image, valid_range: List[str]) -> Optional[str]:
    """
    Quando a leitura normal falha, testa várias combinações de filtros e modos de OCR.
    """
    print("\n[!] Leitura inicial falhou. Ativando modo de busca agressiva (rápido)...")
    thresholds_para_testar = [95, 115, 80]
    psm_para_testar = [8, 10, 7, 6, 11, 12, 13] # Coloquei o 8 e 10 como prioridade

    for psm in psm_para_testar:
        for threshold in thresholds_para_testar:
            config_ocr_agressivo = f'--oem 3 --psm {psm} -c tessedit_char_whitelist=0123456789'
            print(f"[BUSCA] Tentando com PSM={psm} e Threshold={threshold}...", end='\r')
            img_processada = processar_imagem_para_ocr(img_pil, threshold=threshold)
            texto_lido = pytesseract.image_to_string(img_processada, config=config_ocr_agressivo)
            numero_str = re.sub(r'\D', '', texto_lido)
            if numero_str and numero_str in valid_range:
                print(f"\n[SUCESSO] Número encontrado com PSM={psm} e Threshold={threshold}!  ")
                img_processada.save("debug_sucesso_agressivo.png")
                return numero_str
            # Pausa muito curta para velocidade máxima
            time.sleep(0.05)
    print("\n[FALHA] Busca agressiva concluída. Nenhum número encontrado.")
    return None

def main_monitor():
    """
    Função principal que orquestra todo o processo, agora com lógica de fallback.
    """
    motor = configurar_e_preparar()
    if not motor: return
    regiao_monitoramento = obter_regiao_interativa()
    if not regiao_monitoramento: return
    
    print(f"\n✅ Tudo pronto! Iniciando monitoramento. Pressione Ctrl+C para parar.")
    valid_range = [str(i) for i in range(37)]
    if TIPO_ROLETA == 'AMERICANA': valid_range.append('00')
    
    config_ocr_padrao = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
    ultimo_numero_lido = None
    
    try:
        with mss.mss() as sct:
            while True:
                img_raw = sct.grab(regiao_monitoramento)
                img_pil = Image.frombytes("RGB", img_raw.size, img_raw.bgra, "raw", "BGRX")
                
                img_processada_padrao = processar_imagem_para_ocr(img_pil)
                texto_lido = pytesseract.image_to_string(img_processada_padrao, config=config_ocr_padrao)
                numero_final = re.sub(r'\D', '', texto_lido)
                
                print(f"[DEBUG] Leitura Padrão: '{texto_lido.strip()}' -> Limpo: '{numero_final}' | Último: {ultimo_numero_lido}   ", end='\r')

                if not numero_final or numero_final not in valid_range:
                    numero_final = tentar_leitura_agressiva(img_pil, valid_range)

                if numero_final and (numero_final in valid_range) and (numero_final != ultimo_numero_lido):
                    print("\n" + "="*55)
                    print(f"NOVO NÚMERO DETECTADO: {numero_final}")
                    print("="*55)
                    feedback = motor.processar_giro(numero_final)
                    print(feedback)
                    ultimo_numero_lido = numero_final
                
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n\nMonitoramento interrompido pelo utilizador.")
    except Exception as e:
        print(f"\nOcorreu um erro fatal no monitoramento: {e}")
    finally:
        if motor:
            print("\nEncerrando Assistente.")
            resultado_final = motor.banca.get_saldo() - motor.banca.valor_inicial
            print(f"Banca Final: R$ {motor.banca.get_saldo():.2f} | Resultado da Sessão: R$ {resultado_final:+.2f}")

# ====================================================================
# === PONTO DE ENTRADA DO SCRIPT =====================================
# ====================================================================

if __name__ == "__main__":
    try:
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        tesseract_version = pytesseract.get_tesseract_version()
        print(f"Tesseract OCR v{tesseract_version} encontrado com sucesso.")
    except Exception:
        print("--- ERRO CRÍTICO AO INICIAR O TESSERACT ---")
        print(f"Caminho configurado: {TESSERACT_PATH}")
        print("Verifique se o caminho no topo do script (TESSERACT_PATH) está 100% correto.")
        input("\nPressione Enter para sair.")
        exit()

    main_monitor()

