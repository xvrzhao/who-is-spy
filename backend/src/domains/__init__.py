from fastapi import APIRouter

from .game.endpoints import router as game_router

router = APIRouter(prefix="/api")

router.include_router(game_router)
