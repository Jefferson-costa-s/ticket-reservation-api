from pydantic import BaseModel, Field, field_validator, EmailStr
from datetime import datetime
from typing import List, Optional

# ----------------------
# USER SCHEMAS
# ----------------------


class UserBase(BaseModel):
    """Base para User (campos comuns)"""
    name: str
    email: str


class UserCreate(UserBase):
    """Schema para criar novo usuario.

    Validaçoes:
    - Email: RFC 5322 COMPLIANT (USER@DOMAIN.COM)
     - Senha: minimo 8 caracteres """

    email: EmailStr  # valida formato de email automaticamente
    password: str = Field(..., min_length=8, max_length=100)

    @field_validator('password')
    def password_strength(cls, v: str) -> str:
        """
        Regras de senha forte:
        - Pelo menos 1 numero
        - Pelo menos 1 letra maiuscula
        - pelo menos 1 letra minuscula
        """
        if not any(char.isdigit() for char in v):
            raise ValueError('Senha deve conter pelo menos 1 numero')

        if not any(char.isupper() for char in v):
            raise ValueError('Senha deve conter pelo menos 1 letra maiúscula')
        if not any(char.islower() for char in v):
            raise ValueError('Senha deve conter pelo menos 1 letra minuscula')
        return v



class UserResponse(UserBase):
    """Para retornar usuario (resposta da API)"""
    id: int

    class Config:  # CORREÇÃO: "C" maiúsculo
        from_attributes = True

# ----------------------
# EVENT SCHEMAS
# ----------------------


class EventBase(BaseModel):
    """Base para event"""
    name: str
    description: str
    date: datetime
    price: float


class EventCreate(BaseModel):
    """Schema para criar novo evento.
        Validações:
        - Nome: 1-100 caracteres, sem SQL injection
        - Total tickets: > 0, ≤ 10.000
        - Preço: > 0
        - Data: não pode ser no passado"""
    name: str = Field(..., min_length=1, max_length=100)
    total_tickets: int = Field(..., gt=0, le=10000)
    price: float = Field(..., gt=0)
    date: datetime

    @field_validator('name')
    def sanitize_name(cls, v: str) -> str:
        """
        Impede caracteres perigosos no nome do evento, 
        SQL injection comum: evento' OR '1'='1
        """
        forbidden = ["'", '"', '--', '/*', '*/']
        if any(char in v for char in forbidden):
            raise ValueError('Nome contém caracteres proibidos')
        return v.strip()

    @field_validator('date')
    def ckeck_future_date(cls, v: datetime) -> datetime:
        """
        Regra de negócio: evento não pode ser agendado no passado.
        """
        if v < datetime.utcnow():
            raise ValueError("Data do eevnto não pode ser no passado")
        return v


class EventResponse(EventBase):
    """Para retornar evento"""
    id: int
    creator_id: int

    class Config:
        from_attributes = True  # CORREÇÃO: "attributes" escrito certo

# ----------------------
# TICKET SCHEMAS
# ----------------------


class TicketBase(BaseModel):
    """Base para ticket"""
    seat_number: str
    price: float


class TicketCreate(TicketBase):
    """Para criar novo ingresso"""
    event_id: int
    # CORREÇÃO: Removido "id: int" (o banco cria o ID sozinho)


class TicketResponse(TicketBase):  # CORREÇÃO: Classe que faltava!
    """Para retornar ingresso"""
    id: int
    event_id: int
    is_reserved: bool = False

    class Config:
        from_attributes = True

# ----------------------
# EVENT WITH TICKETS
# ----------------------


class EventWithTicketsResponse(EventResponse):
    """Para retornar evento com seus ingressos"""
    tickets: List[TicketResponse] = []


class TicketReserveRequest(BaseModel):
    """
    Schema para reservar ingressos.
    Validações:
    - event_id: > 0
    - user_id: > 0
    - quantity: entre 1 e 10 (limite de negócio)
    """
    event_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    quantity: int = Field(default=1, gt=0, le=10)


class TicketReserveResponse(BaseModel):
    ticket_id: int
    event_id: int
    user_id: int
    reserved_at: datetime
