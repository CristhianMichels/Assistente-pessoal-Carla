import queue
import threading

from audio.falar import falar, falar_stream
from audio.ouvir import (
    calibrar, escutar, monitorar_fala, parar_monitoramento,
    resultado_interrupcao,
)
from cerebro.decisao import decidir
from recursos.formatacao import remover_acentos

TIMEOUT_RECONHECIMENTO_INTERRUPCAO = 4


def falar_com_interrupcao(fila_frases, cancelar_geracao=None):
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
            if cancelar_geracao:
                cancelar_geracao.set()
        else:
            parar_monitoramento()
        thread_monitor.join()

    return interrompida


def _proximo_texto():
    """Sem timeout de propósito: a conversa não deve voltar sozinha pra
    palavra de ativação por silêncio, só quando a pessoa disser
    explicitamente "tchau carla" (despedida) ou "desativar carla"
    (desligar o sistema)."""
    if not resultado_interrupcao.empty():
        return resultado_interrupcao.get()
    return escutar()


def _texto_da_interrupcao():
    try:
        return resultado_interrupcao.get(timeout=TIMEOUT_RECONHECIMENTO_INTERRUPCAO)
    except queue.Empty:
        return None


def ciclo_conversa():
    """Devolve True pra continuar ligado (voltar a esperar a palavra de
    ativação) e False só quando for pra desligar o sistema de vez."""
    texto = None
    conversa = True
    while conversa:
        if texto is None:
            texto = _proximo_texto()

        if not texto:
            texto = None
            continue

        print(f"Você: {texto}")

        if "desativar carla" in remover_acentos(texto).lower():
            print("Carla: Desligando")
            return False

        conversa, resposta, fila_frases, cancelar_geracao = decidir(texto)
        interrompida = False
        
        if resposta:
            try:
                interrompida = falar_com_interrupcao(fila_frases, cancelar_geracao)
            except Exception as e:
                print(f"Erro ao gerar/falar resposta: {e}")

            texto = _texto_da_interrupcao() if interrompida else None
        else:
            texto = None

    return True


def main():
    calibrar()
    ligado = True

    while ligado:
        try:
            texto = escutar()
        except KeyboardInterrupt:
            print("\nEncerrando...")
            break

        if not texto:
            continue

        texto_normalizado = remover_acentos(texto).lower()

        if "desativar carla" in texto_normalizado:
            print("Carla: Desligando")
            ligado = False
        elif "carla" in texto_normalizado:
            print("Estou aqui!")
            falar("Estou aqui!")
            ligado = ciclo_conversa()


if __name__ == "__main__":
    main()