import pyautogui
import keyboard
import time
import cv2
import numpy as np

def obter_regiao_interativa():
    """
    Permite que o usuário selecione uma região da tela pressionando 'r' 
    nos cantos superior esquerdo e inferior direito.
    """
    
    print("--- Calibração da Região de Leitura ---")
    print("\n1. Mova o mouse para o canto SUPERIOR ESQUERDO da área que você quer ler.")
    print("   (Ex: bem no cantinho de cima e à esquerda do número)")
    print("\n   Pressione 'r' para salvar o Ponto 1.")
    
    # Espera o usuário pressionar 'r'
    keyboard.wait('r')
    x1, y1 = pyautogui.position()
    print(f"-> Ponto 1 (Superior Esquerdo) salvo: ({x1}, {y1})")
    
    # Pequena pausa para evitar leitura dupla da tecla
    time.sleep(0.5) 
    
    print("\n2. Agora, mova o mouse para o canto INFERIOR DIREITO da área.")
    print("   (Ex: no cantinho de baixo e à direita do número)")
    print("\n   Pressione 'r' novamente para salvar o Ponto 2.")
    
    # Espera o usuário pressionar 'r' novamente
    keyboard.wait('r')
    x2, y2 = pyautogui.position()
    print(f"-> Ponto 2 (Inferior Direito) salvo: ({x2}, {y2})")
    print("\n-------------------------------------------")

    # Garante que os pontos sejam ordenados corretamente (à prova de erros)
    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)  # abs() garante que seja positivo
    height = abs(y2 - y1) # abs() garante que seja positivo
    
    # Verifica se a região tem um tamanho válido
    if width == 0 or height == 0:
        print("ERRO: A largura e a altura não podem ser zero. Tente novamente.")
        return None

    # Formato que a biblioteca 'mss' (de screenshot) precisa
    regiao_mss = {'top': top, 'left': left, 'width': width, 'height': height}
    
    print(f"✅ Calibração Concluída!")
    print(f"A região de monitoramento foi definida como:")
    print(regiao_mss)
    
    return regiao_mss

if __name__ == "__main__":
    # NOTA: Este script pode precisar de privilégios de administrador
    # no Windows para "ouvir" as teclas em outros programas.
    # Se não funcionar, tente executar seu terminal/editor como "Administrador".
    try:
        regiao_final = obter_regiao_interativa()
        if regiao_final:
            print("\nÓtimo! Agora vamos usar essa região no script principal.")
            # No nosso script final, vamos chamar essa função
            # e passar 'regiao_final' para o monitor de OCR.
            
    except Exception as e:
        print(f"\nOcorreu um erro. Você está executando este script como Administrador?")
        print(f"Detalhe: {e}")
    
    print("\nPressione Enter para sair...")
    input()