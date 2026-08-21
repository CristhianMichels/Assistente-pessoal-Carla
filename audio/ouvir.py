import speech_recognition as sr

def escutar():
    recognizer = sr.Recognizer()

    recognizer.pause_threshold = 1.0
    recognizer.non_speaking_duration = 0.5

    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = 400

    with sr.Microphone(sample_rate=16000) as source:
        print("Calibrando microfone por 1 segundo (fique em silêncio)...")
        recognizer.adjust_for_ambient_noise(source, duration=1.0)

        recognizer.energy_threshold = max(recognizer.energy_threshold, 300)
        print(f"Sensibilidade definida em: {recognizer.energy_threshold}")

        print("\nMicrofone pronto! Fale normalmente...\n")

        try:
            audio = recognizer.listen(source, phrase_time_limit=None)
            print("Transcrevendo...")

            texto = recognizer.recognize_google(
                audio,
                language="pt-BR"
            )

            if texto:
                print(f"Você: {texto}\n")
                return texto

        except sr.UnknownValueError:
            pass

        except sr.RequestError as e:
            print(f"Erro no serviço do Google: {e}\n")

        except KeyboardInterrupt:
            print("\nEncerrando...")

        return None


if __name__ == "__main__":
    escutar()