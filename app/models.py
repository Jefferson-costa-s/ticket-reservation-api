from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
# Importar Base do config para garantir que o Alembic e o main.py enxerguem as tabelas
from app.config import Base
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String, index=True)
    email: str = Column(String, unique=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=True)
    events = relationship(
        "Event",
        back_populates="creator",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Event(Base):
    __tablename__ = "events"

    id: int = Column(Integer, primary_key=True, index=True)
    name: str = Column(String, index=True)
    description: str = Column(String)
    date: datetime = Column(DateTime, default=datetime.utcnow)
    price: float = Column(Float)

    creator_id: int = Column(Integer, ForeignKey("users.id"))

    creator = relationship(
        "User",
        back_populates="events"
    )

    # CORREÇÃO: Removido ": list"
    tickets = relationship(
        "Ticket",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event(id={self.id}, name={self.name}, tickets={len(self.tickets)})>"


class Ticket(Base):
    __tablename__ = "tickets"

    id: int = Column(Integer, primary_key=True, index=True)
    seat_number: str = Column(String)
    price: float = Column(Float)
    event_id: int = Column(Integer, ForeignKey("events.id"), index=True)
    is_reserved: bool = Column(Boolean, default=False, index=True)
    reserved_at: datetime | None = Column(DateTime, nullable=True)
    user_id: int | None = Column(
        Integer, ForeignKey("users.id"), nullable=True)
    event = relationship("Event", back_populates="tickets")

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, seat={self.seat_number})>"
