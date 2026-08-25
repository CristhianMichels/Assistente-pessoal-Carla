import queue
import threading

from audio.falar import falar, falar_stream
from audio.ouvir import (
    calibrar, escutar, monitorar_fala, parar_monitoramento,
    resultado_interrupcao,
)
from cerebro.ia import pensar_stream
from cerebro.decisao import decidir

TIMEOUT_CONVERSA = 20
# Depois de uma interrupção, o áudio já foi capturado (falar_com_interrupcao
# só retorna depois disso), mas o reconhecimento (Google, rede) ainda pode
# estar rolando em background. Esse é o tempo que esperamos o texto chegar
# em resultado_interrupcao antes de desistir e abrir um escutar() novo.
TIMEOUT_RECONHECIMENTO_INTERRUPCAO = 4


def falar_com_interrupcao(fila_frases, cancelar_geracao):
    """Fala a resposta em streaming contínuo (ver audio.falar.falar_stream)
    enquanto monitora interrupção o tempo todo. Devolve True se foi
    interrompida no meio."""
    stop_event = threading.Event()
    thread_monitor = threading.Thread(
        target=monitorar_fala, args=(stop_event,), daemon=True
    )
    thread_monitor.start()

    interrompida = False
    try:
        interrompida = falar_stream(fila_frases, stop_event)
    finally:
        if interrompida:
            cancelar_geracao.set()
        else:
            parar_monitoramento()
        thread_monitor.join()

    return interrompida


def _proximo_texto():
    if not resultado_interrupcao.empty():
        return resultado_interrupcao.get()
    return escutar(timeout=TIMEOUT_CONVERSA)


def _texto_da_interrupcao():
    """Chamada logo depois de uma interrupção confirmada: espera o texto
    do que a pessoa falou por cima da Carla chegar em resultado_interrupcao
    (reconhecimento roda em background, é assíncrono). Se não chegar a
    tempo (reconhecimento falhou ou demorou demais), devolve None e quem
    chamou cai de volta pra um escutar() novo — sem travar pra sempre."""
    try:
        return resultado_interrupcao.get(timeout=TIMEOUT_RECONHECIMENTO_INTERRUPCAO)
    except queue.Empty:
        return None


def ciclo_conversa():
    texto = None
    conversa = True
    while conversa:
        if texto is None:
            texto = _proximo_texto()

        if not texto:
            print("Carla: (silêncio) voltando a esperar a palavra de ativação.")
            return

        print(f"Você: {texto}")

        conversa = decidir(texto)
        interrompida = False

        try:
            fila_frases, cancelar_geracao = pensar_stream(texto)
            interrompida = falar_com_interrupcao(fila_frases, cancelar_geracao)
        except Exception as e:
            print(f"Erro ao gerar/falar resposta: {e}")

        texto = _texto_da_interrupcao() if interrompida else None


def main():
    calibrar()

    while True:
        try:
            texto = escutar()
        except KeyboardInterrupt:
            print("\nEncerrando...")
            break

        if texto and "carla" in texto.lower():
            print("Estou aqui!")
            falar("Estou aqui!")
            ciclo_conversa()


if __name__ == "__main__":
    main()