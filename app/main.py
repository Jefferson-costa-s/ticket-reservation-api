from fastapi import FastAPI, HTTPException, Depends
from typing import Dict, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
import psutil
import os
from sqlalchemy.orm import Session
from app.config import get_db
import asyncio
import time

app = FastAPI(title="Ticket Reservation API")


async def simulate_slow_io(delay: float = 1.0) -> dict:
    """
    Simula uma operação lenta (como query ao banco).
    """
    await asyncio.sleep(delay)
    return {"status": "ok"}

# Global sessions (RUIM: sem cleanup)
sessions_bad: Dict[str, dict] = {}

# Global sessions (BOM: com TTL)
sessions_good: Dict[str, dict] = {}
SESSION_TTL_SECONDS = 0


@app.get("/health")
def health():
    """Health check simples"""
    return {"status": "ok"}


@app.get("/memory")
def memory_usage():
    """Monitorar RTAM em tempo real."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        "rss_mb": mem_info.rss / (1024 * 1024),  # memoria residente
        "vms_mb": mem_info.vms / (1024 * 1024),  # memoria virtual
    }


@app.post("/sessions-bad")
def create_sessions_bad(user_id: int):
    """RUIM: acumula em memoria sem limite."""
    if user_id < 0:
        raise HTTPException(status_code=400, detail="user_id must be positive")

    session_id = f"sess_{user_id}_{len(sessions_bad)}"
    sessions_bad[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "data": "x" * 100000,  # 100KB de dados
    }
    return {"session_id": session_id}


@app.post("/sessions-good")
def create_session_good(user_id: int):
    """BOM: com TTL."""
    if user_id < 0:
        raise HTTPException(
            status_code=400, detail="user_id must be a positive")

    session_id = f"sess_{user_id}_{len(sessions_good)}"
    sessions_good[session_id] = {
        "user_id": user_id,
        "created_at": datetime.now(),
        "data": "x" * 100000,
    }
    cleanup_expired_sessions()
    return {"session_id": session_id}


@app.post("/reserve-sync")
def reserve_sync(event_id: int, quantity: int) -> dict:
    """
    ❌ RUIM: Bloqueante - tudo sequencial
    Simula reserva com 3 validações de 1 segundo cada.
    Sem async/await, tudo acontece UM POR UM.
    """
    if event_id <= 0 or quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid input")

    start = time.time()

    # Validação 1: evento existe? (1 segundo)
    time.sleep(1.0)  # BLOQUEIA a thread
    validation1 = {"check": "event_exists", "result": True}

    # validação 2: Ingeressos disponivels? (1 segundo)
    time.sleep(1.0)  # BLOQUEIA a thread
    validation2 = {"check": "tickets_available", "result": True}

    # Validação 3: Usuario pode reservar? (1 segundo)
    time.sleep(1.0)  # BLOQUEIA a thread
    validation3 = {"check": "user_can_reserve", "result": True}

    elapsed = time.time() - start

    return {
        "status": "reserved",
        "elapsed_seconds": elapsed,
        "concurrency_mode": "sync (bloqueante)",
        "validations": [validation1, validation2, validation3]
    }


@app.post("/reserve-async")
async def reserve_async(event_id: int, quantity: int) -> dict:
    """
    BOM: Não-bloqueante - validações em paralelo
    ✅
    Simula reserva com 3 validações de 1 segundo cada.
    Com async/await e asyncio.gather, tudo acontece EM PARALELO.
    """
# Validação input
    if event_id <= 0 or quantity <= 0:
        raise HTTPException(status_code=400, detail="Invalid input")

    start = time.time()

    # PARALELO: 2 tarefas assincronamente
    results = await asyncio.gather(
        simulate_slow_io(1.0),  # Validação 1: Evento existe? (1s)
        simulate_slow_io(1.0),  # Validação 2: Ingeressos disponiveis? (1s)
        simulate_slow_io(1.0),  # Validação 3: Usuario pode reservar? (1s)
    )
    elapsed = time.time() - start
    # Extrair resultados
    validation1 = {"check": "event_exists",
                   "result": results[0]["status"] == "ok"}
    validation2 = {"check": "tickets_available",
                   "result": results[1]["status"] == "ok"}
    validation3 = {"check": "user_can_reserve",
                   "result": results[2]["status"] == "ok"}

    return {
        "status": "reserved",
        "elapsed_seconds": elapsed,
        "concurrency_mode": "async (não-bloqueante)",
        "validations": [validation1, validation2, validation3]
    }


@app.get("/benchmark")
async def benchmark() -> dict:
    """
    Compara tempo de sync vs async.
    Roda ambas as rotas e mostra a diferença.
    """
    import httpx

    # Testar SYNC
    start_sync = time.time()
    async with httpx.AsyncClient() as client:
        response_sync = await client.post(
            "http://localhost:8000/reserve-sync",
            json={"event_id": 1, "quantity": 1}
        )
    sync_time = time.time() - start_sync

    # Testar Async
    start_async = time.time()
    async with httpx.AsyncClient() as client:
        response_async = await client.post(
            "http://localhost:8000/reserve-async",
            json={"event_id": 1, "quantity": 1}
        )
    async_time = time.time() - start_async
    speedup = sync_time / async_time

    return {
        "sync_time_seconds": round(sync_time, 2),
        "async_time_seconds": round(async_time, 2),
        "speedup_factor": f"{speedup:.1f}x mais rapido",
        "message": "Async é mais efeiciente que Sync!"
    }


def cleanup_expired_sessions():
    """Remove sessoes expiradas."""
    now = datetime.now()
    expired = [
        sid for sid, session in sessions_good.items()
        if (now - session["created_at"]).total_seconds() > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del sessions_good[sid]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
