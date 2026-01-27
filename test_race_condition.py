"""

teste de race Condition:
Tentar comprar o MESMO ultiomo ingresso a aprtir de 2 thread ao mesmo tempo.
"""

import threading
import time
import requests
from typing import Any, Dict

BASE_URL = "http://localhost:8000"


def reserve_ticket_thread(name: str, event_id: int, user_id: int) -> None:
    """
    Função executada por cada thread: tenta reservar um ticket.
    """
    payload: Dict[str, Any] = {
        "event_id": event_id,
        "user_id": user_id,
    }
    print(f"[{name}] Enviando requisição...")

    try:
        response = requests.post(
            f"{BASE_URL}/tickets/reserve",
            json=payload,
            timeout=5
        )
        print(f"[{name}] Status: {response.status_code}")
        print(f"[{name}] Corpo: {response.json()}")

    except requests.exceptions.RequestException as e:
        print(f"[{name}] Erro na requisição: {e}")


def main():
    event_id = 1
    print("=" * 60)
    print("TESTE DE RACE CONDITION")
    print("=" * 60)
    print("Cenário: 2 usuários tentando reservar o ÚLTIMO ingresso")
    print("Esperado: Apenas 1 sucesso (201), o outro recebe 409")
    print("=" * 60)

    time.sleep(1)

    # Duas threads simulando 2 usuarios diferentes

    t1 = threading.Thread(
        target=reserve_ticket_thread,
        args=("Thread-1", event_id, 1001),
    )
    t2 = threading.Thread(
        target=reserve_ticket_thread,
        args=("Thread-2", event_id, 1002),
    )

    # Disparar as duas quase ao mesmo tempo
    t1.start()
    t2.start()

    # Esperar ambas terminarem

    t1.join()
    t2.join()

    print("=" * 60)
    print("Teste concluido.")
    print("=" * 60)


if __name__ == "__main__":
    main()
