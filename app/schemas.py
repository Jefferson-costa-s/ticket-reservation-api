from pydantic import BaseModel
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
    """Para criar novo usuario"""
    pass


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


class EventCreate(EventBase):
    """Base para criar Event"""
    creator_id: int


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
