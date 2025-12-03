"""API路由模块"""
from .servers import router as servers_router
from .quotes import router as quotes_router
from .history import router as history_router
from .blocks import router as blocks_router

__all__ = ["servers_router", "quotes_router", "history_router", "blocks_router"]

