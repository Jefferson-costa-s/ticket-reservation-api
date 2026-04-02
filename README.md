# Ticket Reservation API

API REST para reserva de ingressos construída com FastAPI e PostgreSQL,
focada em resolver problemas reais de alta concorrência e integridade de dados.

## Stack

- **Runtime:** Python 3.11+ | FastAPI (async)
- **Banco de dados:** PostgreSQL | Redis
- **ORM / Migrations:** SQLAlchemy 2.0 | Alembic
- **Auth / Validação:** JWT | Pydantic | Passlib (Bcrypt)
- **Gerenciamento:** Poetry

## Decisões técnicas

**Controle de concorrência**
Overbooking prevenido com row-level locks (`SELECT ... FOR UPDATE SKIP LOCKED`)
diretamente no PostgreSQL. Transações atômicas garantem que dois usuários
simultâneos não reservem o mesmo assento.

**Otimização de queries**
N+1 eliminado com `joinedload` no SQLAlchemy. Consultas que antes geravam
N+1 roundtrips ao banco passaram a executar em join único.

**Autenticação**
Access token de curta duração + refresh token em cookie HttpOnly (prevenção
de XSS). Logout real implementado com blacklist de tokens no Redis.

**Validação de entrada**
Payloads validados na camada Pydantic antes de atingir o banco.
Dados inválidos ou maliciosos são rejeitados na borda da aplicação.

## Executar localmente

**Pré-requisitos:** Python 3.11+, Poetry, PostgreSQL e Redis em execução.

```bash
git clone https://github.com/jeffersoncosta-dev/ticket-reservation-api.git
cd ticket-reservation-api
poetry install
```

Crie `.env` na raiz:

```env
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/ticket_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=sua_chave_secreta_jwt_aqui
ALGORITHM=HS256
```

```bash
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```
