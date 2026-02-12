from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from redis import Redis
import os

from app.config import get_db
from app.models import User
from app.schemas import UserCreate
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    REFRESH_TOKEN_EXPIRE_DAYS
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Cliente Redis para blacklist
redis_client = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True
)

# ════════════════════════════════════════════════════════════
# POST /auth/register - Criar novo usuário
# ════════════════════════════════════════════════════════════


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    session: Session = Depends(get_db),
) -> dict:
    """
    Cria novo usuário no banco.

    Validações (feitas pelo Pydantic na Semana 5):
    - Email: RFC 5322 compliant
    - Senha: mínimo 8 chars + número + maiúscula
    """
    # Verificar se email já existe
    existing = session.query(User).filter(
        User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado"
        )

    # Criar usuário com senha hasheada
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hash_password(user_data.password)  # bcrypt hash
    )
    session.add(user)
    session.commit()
    session.refresh(user)  # Pega o ID gerado pelo banco

    return {
        "id": user.id,
        "email": user.email,
        "message": "Usuário criado com sucesso"
    }


# ════════════════════════════════════════════════════════════
# POST /auth/login - Login com email e senha
# ════════════════════════════════════════════════════════════

@router.post("/login")
def login(
    response: Response,
    # 🛠️ AJUSTE 1: Usar OAuth2PasswordRequestForm permite usar o botão de cadeado do Swagger
    # Se preferir manter JSON, use um Schema (ex: LoginSchema)
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_db),
) -> dict:
    
    # 1. Buscar usuário ('username', é o email)
    user = session.query(User).filter(User.email == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 2. Verificar senha
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    # 3. Criar tokens
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # 4. Armazenar Refresh Token no Redis
    # Engenharia: Isso permite o "Logout Remoto" (Invalidação de sessão)
    try:
        redis_client.setex(
            f"refresh_token:{user.id}",
            REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
            refresh_token
        )
    except Exception as e:
        # Se o Redis falhar, logamos o erro mas não travamos o login 
        # (Trade-off: disponibilidade vs rastreabilidade)
        print(f"Erro Redis: {e}")

    # 5. Configurar cookie HttpOnly
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, # ⚠️ IMPORTANTE: Mude para True em produção (HTTPS)
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )

    # 6. Retorno padrão OAuth2
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800 
    }


@router.post("/refresh")
def refresh_token(
    request: Request,
    response: Response,
) -> dict:
    """
    Renova Access Token usando Refresh Token do cookie.

    Fluxo:
    1. Lê Refresh Token do cookie HttpOnly
    2. Valida token (assinatura + expiração)
    3. Verifica se não foi revogado (Redis blacklist)
    4. Cria novo Access Token
    5. Retorna novo Access no JSON
    """
    # 1. Ler cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token ausente"
        )

    # 2. Validar token
    user_id = verify_refresh_token(refresh_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado"
        )

    # 3. Verificar se token foi revogado (blacklist)
    stored_token = redis_client.get(f"refresh_token:{user_id}")
    if stored_token != refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revogado (logout foi feito)"
        )

    # 4. Criar novo Access Token
    new_access_token = create_access_token(user_id)

    # 5. Retornar
    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": 1800
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
) -> dict:
    """
    Logou real: revoga o Refresh token e limpa cookie.

    Fluxo:
    1. Lê o refresh token do cookie
    2. decodigica para pegar user_id
    3. APAGA TOKEN DO REDIS (Blacklist)
    4. apaga cookie do navegador
    """
    # 1. ler cookie
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            # 2. Decodificar para pegar user_id
            user_id = verify_refresh_token(refresh_token)
            if user_id:
                # 3. Apagar do redis (revoga token)
                redis_client.delete(f"refresh_token:{user_id}")
        except Exception:
            # Token invalido mas não é erro critico
            pass

    # 4. Apagar cookie do navegador
    response.delete_cookie("refresh_token")
    return {"message": "Logout realizado com sucesso"}
