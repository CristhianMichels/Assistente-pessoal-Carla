import queue
import threading

import sounddevice as sd
from kokoro import KPipeline

from cerebro.ia import FIM_STREAM

pipeline = KPipeline(lang_code="p")

VOZ = "af_sky"
VELOCIDADE = 1.3
SAMPLE_RATE = 24000

_FIM = object()


def falar(texto, stop_event=None):
    """Fala um texto avulso, bloqueante. Usado fora do fluxo de
    streaming da IA — ex.: o "Estou aqui!" de ativação."""
    if not texto or not texto.strip():
        return

    fila_audio = queue.Queue(maxsize=2)

    def gerar():
        try:
            for _, _, audio in pipeline(texto, voice=VOZ, speed=VELOCIDADE):
                if stop_event and stop_event.is_set():
                    break
                fila_audio.put(audio)
        except Exception as e:
            print(f"Erro na síntese de voz: {e}")
        finally:
            fila_audio.put(_FIM)

    thread_gerador = threading.Thread(target=gerar, daemon=True)
    thread_gerador.start()

    try:
        while True:
            audio = fila_audio.get()
            if audio is _FIM:
                break
            if stop_event and stop_event.is_set():
                break
            if _tocar(audio, stop_event):
                break
    finally:
        thread_gerador.join(timeout=2)


def falar_stream(fila_frases, stop_event=None):
    """Consome frases assim que saem do LLM (a fila devolvida por
    cerebro.ia.pensar_stream) e vai sintetizando + tocando o áudio sem
    parar: enquanto uma frase está tocando, a PRÓXIMA já está sendo
    sintetizada no Kokoro em paralelo — sem espera/silêncio entre uma
    frase e outra.

    Antes, cada frase disparava sua própria chamada bloqueante a
    falar(), então a síntese da frase seguinte só começava depois que a
    anterior tocasse inteira: daí o delay entre frases. Aqui a geração
    roda numa única thread contínua que vai lendo a fila de texto e
    empilhando áudio numa fila só, enquanto a reprodução consome dessa
    fila em paralelo.

    Devolve True se foi interrompida no meio."""
    fila_audio = queue.Queue(maxsize=3)

    def gerar():
        try:
            while True:
                if stop_event and stop_event.is_set():
                    return
                try:
                    # timeout curto em vez de bloquear pra sempre: assim
                    # a geração nota uma interrupção mesmo se ainda não
                    # tiver chegado a próxima frase do LLM.
                    frase = fila_frases.get(timeout=0.1)
                except queue.Empty:
                    continue

                if frase is FIM_STREAM:
                    return

                print(f"Carla: {frase}")
                for _, _, audio in pipeline(frase, voice=VOZ, speed=VELOCIDADE):
                    if stop_event and stop_event.is_set():
                        return
                    fila_audio.put(audio)
        except Exception as e:
            print(f"Erro na síntese de voz: {e}")
        finally:
            fila_audio.put(_FIM)

    thread_gerador = threading.Thread(target=gerar, daemon=True)
    thread_gerador.start()

    interrompida = False
    try:
        while True:
            audio = fila_audio.get()
            if audio is _FIM:
                break
            if stop_event and stop_event.is_set():
                interrompida = True
                break
            if _tocar(audio, stop_event):
                interrompida = True
                break
    finally:
        thread_gerador.join(timeout=2)

    return interrompida


def _tocar(audio, stop_event):
    """Toca um pedaço de áudio, checando interrupção a cada 30ms.
    Devolve True se foi interrompido no meio da reprodução."""
    sd.play(audio, SAMPLE_RATE)
    while sd.get_stream().active:
        if stop_event and stop_event.is_set():
            sd.stop()
            return True
        sd.sleep(30)
    return False