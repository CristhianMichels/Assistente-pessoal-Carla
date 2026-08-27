"""Camada de decisão: interpreta o texto do usuário e decide o que a
Carla deve fazer a seguir. Por enquanto só cobre despedida; no futuro
vai crescer pra reconhecer pedidos de automação, pesquisa, papo furado
etc., mantendo o main.py enxuto (só chama decidir())."""

from recursos.formatacao import remover_acentos
from cerebro.ia import pensar_stream

PALAVRAS_DESPEDIDA = [
    "tchau carla", "vai dormir carla", "carla tchau",
]


def decidir(texto):
    """Devolve sempre (conversa, resposta, fila_frases, cancelar_geracao):
    - conversa: False quando o usuário está encerrando, True caso contrário
    - resposta: o texto que vai virar fala, ou None se não há nada a falar
    - fila_frases / cancelar_geracao: o que falar_com_interrupcao precisa
      pra tocar e, se for o caso, cancelar a geração. Vêm None quando não
      há geração de IA rolando."""
    texto_normalizado = remover_acentos(texto)

    if any(x in texto_normalizado for x in PALAVRAS_DESPEDIDA):
        return False, None, None, None

    resposta = texto
    fila_frases, cancelar_geracao = pensar_stream(resposta)
    return True, resposta, fila_frases, cancelar_geracao