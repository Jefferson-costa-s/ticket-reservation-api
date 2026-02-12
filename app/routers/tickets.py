from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select
from datetime import datetime

from app.config import get_db
from app.models import Ticket, Event, User
from app.schemas import TicketReserveRequest, TicketReserveResponse
from app.core.dependencies import get_current_user

# Define o prefixo. Todas as rotas aqui serão /tickets/...
router = APIRouter(prefix="/tickets", tags=["tickets"])


# FUNÇÕES AUXILIARES (Lógica interna)

def check_user_ticket_limit(user_id: int, session: Session) -> None:
    """
    Regra de negócio: usuario não pode ter mais de 5 reservas ativas.
    """
    # Conta quantos tickets reservados este ID possui
    active_count = session.query(func.count(Ticket.id)).filter(
        Ticket.owner_id == user_id, 
        Ticket.status == "reserved" 
    ).scalar()

    if active_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Você já atingiu o limite de 5 reservas ativas."
        )

# ROTAS
@router.post("/reserve", response_model=TicketReserveResponse, status_code=status.HTTP_201_CREATED)
def reserve_ticket(
    req: TicketReserveRequest,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # 🔒 BLINDAGEM: JWT Obrigatório
):
    """
    Reserva um ingresso de forma atômica (ACID).
    """
    
    # 1. Validar limite de tickets do usuario LOGADO
    check_user_ticket_limit(current_user.id, session)

    try:
        # 2. Iniciar transação explícita
        with session.begin():
            
            # 2.1 Buscar evento
            event = session.get(Event, req.event_id)
            if not event:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Evento não encontrado"
                )

            # 2.2 Montar Query para buscar 1 ingresso livre
            query = select(Ticket).where(
                Ticket.event_id == req.event_id,
                Ticket.status == "available" # Garante que está livre
            )

            # 2.3 Aplicar Row Lock (FOR UPDATE) - Proteção contra Race Condition
            # Se não for SQLite (que não suporta isso bem), trava a linha no Postgres
            if "sqlite" not in str(session.bind.url):
                query = query.with_for_update(skip_locked=True)
            
            # Limita a 1 resultado
            query = query.limit(1)

            # Executa
            result = session.execute(query)
            ticket = result.scalar_one_or_none()

            if not ticket:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Esgotado! Nenhum ingresso disponível."
                )

            # 3. Atualizar o Ticket (A Compra Real)
            ticket.status = "reserved"
            ticket.owner_id = current_user.id  # Usa o ID do token, ignora JSON
            ticket.reserved_at = datetime.utcnow()
            
            # session.commit() é automático ao sair do 'with session.begin()'

            # 4. Retornar
            return TicketReserveResponse(
                id=ticket.id,
                status="reserved",
                event_id=ticket.event_id,
                user_id=current_user.id, # Confirmação visual de quem comprou
                created_at=datetime.utcnow() # Apenas para cumprir o schema
            )

    except HTTPException as e:
        # Re-lança erros HTTP conhecidos (404, 409)
        raise e
    except Exception as e:
        # Captura erros inesperados de banco
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno na reserva: {str(e)}"
        )