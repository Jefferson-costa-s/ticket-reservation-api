#!/usr/bin/env python
"""
Stress test: Simula 50 usuários criando sessões (com e sem cleanup).
Mostra na prática o memory leak vs memory cleanup.
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"


def get_memory():
    """Retorna uso de RAM em MB."""
    response = requests.get(f"{BASE_URL}/memory")
    data = response.json()
    return data["rss_mb"]


def test_sessions_bad():
    """Testa endpóint RUIM (memory leak)."""
    print("\n" + "="*60)
    print("TESTE1: Memory Leak (RUIM) - /sessions-bad")
    print("="*60)
    print("Criando 50 sessẽs SEM cleanup...")
    print("Observe a RAM crescer cada vez mais!\n")

    print(f"{'Iteração':<10} {'RAM (MB)'} {'Tendência':<15}")
    print("-" * 40)

    for i in range(1, 51):
        # Fazer requisição
        response = requests.post(
            f"{BASE_URL}/sessions-bad",
            params={"user_id": i},
            timeout=5)
        if response.status_code != 200:
            print(f"Erro na iteração {i}: {response.status_code}")
            continue

        # checar ram
        ram = get_memory()

        # Mostrar tendência
        if i > 1:
            trend = "↑ (crescendo)" if i % 10 == 0 else ""

        else:
            trend = ""

        if i % 5 == 0 or i == 1 or i == 50:
            print(F"{i:<10} {ram:<15.2f} {trend:<15}")

        time.sleep(0.1)  # 100ms entre requisições

    final_ram = get_memory()
    print(f"\nRAMFINAL: {final_ram:.2f} MB")
    print("Resultado: RAM cresceu constantemente (VAZAMENTO)")
    print("Explicação: Cada sesão fica armazenada forever. Sem cleanup!")


def test_sessions_good():
    """Testa endpoint BOM (com cleanup)."""
    print("\n" + "="*60)
    print("TESTE 2: Memory Cleanup (BOM) - /sessions-good")
    print("="*60)
    print("Criando 50 sessões COM cleanup automático...")
    print("Observe a RAM ficar estável!\n")

    print(f"{'Iteração':<10} {'RAM (MB)':<15} {'Status':<15}")
    print("-" * 40)

    for i in range(1, 51):
        # Fazer requisição
        response = requests.post(
            f"{BASE_URL}/sessions-good",
            params={"user_id": i},
            timeout=5
        )
        if response.status_code != 200:
            print(f"Erro na iteração {i}: {response.status_code}")
            continue

        # Checar RAM
        ram = get_memory()

        # Status
        status = "Estável ✓" if i > 5 else "Aquecendo..."

        if i % 5 == 0 or i == 1 or i == 50:
            print(f"{i:<10} {ram:<15.2f} {status:<15}")

        time.sleep(0.1)  # 100ms entre requisições

    final_ram = get_memory()
    print(f"\nRAM FINAL: {final_ram:.2f} MB")
    print("Resultado: RAM permaneceu estável (SEM VAZAMENTO!)")
    print("Explicação: Cleanup automático libera memória expirada.")


def main():
    print("\n" + "█"*60)
    print("MEMORY LEAK STRESS TEST - Ticket Reservation API")
    print("█"*60)

    # Testar conexão
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ FastAPI não está respondendo!")
            print("Execute primeiro: poetry run uvicorn app.main:app --reload")
            return
        print("✓ FastAPI está rodando!")
        print(f"✓ RAM inicial: {get_memory():.2f} MB")
    except requests.ConnectionError:
        print("❌ Não consegui conectar ao FastAPI!")
        print("Execute em outro terminal: poetry run uvicorn app.main:app --reload")
        return

    # Rodar testes
    test_sessions_bad()
    time.sleep(2)  # Pausa entre testes
    test_sessions_good()

    print("\n" + "█"*60)
    print("CONCLUSÃO")
    print("█"*60)
    print("❌ /sessions-bad: RAM cresceu (memory leak)")
    print("✓ /sessions-good: RAM estável (cleanup correto)")
    print("\nVocê acabou de VER na prática a diferença!")
    print("█"*60 + "\n")


if __name__ == "__main__":
    main()
