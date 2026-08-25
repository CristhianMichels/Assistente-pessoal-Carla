import queue
import threading

import numpy as np
import sounddevice as sd
import speech_recognition as sr

recognizer = sr.Recognizer()

recognizer.pause_threshold = 1.0
recognizer.non_speaking_duration = 0.5
# Mínimo de áudio acima do limiar pra contar como frase válida (em vez
# de ruído/clique). O padrão da lib é 0.3s, e isso cortava palavras
# únicas curtas tipo "sim", "não", "opa" antes de completarem esse
# tempo — baixado pra pegar elas também.
recognizer.phrase_threshold = 0.1

recognizer.dynamic_energy_threshold = False
recognizer.energy_threshold = 400

microfone = sr.Microphone(sample_rate=16000)
_source = None

LIMIAR_INTERRUPCAO = 0.05
LIMITE_SILENCIO = 20

resultado_interrupcao = queue.Queue()

_stream_monitor = None
_armado = False
_gravando = False
_silencio_contador = 0
_frames = []
_stop_event_atual = None

# Fila só de áudio já capturado -> o worker de reconhecimento consome
# fora da thread de áudio, então pode bloquear em rede sem problema.
_fila_audio_para_reconhecer = queue.Queue()


def calibrar():
    global _source, _stream_monitor

    _source = microfone.__enter__()

    print("Calibrando microfone por 1 segundo (fique em silêncio)...")
    recognizer.adjust_for_ambient_noise(_source, duration=1.0)

    recognizer.energy_threshold = max(recognizer.energy_threshold, 300)
    print(f"Sensibilidade definida em: {recognizer.energy_threshold}")

    _stream_monitor = sd.InputStream(
        samplerate=16000,
        channels=1,
        dtype='float32',
        callback=_callback_monitor
    )

    threading.Thread(
        target=_loop_reconhecimento_interrupcao, daemon=True
    ).start()

    print("\nMicrofone pronto! Fale normalmente...\n")


def iniciar_stream_monitor():
    if not _stream_monitor.active:
        _stream_monitor.start()


def parar_stream_monitor():
    if _stream_monitor.active:
        _stream_monitor.stop()


def escutar(timeout=None, phrase_time_limit=None):
    try:
        audio = recognizer.listen(
            _source, timeout=timeout, phrase_time_limit=phrase_time_limit
        )
        print("Transcrevendo...")

        texto = recognizer.recognize_google(audio, language="pt-BR")
        return texto or None

    except sr.WaitTimeoutError:
        return None

    except sr.UnknownValueError:
        return None

    except sr.RequestError as e:
        print(f"Erro no serviço do Google: {e}\n")
        return None

    except KeyboardInterrupt:
        print("\nEncerrando...")
        raise


def _callback_monitor(indata, frames_count, time_info, status):
    """Roda na thread de áudio do PortAudio. Precisa ser rápido e sem I/O
    de rede/disco — só mede volume e empilha o buffer."""
    global _gravando, _silencio_contador

    if not _armado:
        return

    volume = np.abs(indata).mean()

    if not _gravando:
        if volume > LIMIAR_INTERRUPCAO:
            _gravando = True
            _silencio_contador = 0
            _frames.append(indata.copy())
            if _stop_event_atual:
                _stop_event_atual.set()
    else:
        _frames.append(indata.copy())
        if volume > LIMIAR_INTERRUPCAO:
            _silencio_contador = 0
        else:
            _silencio_contador += 1
            if _silencio_contador > LIMITE_SILENCIO:
                _finalizar_gravacao()


def _finalizar_gravacao():
    """Ainda roda dentro do callback, mas agora só empacota e delega —
    nada de rede aqui. Parar o InputStream em si também NÃO é feito
    aqui: parar/fechar um stream de dentro do próprio callback trava.
    Isso é feito fora, pela monitorar_fala, quando o loop dela nota que
    _armado virou False."""
    global _armado, _gravando

    _armado = False
    _gravando = False

    if _frames:
        audio_np = np.concatenate(_frames, axis=0)
        _fila_audio_para_reconhecer.put(audio_np)


def _loop_reconhecimento_interrupcao():
    """Worker dedicado, fora da thread de áudio: aqui pode bloquear em
    rede à vontade."""
    while True:
        audio_np = _fila_audio_para_reconhecer.get()

        try:
            audio_np = np.clip(audio_np, -1.0, 1.0)
            audio_int16 = (audio_np * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()

            audio_data = sr.AudioData(audio_bytes, 16000, 2)
            texto = recognizer.recognize_google(audio_data, language="pt-BR")
            if texto:
                resultado_interrupcao.put(texto)

        except (sr.UnknownValueError, sr.RequestError):
            pass


def parar_monitoramento():
    global _armado
    _armado = False


def monitorar_fala(stop_event):
    global _armado, _frames, _gravando, _silencio_contador, _stop_event_atual

    _frames = []
    _gravando = False
    _silencio_contador = 0
    _stop_event_atual = stop_event
    _armado = True

    # Bug das últimas mudanças: o InputStream era só criado em
    # calibrar(), nunca iniciado — então _callback_monitor nunca
    # rodava e a interrupção nunca era detectada. Agora o stream liga
    # aqui (só durante a fala da Carla) e desliga ao sair do loop.
    iniciar_stream_monitor()

    while _armado:
        sd.sleep(50)

    parar_stream_monitor()


if __name__ == "__main__":
    calibrar()
    print(escutar())