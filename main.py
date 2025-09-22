import speech_recognition as sr
import pyautogui
import time
import os
import asyncio
from playsound import playsound
from modulos import funcoes
import edge_tts
import pyperclip

parar = 'nao'

# Lista de comandos
comandos = {
    "tchau": ["tchau", "adeus"],
    "abrir": ["abrir", "abre", "abra", "executa", "executar"],
    "escrever": ["escreva", "escrever", "escreve"],
    "enter": ["enter", "pressionar enter"]
}

# Função para gerar e tocar a voz da Carla
async def gerar_audio(texto, arquivo="voz.mp3"):
    communicate = edge_tts.Communicate(texto, voice="pt-BR-FranciscaNeural")
    await communicate.save(arquivo)  # salva mp3

def falar(texto):
    arquivo = "voz.mp3"
    asyncio.run(gerar_audio(texto, arquivo))
    playsound(arquivo)
    os.remove(arquivo)

# Função para ouvir ativação
def microfone_ouvir():
    global parar
    microfone = sr.Recognizer()

    with sr.Microphone() as source:
        microfone.energy_threshold = 70
        microfone.dynamic_energy_threshold = True
        microfone.pause_threshold = 0.8
        microfone.adjust_for_ambient_noise(source, duration=1.5)

        print("Aguardando 'Carla' para ativar...")

        while parar == 'nao':
            try:
                audio = microfone.listen(source)
                frase = microfone.recognize_google(audio, language='pt-BR').lower()

                # Comando de desligar
                if "carla" in frase and "desligar" in frase:
                    print("Carla foi dormir...")
                    falar("Valeu gurizada!...")
                    parar = 'sim'

                # Ativação do assistente
                elif "carla" in frase:
                    print("Oi, como posso ajudar?")
                    falar("Oi, como posso ajudar?")
                    interagir(microfone, source)

            except sr.UnknownValueError:
                continue
            time.sleep(0.3)

# Função de interação com comandos
def interagir(microfone, source):
    while True:
        try:
            audio = microfone.listen(source)
            frasenatural = microfone.recognize_google(audio, language='pt-BR')
            frase = frasenatural.lower()
            print(f"Você disse: {frase}")

            # Comando de tchau
            if any(cmd in frase for cmd in comandos["tchau"]):
                print("Até logo!")
                falar("Até logo!")
                break

            # Comando de abrir
            elif any(cmd in frase for cmd in comandos["abrir"]):
                funcoes.abrir(frase)

            # Comando de escrever
            elif any(cmd in frase for cmd in comandos["escrever"]):
                frase_modificada = frasenatural
                for palavra in comandos["escrever"]:
                    frase_modificada = frase_modificada.replace(palavra, "")
                frase_modificada = frase_modificada.strip()

                # Usa clipboard para escrever corretamente
                pyperclip.copy(frase_modificada)
                pyautogui.hotkey("ctrl", "v")


            # Comando de enter
            elif any(cmd in frase for cmd in comandos["enter"]):
                pyautogui.press("enter")

        except sr.UnknownValueError:
            continue

# Inicia a Carla
microfone_ouvir()
