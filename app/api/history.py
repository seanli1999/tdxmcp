"""历史数据API路由"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from ..models.schemas import BatchHistoryRequest
from ..connection.client import tdx_client

router = APIRouter(prefix="/api", tags=["history"])
executor = ThreadPoolExecutor(max_workers=10)


@router.get("/history/{symbol}")
async def get_history_data(
    symbol: str, 
    period: int = 9,  # 9: 日线, 0: 5分钟, 1: 15分钟等
    count: int = 100
):
    """获取历史K线数据"""
    if count > 1000:
        raise HTTPException(status_code=400, detail="一次最多获取1000条数据")
    
    bars = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_security_bars, symbol, period, count
    )
    
    if bars is None:
        raise HTTPException(status_code=404, detail="历史数据获取失败")
    
    return {"symbol": symbol, "period": period, "data": bars}


@router.post("/history/batch")
async def get_batch_history_data(request: BatchHistoryRequest):
    """批量获取历史K线数据"""
    if len(request.symbols) > 100:
        raise HTTPException(status_code=400, detail="一次最多查询100只股票")
    
    if request.count > 1000:
        raise HTTPException(status_code=400, detail="一次最多获取1000条数据")
    
    bars = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_batch_security_bars, request.symbols, request.period, request.count, request.batch_size
    )
    
    return {"symbols": request.symbols, "period": request.period, "data": bars}

