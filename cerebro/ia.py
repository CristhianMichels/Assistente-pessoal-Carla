import re
import threading
import queue as _queue
import ollama
from cerebro.personalidade import PERSONALIDADE_BASE, INSTRUCAO_SUGESTAO

PALAVRAS_TECNICAS = [
    "explica", "explique", "me explica",
    "o que e", "qual a diferenca", "qual e a diferenca",
    "me ensina", "como funciona", "como faco",
    "passo a passo", "detalhe", "detalhes",
    "definicao", "o que significa",
    "quem foi", "quem e", "quem sao",
    "onde fica", "quando foi", "quantos", "qual que e", "que que e",
    "formula", "equacao", "teorema", "calcula", "calculo",
    "resolve", "resolver", "repete",
]

PALAVRAS_GERACAO_TEXTO = [
    "cria uma historia", "crie uma historia",
    "redacao", "poema", "texto sobre",
    "resumo sobre", "resuma",
    "gera um texto", "gere um texto",
    "carta sobre"
]

MAX_HISTORICO = 4

_historico = []
_historico_lock = threading.Lock()

FIM_STREAM = object()

_PADRAO_ORIGEM_PROIBIDA = re.compile(
    r"(eu\s+sou\s+(a\s+|o\s+)?(llama|chatgpt|gpt|gemini)\b)"
    r"|((fui|sou)\s+(treinad[oa]|desenvolvid[oa]|criad[oa])\s+(pel[ao]|por)\s+(a\s+)?(meta|openai|google))"
    r"|((minha|a\s+minha)\s+(empresa|criadora)\s+(é|eh)\s+(a\s+)?(meta|openai|google))",
    re.IGNORECASE,
)

_RE_FIM_FRASE = re.compile(r'([.!?\n]+)(\s+|$)')


def limpar_resposta(texto):
    texto = re.sub(r'[*_#`]', '', texto)
    texto = re.sub(r'\s*\n+\s*', ' ', texto)
    texto = re.sub(r'[\U0001F300-\U0001FAFF]', '', texto)
    return texto.strip()


def _validar_origem(frase):
    if frase and _PADRAO_ORIGEM_PROIBIDA.search(frase):
        return "Fui criada pelo Cristhian Post Michels."
    return frase


def classificar_pergunta(pergunta):
    texto = pergunta.lower()

    if any(x in texto for x in PALAVRAS_GERACAO_TEXTO):
        return "geracao"

    if any(x in texto for x in PALAVRAS_TECNICAS):
        return "tecnico"

    return "casual"


def _config_por_tipo(tipo):
    if tipo == "geracao":
        return (
            "gemma3:4b", 700, 4096, 0.7,
            "Gere exatamente o texto solicitado com qualidade, sem falar nada além do que foi solicitado, apenas uma sugestão ao final quando necessário."
        )

    if tipo == "tecnico":
        return (
            "llama3.2:3b", 300, 2048, 0.2,
            "Responda com precisão e detalhes. Não invente informações. "
            "No máximo umas 150 palavras. Se não tiver certeza sobre "
            "algo, diga claramente que não sabe em vez de chutar."
        )

    return (
        "llama3.2:3b", 70, 1024, 0.6,
        "Converse naturalmente. Responda em até 25 palavras."
    )


def _extrair_frase_pronta(buffer):
    """Corta o buffer no primeiro fim de frase encontrado (. ! ? ou
    quebra de linha). Devolve (frase, resto) ou (None, buffer) se ainda
    não tiver nenhum fim de frase completo."""
    m = _RE_FIM_FRASE.search(buffer)
    if not m:
        return None, buffer
    fim = m.end()
    return buffer[:fim], buffer[fim:]


def pensar_stream(pergunta):
    """Dispara a geração da resposta numa thread separada e devolve uma
    fila de onde dá pra consumir frases prontas assim que elas saem do
    Ollama — enquanto uma frase está sendo falada, a próxima já pode
    estar sendo gerada em paralelo.

    Devolve (fila, cancelar):
    - fila: dá objetos `str` (frases) e termina com o sentinel FIM_STREAM
    - cancelar: threading.Event — chame .set() para parar a geração
      antecipadamente (ex.: quando o usuário interrompe a Carla)
    """
    fila = _queue.Queue()
    cancelar = threading.Event()

    threading.Thread(
        target=_gerar_em_thread, args=(pergunta, fila, cancelar), daemon=True
    ).start()

    return fila, cancelar


def pensar(pergunta):
    """Versão bloqueante, mantida por compatibilidade: espera a resposta
    inteira e devolve como uma string só."""
    fila, _ = pensar_stream(pergunta)
    partes = []
    while True:
        item = fila.get()
        if item is FIM_STREAM:
            break
        partes.append(item)
    return " ".join(partes).strip()


def _gerar_em_thread(pergunta, fila, cancelar):
    global _historico

    tipo = classificar_pergunta(pergunta)
    modelo, num_predict, num_ctx, temperature, instrucao = _config_por_tipo(tipo)

    system_prompt = (
        f"{PERSONALIDADE_BASE}\n\n"
        f"{instrucao}\n\n"
        f"{INSTRUCAO_SUGESTAO}"
    )

    with _historico_lock:
        mensagens = [{"role": "system", "content": system_prompt}]
        mensagens.extend(_historico[-MAX_HISTORICO:])
    mensagens.append({"role": "user", "content": pergunta})

    resposta_completa = ""
    buffer = ""

    try:
        stream = ollama.chat(
            model=modelo,
            messages=mensagens,
            stream=True,
            options={
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": num_ctx,
                "stop": ["Usuário:", "User:", "Assistant:", "Carla:"],
            },
        )

        for chunk in stream:
            if cancelar.is_set():
                break

            pedaco = chunk.get("message", {}).get("content", "")
            if not pedaco:
                continue
            buffer += pedaco

            frase, buffer = _extrair_frase_pronta(buffer)
            while frase:
                frase_limpa = _validar_origem(limpar_resposta(frase))
                if frase_limpa:
                    resposta_completa += frase_limpa + " "
                    fila.put(frase_limpa)
                frase, buffer = _extrair_frase_pronta(buffer)
                if cancelar.is_set():
                    break

        if not cancelar.is_set():
            sobra = _validar_origem(limpar_resposta(buffer))
            if sobra:
                resposta_completa += sobra
                fila.put(sobra)

    except Exception as e:
        print(f"Erro ao consultar o Ollama: {e}")

    finally:
        resposta_final = resposta_completa.strip()
        if resposta_final:
            with _historico_lock:
                _historico.append({"role": "user", "content": pergunta})
                _historico.append({"role": "assistant", "content": resposta_final})
                _historico[:] = _historico[-MAX_HISTORICO:]
        fila.put(FIM_STREAM)