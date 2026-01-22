from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import time
from datetime import datetime, timedelta
from typing import List
from app.config import get_db, engine, Base
from app.models import User, Event, Ticket
from app.schemas import (
    UserCreate, UserResponse,
    EventCreate, EventResponse, EventWithTicketsResponse,
    TicketCreate, TicketResponse
)

# Criar aplicação
app = FastAPI(title="Ticket reservation API - Semana 3")

# Criar tabelas no banco (automatico)
Base.metadata.create_all(bind=engine)

# ═══════════════════════════════════════════════════════════
#
# SEED: Gerar dados fake para testes
# ═══════════════════════════════════════════════════════════


@app.post("/seed")
def seed_database(session: Session = Depends(get_db)):
    # 1. Limpar banco (Staging)
    session.query(Ticket).delete()
    session.query(Event).delete()
    session.query(User).delete()

    # Commit imediato para garantir que o banco limpe MESMO se der erro depois
    session.commit()

    print("--- Banco Limpo ---")  # Debug no terminal

    # 2. Criar Usuários
    users = []  # <--- AQUI ESTAVA O ERRO (Faltava inicializar a lista)
    for i in range(1, 11):
        user = User(
            name=f"Creator {i}",
            email=f"creator{i}@example.com"
        )
        session.add(user)
        users.append(user)  # <--- Indentação correta (dentro do for)

    session.commit()  # Salva usuários para gerar IDs
    print(f"--- {len(users)} Usuários Criados ---")

    # 3. Criar Eventos
    events = []
    for i, user in enumerate(users):
        event = Event(
            name=f"Concert {i+1}",
            description=f"Show top {i+1}",
            date=datetime.now(),
            price=100.0,
            creator_id=user.id
        )
        session.add(event)
        events.append(event)

    session.commit()  # Salva eventos
    print(f"--- {len(events)} Eventos Criados ---")

    # 4. Criar Ingressos
    for event in events:
        for i in range(50):  # 50 ingressos por evento
            ticket = Ticket(
                seat_number=f"Seat {i}",
                price=event.price,
                event_id=event.id
            )
            session.add(ticket)

    session.commit()  # Salva ingressos

    return {
        "message": "Seed Realizado com Sucesso!",
        "users": len(users),
        "events": len(events)
    }
# ═══════════════════════════════════════════════════════════
#
# /events-bad: DEMONSTRAR N+1 (lento demais)
# ═══════════════════════════════════════════════════════════


@app.get("/events-bad")
def get_events_bad(session: Session = Depends(get_db)) -> dict:
    """
    N+1 PROBLEMA: Pega eventos, depois acessa .tickets de cada um.
    ❌
    SQL gerado:
    Query 1: SELECT * FROM events;
    Query 2: SELECT * FROM tickets WHERE event_id = 1;
    Query 3: SELECT * FROM tickets WHERE event_id = 2;
    Query N: SELECT * FROM tickets WHERE event_id = N;
    Tempo esperado:
    10 eventos: ~50-100ms
    100 eventos: ~500ms-1s
    1000 eventos: ~5-10s (TRAVA!)
    """
    start = time.time()

    # Query 1: pega todos os eventos
    events = session.query(Event).all()

    # Aqui começam os prolbemas! Para CADA evento:
    events_data = []
    for event in events:
        # PROBLEMA: Isso dispara 1 query por evento!
        # SELECT * FROM tickets WHERE event_id = {event.id}
        ticket_count = len(event.tickets)

        events_data.append({
            "id": event.id,
            "name": event.name,
            "ticket_count": ticket_count
        })

        elapsed = time.time() - start

        return {
            "method": "BAD (N+1)",
            "elapsed_seconds": round(elapsed, 3),
            "events_count": len(events_data),
            "events": events_data,
            "warning": f" Isto dispara ~{len(events_data) + 1} queries! (1 + {len(events_data)})"
        }


# ═══════════════════════════════════════════════════════════
# /events-good: SOLUÇÃO COM JOINEDLOAD (rápido)
# ═══════════════════════════════════════════════════════════

@app.get("/events-good")
def get_events_good(session: Session = Depends(get_db)) -> dict:
    """
    EAGER LOADING: Usa joinedload para trazer TUDO em 1 query.
    ✅
    SQL gerado:
    └─ Query 1: SELECT events.*, tickets.* FROM events LEFT JOIN tickets...
    Tempo esperado:
    ├─ 10 eventos: ~5-10ms
    ├─ 100 eventos: ~10-20ms
    └─ 1000 eventos: ~20-50ms (relâmpago!)
    """
    start = time.time()

    # SOLUÇÃO: joinedload(Event.tickets)
    # "Carregue os tickets junto com cada evento numa única query"
    events = session.query(Event).options(joinedload(Event.tickets)).all()

    # Agora .tickets já esta em memória (nenhuma query extra!)

    events_data = []
    for event in events:
        ticket_count = len(event.tickets)

        events_data.append({
            "id": event.id,
            "name": event.name,
            "ticket_count": ticket_count

        })
    elapsed = time.time() - start

    return {
        "method":  "good (Eager Loading)",
        "elapsed_seconds": round(elapsed, 3),
        "events_count": len(events_data),
        "events": events_data,
        "success": "Isto dispara apenas 1 query! (com JOIN)"
    }

# ═══════════════════════════════════════════════════════════
# /compare - Comparar Bad vs Good
# ═══════════════════════════════════════════════════════════


@app.get("/compare")
def compare_performace(session: Session = Depends(get_db)) -> dict:
    """
    Executa ambas as rotas e compara performance.
    Resultado: Você vai ver a diferença de velocidade.
    """
    # Bad version
    start_bad = time.time()
    events_bad = session.query(Event).all()
    for event in events_bad:
        _ = len(event.tickets)
    time_bad = time.time() - start_bad

    # Versão Boa
    start_good = time.time()
    events_good = session.query(Event).options(
        joinedload(Event.tickets)
    ).all()
    for event in events_good:
        _ = len(event.tickets)
    time_good = time.time() - start_good
    # Calcular diferença
    speedup = time_bad / time_good if time_good > 0 else 0

    return {
        "bad_time_seconds": round(time_bad, 4),
        "good_time_seconds": round(time_good, 4),
        "speedup_factor": f"{speedup:.2f}x mais rapido",
        "veredict": "Eager loading é a vitoria" if time_good < time_bad else "empate (muito rapido)"
    }

# ═══════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════


@app.get("/health")
def health_check() -> dict:
    """Simples health check."""
    return {"status": "online", "week": "Semana 3 - Database & N+1"}
