from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from app.schemas import UserCreate
from app.modeals import User
from app.config import get_db
from fastapi import APIRouter, Depdends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from redis import Redis
importos

# POST / auth/register - Criar novo usuario


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    session: Session = Depends(get_db),
) -> dict:
    """
    Cria novo usuario no banco.
    validaçoes (feitas pelo pydantic na semana 5 ):
    - Email: RFC 5322 COMPLIANT
    - sENHA: MINIMO 8 CHARS + NUMERO + MAIUSCULA
    """
    # Verificar se email já existe
    existing = session.querry(User).filter(
        User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado")
    # Criar usuario com senha hasheada
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password)  # bcrypt hash
    )
    session.add(user)
    session.commit()
    session.refresh(user)  # Pega o ID gerado pelo banco

    return {
        "id": user.id,
        "email": user.email,
        "message": "Usuario criado com sucesso"
    }

# POST /auth/login - Login com email e senha


@router.post("/login")
def login(
    email: str,
    password: str,
    response: Response,
    session: Session = Depends(get_db)
) -> dict:
    """
    Login: retorna Access Token (JSON) + Refresh Token (HttpOnly Cookie).

    Fluxo:
    1. Busca o usuario por email
    2. Verifica senha (bcypt.verify)
    3. Cria Acess Token (30 min)
    4. Cria refresh token (7 dias)
    5. Salva refresh token no cookie httpOnly 
    6. retorna acess no JSON
    """
    # 1. Buscar usuario
    user = session.querry(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 2 . verificar a senha
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 3. Criar tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # 4. armazenar refresh token no redis (para rastreamento/revogação)
    redis_client.setex(
        f"refresh_token:{user.id}",
        REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,  # 7 dias em segundos
        refresh_token
    )
    # 5. Configurar cookie HttpOnlycom Refresh Token
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  # JavaScript não consegue ler
        secure=True,  # só envia via HTTPS (localmente ignora)
        samesite="lax",  # Protege contra CSRF
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )
    # Retornar Acess Token no corpo da resposta
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800  # 30 mins em segundos
    }
