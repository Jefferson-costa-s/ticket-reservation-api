from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import get_db
from app.models import User
from app.core.security import verify_access_token

# Esquema de segurança bearer token
security = HTTPBearer()

def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        session: Session = Depends(get_db)
        ) -> User:
    """
    Dependencia para rotas protegidas
    extrai token do header:
    authorization: bearer eyJhbGc...
    valida token e retorna usuario autenticado
    """
    # Extrair token do header
    token = credentials.credentials

    # validar token
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou exipirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    #Busca usuario no banco
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario não encontrado"
    )
    return user