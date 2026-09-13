"""Espera finita; estados de falha nunca liberam a próxima tarefa."""
import logging
import time


def wait_terminal(fetch, state_of, success, failure, timeout=1800, interval=15):
    deadline = time.monotonic() + timeout
    previous = None
    while time.monotonic() < deadline:
        result = fetch()
        state = state_of(result)
        if state != previous:
            logging.info("Estado remoto: %s", state)
            previous = state
        if state in success:
            return result
        if state in failure:
            raise RuntimeError(f"Execução remota falhou: {state}")
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"Execução remota excedeu {timeout}s; confira/cancele no serviço")
