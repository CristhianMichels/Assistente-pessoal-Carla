from audio.ouvir import escutar
from audio.falar import falar

while True:
    texto = escutar()
    if texto:
        print(texto)
        falar(texto)