from kokoro import KPipeline
import sounddevice as sd

pipeline = KPipeline(lang_code="p")


def falar(texto):
    
    gerador = pipeline(
        texto,
        voice="pf_dora",
        speed=1.1
    )

    for _, _, audio in gerador:
        sd.play(audio, 24000)
        sd.wait()
