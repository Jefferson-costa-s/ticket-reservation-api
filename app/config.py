import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db"  # Cria arquivo app.db na raiz
)

if "sqlite" in DATABASE_URL:
    # SQLite precisa desssa config para evitar "database is locked"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True
    )
else:
    # Para PostgreSQL (depois)
    engine = create_engine(DATABASE_URL, echo=False)

# Criar sessão
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
