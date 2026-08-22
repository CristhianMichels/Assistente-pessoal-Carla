from audio.ouvir import escutar, calibrar
from audio.falar import falar
from cerebro.ia import pensar

calibrar()
while True:
    texto = escutar()
    if texto:
        print(f"Você: {texto}")
        resposta = pensar(texto)
        print(f"Carla: {resposta}")
        falar(resposta)