import ollama

PALAVRAS_TECNICAS = [
    "como", "explica", "explique", "por que", "porque",
    "o que é", "qual a diferença", "me ensina", "ensinar",
    "funciona", "passo a passo", "detalhe", "detalhes"
]


def eh_pergunta_tecnica(pergunta):
    pergunta_lower = pergunta.lower()
    return any(palavra in pergunta_lower for palavra in PALAVRAS_TECNICAS)


def pensar(pergunta):
    if eh_pergunta_tecnica(pergunta):
        num_predict = 150
        instrucao_tamanho = "pode responder com mais detalhes, mas sem enrolar."
    else:
        num_predict = 30
        instrucao_tamanho = "responda com o mínimo de palavras possível, direto ao ponto."

    resposta = ollama.chat(
        model="llama3.2:1b",
        messages=[
            {
                "role": "system",
                "content": (
                    "Você é a Carla, uma assistente de voz pessoal. "
                    f"{instrucao_tamanho}"
                )
            },
            {"role": "user", "content": pergunta}
        ],
        options={
            "num_predict": num_predict,
            "num_ctx": 512
        }
    )
    return resposta["message"]["content"]