from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional
import os

# CONFIGURAÇOES DE SEGURANÇA

# Contexto para hash de senhasa (bcrypt)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Configuraçoes JWT
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-CHANGE-IN-PRODUCTION")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token de acesso: 30 minutos
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Token de renovação: 7 dias

# FUNÇOES DE HASH DE SENHA


def hash_password(password: str) -> str:
    """
    Gera hash bcrypt da senha.

    Bastidores:
    - Bcrypt adiciona 'salt' aleatorio (evita rainbow tables)
    - Custo computacional alto (lento de propósito, dificulta brute force)
    - Resultado: $2b$12$LQv3c1yq... (nunca igual mesmo senha igual)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
        Verifica se senha em texto puro confere com a hash armazenado

        Bastidores:
        - extrai o 'salt' do hash armazenado 
        - Aplica bcrypt na senha fornecida com esse salt
        - Compara os hashes (tempo constante, evita timing atacks)
    """
    return pwd_context.verify(plain_password, hashed_password)

# FUNÇOES DE JWT


def create_access_token(user_id: int) -> str:
    """
    Cria access Token (curto - 30 min).
    Payload
    - sub: user_id (subject - quem é o usuario)
    - type: 'access' (diferencia de refresh token )
    - exp: timestamp de expiração
    """
    payload = {
        # Subject: O ID do usuário (o dado mais importante)
        "sub": str(user_id),
        "type": "access",     # Metadado de negócio: é acesso ou refresh?
        # Expiration: Até quando isso vale?
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """
    Cria refresh token (longo - 7 dias).
    diferença tecnica: Expiraçao maior é type = 'refresh'.
    """
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> Optional[int]:
    """
    Valida access token e retorna user_id

    Batidores:
    - decodifica o token usando JWT_SECRET
    - verifica assinatura (previne tokens forjados)
    - verifica expiração (exp < now = token invalido)
    - verifica rype = 'access' (refresh token não serve aqui)

    retorna:
    - user_id(int) se valido
    - None se invalido/expirado
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        # Verificar tipo do token
        if payload.get("type") != "access":
            return None
        # extrair user_id
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        # Token invalido, expirado ou assinatura incorreta
        return None


def verify_refresh_token(token: str) -> Optional[int]:
    """
    Valida a resh token e retorna user_id.
    similar o verify_access_token, mas veirfica type = 'refres'.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None
