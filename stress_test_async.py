#!/usr/bin/env python
"""
Stress test: Enviar 5 requisições simultâneas
Comparar tempo de sync vs async
"""

import requests
import time
import concurrent.futures

BASE_URL = "http://localhost:8000"


def test_sync():
    """Faz 5 requiçoes sincronas (uma a uma)"""
    print("\n" + "="*60)
    print("TESTE 1: 5 Requisiçoes SYNC (uma por uma)")
    print("="*60)

    start = time.time()

    for i in range(1, 6):
        response = requests.post(
            f"{BASE_URL}/reserve-sync",
            params={"event_id": 1, "quantity": 1},
            timeout=10
        )
        if response.status_code != 200:
            print(f"ERRO API: {response.status_code} - {response.text}")
        elapsed_req = response.json().get("elapsed_seconds", 0)
        print(f"Requisição {i}: {elapsed_req:.2f}s")

    total_sync = time.time() - start

    print(f"\nTempo TOTAL (5 requisiçoes): {total_sync:.2f}s")
    print("Esperado: 5s (5 x 3s cada)")
    return total_sync


def test_async_parallel():
    """faz 5 requisiçoes assincronamente (em paralelo)"""
    print("\n" + "="*60)
    print("TESTE 2: 5 Requisiçoes ASYNC (em paralelo)")
    print("="*60)

    def make_request(i):
        reponse = requests.post(
            f"{BASE_URL}/reserve-async",
            params={"event_id": 1, "quantity": 1},
            timeout=10
        )
        elapsed_req = reponse.json().get("elapsed_seconds", 0)
        print(f"Requisição {i}: {elapsed_req:.2f}s")
        return reponse
    start = time.time()

    # Usar ThreadPoolExecutor para simular concorrência
    # (Não é async puro, mas mostra o conceito)

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(1, 6)]
        concurrent.futures.wait(futures)

    total_async = time.time() - start
    print(f"\nTempo TOTAL (5 requisições em paralelo): {total_async:.2f}s")
    print(f"Esperado: ~1-2s (porque cada uma demora ~1s, não sequencial)")
    return total_async


def main():
    print("Teste de Conexão FastAPI...")
    try:
        reponse = requests.get(f"{BASE_URL}/health", timeout=2)
        if reponse.status_code == 200:
            print("FastAPI está rodando!")
        else:
            print("FastAPI retornou erro")
            return
    except requests.ConnectionError:
        print("Não consegui conectar a FastAPI")
        print("execute em outro terminal: poetry run uvivorn app.main:app--reload")
        return

    sync_time = test_sync()
    async_time = test_async_parallel()

    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Sync (sequencial):    {sync_time:.2f}s")
    print(f"Async (paralelo):     {async_time:.2f}s")
    print(f"Speedup:              {sync_time/async_time:.1f}x mais rápido")
    print("="*60)


if __name__ == "__main__":
    main()
