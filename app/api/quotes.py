"""行情API路由"""
import asyncio
from typing import List
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException

from ..connection.client import tdx_client

router = APIRouter(prefix="/api", tags=["quotes"])
executor = ThreadPoolExecutor(max_workers=10)


@router.get("/markets")
async def get_markets():
    """获取市场列表"""
    markets = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_market_list
    )
    return {"markets": markets}


@router.get("/stock/{symbol}")
async def get_stock_info(symbol: str):
    """获取股票基本信息"""
    info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_instrument_info, symbol
    )
    
    if info is None:
        raise HTTPException(status_code=404, detail="股票信息获取失败")
    
    return {"symbol": symbol, "info": info}


@router.get("/quote/{symbol}")
async def get_real_time_quote(symbol: str):
    """获取单个股票的实时行情"""
    print(f"[DEBUG] 开始获取实时行情: {symbol}")
    
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_security_quotes, [symbol]
    )
    
    print(f"[DEBUG] 实时行情获取结果: symbol={symbol}, quotes={quotes}")
    
    if not quotes:
        print(f"[ERROR] 实时行情获取失败: symbol={symbol}, quotes为空")
        raise HTTPException(status_code=404, detail="实时行情获取失败")
    
    print(f"[DEBUG] 成功获取实时行情: symbol={symbol}, quote={quotes[0]}")
    return {"symbol": symbol, "quote": quotes[0]}


@router.post("/quotes")
async def get_batch_quotes(symbols: List[str]):
    """批量获取实时行情"""
    print(f"[DEBUG] 开始批量获取实时行情: symbols={symbols}")
    
    if len(symbols) > 100:
        print(f"[ERROR] 批量查询股票数量超过限制: {len(symbols)} > 100")
        raise HTTPException(status_code=400, detail="一次最多查询100只股票")
    
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_security_quotes, symbols
    )
    
    print(f"[DEBUG] 批量实时行情获取结果: symbols={symbols}, quotes_count={len(quotes) if quotes else 0}")
    
    return {"quotes": quotes}


@router.post("/quotes/batch")
async def get_large_batch_quotes(symbols: List[str], batch_size: int = 80):
    """批量获取实时行情（支持大量股票）"""
    if len(symbols) > 500:
        raise HTTPException(status_code=400, detail="一次最多查询500只股票")
    
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_batch_security_quotes, symbols, batch_size
    )
    
    return {"quotes": quotes, "count": len(quotes) if quotes else 0}


@router.get("/finance/{symbol}")
async def get_finance_data(symbol: str):
    """获取财务信息"""
    finance_info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_finance_info, symbol
    )
    
    if finance_info is None:
        raise HTTPException(status_code=404, detail="财务信息获取失败")
    
    return {"symbol": symbol, "finance_info": finance_info}


@router.get("/report/{symbol}")
async def get_company_report(symbol: str, report_type: int = 0):
    """获取公司报告文件"""
    report_data = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_company_report, symbol, report_type
    )
    
    # 即使无法获取报告数据，也返回一个合理的响应而不是404
    data_size = len(report_data) if report_data else 0
    has_data = bool(report_data)
    
    return {
        "symbol": symbol, 
        "report_type": report_type,
        "data_size": data_size,
        "has_data": has_data,
        "message": "报告数据获取成功" if has_data else "暂时无法获取公司报告数据"
    }


@router.get("/xdxr/{symbol}")
async def get_xdxr_info(symbol: str):
    """获取除权除息信息"""
    xdxr_info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_xdxr_info, symbol
    )
    
    if xdxr_info is None:
        raise HTTPException(status_code=404, detail="除权除息信息获取失败")
    
    safe_info = tdx_client._json_safe_records(xdxr_info)
    return {"symbol": symbol, "xdxr_info": safe_info, "count": len(safe_info) if safe_info else 0}


@router.get("/news")
async def get_news():
    """获取新闻信息（需要扩展实现）"""
    # 这里可以扩展实现新闻数据获取
    return {"news": [], "message": "新闻功能待实现"}

