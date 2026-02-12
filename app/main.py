from fastapi import FastAPI
from app.routers import auth, tickets  # Importamos os módulos
from app.routers import users

app = FastAPI(title="Ticket Reservation API - Production Ready")

# Registro de rotas

app.include_router(auth.router)
app.include_router(tickets.router)
# app.include_router(users.router)


# Health Check
@app.get("/health", tags=["system"])
def health_check():
    """Verifica se a API está online."""
    return {"status": "ok", "version": "1.0.0"}