"""板块/行业API路由"""
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from ..connection.pool import tdx_connection_pool
from ..connection.client import tdx_client

router = APIRouter(prefix="/api", tags=["blocks"])
executor = ThreadPoolExecutor(max_workers=10)


@router.get("/blocks")
async def get_stock_blocks():
    """获取股票板块数据"""
    blocks = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_stock_blocks
    )
    
    if blocks is None:
        raise HTTPException(status_code=404, detail="板块数据获取失败")
    
    try:
        print(f"板块数据条数: {len(blocks) if blocks else 0}")
    except Exception:
        pass
    return {"blocks": blocks, "count": len(blocks) if blocks else 0}


@router.get("/industries")
async def get_industries():
    """获取行业信息数据"""
    industries = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_industry_info
    )
    
    if industries is None:
        raise HTTPException(status_code=404, detail="行业数据获取失败")
    
    try:
        print(f"行业数据条数: {len(industries) if industries else 0}")
    except Exception:
        pass
    return {"industries": industries, "count": len(industries) if industries else 0}


@router.get("/status")
async def get_service_status():
    """获取服务状态"""
    return {
        "connected": tdx_client.connected,
        "current_server": tdx_client.current_server,
        "connection_pool": {
            "size": tdx_connection_pool._connection_pool.qsize(),
            "max_size": tdx_connection_pool.max_connections,
            "available": tdx_connection_pool._connection_pool.qsize(),
            "in_use": 0
        },
        "timestamp": datetime.now().isoformat()
    }

