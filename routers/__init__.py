from .user import router as user_router
from .health import router as health_router
from .article import router as article_router
from .role import router as role_router
from .upload import router as upload_router
from .lab import router as lab_router
from .equipment import router as equipment_router

__all__ = ["user_router", "health_router", "article_router", "role_router", "upload_router", "lab_router", "equipment_router"]
