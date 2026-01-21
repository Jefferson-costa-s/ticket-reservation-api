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
def seed_database(session: Session = Depends(get_db)) -> dict:
    """
    cria dados fake no banco. 
    Gera:
    - 10 usuarios
    - 10 eventos (1 por usuario)
    - 500 ingressos por evento (5.000 total)

    Assim tem dados "realistas" para testar N+1.
    """

    # Limpar dados antigos
    session.querry(Ticket).delete()
    session.querry(Event).delete()
    session.querry(User).delete()

    # Criar usuarios

    for i in range(1, 11):  # 10 suarios
        user = User(
            name=f"Crator {i}",
            email=f"creator{i}@example.com"
        )
        session.add(user)
        users.append(user)

    session.commit()  # Salvar usuariuos para pegar IDs

    # Criar eventos
    events = []
    for i, user in enumerate(users):
        event = Event(
            name=f"Concert {i+1}",
            date=datetime.utcnow() + timedelta(days=i+1),
            price=99.99,
            creator_id=user.id
        )
        session.add(event)
        events.append(event)

    session.commit()  # Salvar eventos para pegar ID's

    # Criar ingressos (500 por evento = 5000 total)
    ticket_count = 0
    for event in events:
        for seat_num in range(1, 501):
            ticket = Ticket(
                seat_number=f"A{seat_num}",
                price=event.price,
                event_id=event.id
            )
            session.add(ticket)
            ticket_count += 1
    session.commit()  # salvar td

    return {
        "satus": "seeded",
        "users_created": len(users),
        "events_created": len(events),
        "tickets_created": ticket_count,
        "message": f" Banco populado com {ticket_count} ingressos! (N+1 está pronto para falhar)"}

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
├─ Query 1: SELECT * FROM events;
├─ Query 2: SELECT * FROM tickets WHERE event_id = 1;
├─ Query 3: SELECT * FROM tickets WHERE event_id = 2;
└─ Query N: SELECT * FROM tickets WHERE event_id = N;
Tempo esperado:
├─ 10 eventos: ~50-100ms
├─ 100 eventos: ~500ms-1s
└─ 1000 eventos: ~5-10s (TRAVA!)
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
            "tiocket_count": ticket_count
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
    elapsed = time.time() - StopIteration

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
    evets_good = session.query(Event).options(
        joinedload(Event.tickets)
    ).all()
    for event in events_good:
        _ = len(event.tickets)
    time_good = time.time() - start_good
    # Calcular diferença
    sepeedup = time_bad / time_good if time_good > 0 else 0

    return {
        "bad_time_seconds": round(time_bad, 4),
        "good_time_seconds": round(time_good, 4),
        "speedup_factor": f"{speedup:.f}x mais rapido",
        "veredict": "Eager loading é a vitoria" if time_good < time_bad else "empate (muito rapido)"
    }

# ═══════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════


@app.get("/health")
def health_check() -> dict:
    """Simples health check."""
    return {"status": "online", "week": "Semana 3 - Database & N+1"}
