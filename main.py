"""TDX数据源管理服务 - FastAPI应用入口"""
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from config import TDX_SERVERS
from app.connection.pool import tdx_connection_pool
from app.connection.client import tdx_client
from app.api import servers_router, quotes_router, history_router, blocks_router
from app.mcp.tools import get_mcp_app
from app.services.cache import CacheService

# 创建 FastAPI 应用
app = FastAPI(title="TDX数据源管理服务", version="1.0.0")

# 允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 线程池用于执行阻塞操作
executor = ThreadPoolExecutor(max_workers=10)

# 注册API路由
app.include_router(servers_router)
app.include_router(quotes_router)
app.include_router(history_router)
app.include_router(blocks_router)

# 挂载MCP
mcp_app = get_mcp_app()
if mcp_app:
    app.mount("/mcp", mcp_app)


@app.on_event("startup")
async def preload_caches():
    """启动时预加载缓存"""
    try:
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        cache_service = CacheService(cache_dir)
        
        # 加载服务器配置
        _servers, current = cache_service.get_servers_config(TDX_SERVERS)
        
        if current:
            try:
                tdx_connection_pool.set_server(current)
                tdx_connection_pool.reset_pool()
                tdx_client.current_server = current
            except Exception:
                pass
        
        # 预加载板块和行业数据
        blocks_path = os.path.join(cache_dir, "blocks.json")
        industries_path = os.path.join(cache_dir, "industries.json")
        
        if not os.path.exists(blocks_path):
            asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_stock_blocks)
        if not os.path.exists(industries_path):
            asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_industry_info)
    except Exception:
        pass


@app.get("/")
async def root():
    """服务根路径"""
    return {"message": "TDX数据源管理服务", "version": "1.0.0"}


@app.get("/config", response_class=HTMLResponse)
async def config_page():
    """配置页面"""
    html_path = os.path.join(os.path.dirname(__file__), "app", "static", "config.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "<h1>配置页面加载失败</h1>"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6999)

