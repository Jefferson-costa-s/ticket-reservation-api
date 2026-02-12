from fastapi import APIRouter, Depends

from app.models import User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/users", tags = ["users"])

@router.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Retorna perfil do usuario autenticado.
    requer: Authorizarion: Bearer <acces_token> 
    """
    return{
        "id":  current_user.id,
        "email": current_user.email,
        "message": "você está autenticado!"
    }