from phasenox.memory.history import memory


MAX_MESSAGES = 8


def build_history():

    history = memory.get_messages()

    if len(history) <= MAX_MESSAGES:
        return history

    return history[-MAX_MESSAGES:]