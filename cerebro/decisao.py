"""Camada de decisão: interpreta o texto do usuário e decide o que a
Carla deve fazer a seguir. Por enquanto só cobre despedida; no futuro
vai crescer pra reconhecer pedidos de automação, pesquisa, papo furado
etc., mantendo o main.py enxuto (só chama decidir())."""

from recursos.formatacao import remover_acentos

PALAVRAS_DESPEDIDA = [
    "tchau carla", "vai dormir carla", "carla tchau",
]


def decidir(texto):
    """Devolve False quando o usuário está encerrando a conversa,
    True pra continuar o ciclo normalmente."""
    texto_normalizado = remover_acentos(texto).lower()

    if any(x in texto_normalizado for x in PALAVRAS_DESPEDIDA):
        return False

    return True