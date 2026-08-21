import pyautogui
import time
def abrir(frase):
    palavras_separadas = frase.strip().split()
    if len(palavras_separadas) <3:
        del palavras_separadas[0]
    else:
        del palavras_separadas[0:2]
    
    frase = ' '.join(palavras_separadas)
    print(frase)
    pyautogui.press('win')
    time.sleep(0.8)
    pyautogui.write(frase)
    time.sleep(0.8)
    pyautogui.press('enter')
    
