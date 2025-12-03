"""MCP工具定义"""
import asyncio
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor

from ..connection.client import tdx_client

executor = ThreadPoolExecutor(max_workers=10)
mcp_server = None


def setup_mcp():
    """设置MCP服务器和工具"""
    global mcp_server
    
    try:
        from mcp.server.fastmcp import FastMCP, Context
        
        mcp_server = FastMCP("TDX MCP")
        
        @mcp_server.tool("get_quote")
        async def mcp_get_quote(symbol: str, ctx: Context):
            """获取单个股票实时行情"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_security_quotes, [symbol]
            )
            return rs[0] if rs else {}
        
        @mcp_server.tool("get_quotes")
        async def mcp_get_quotes(symbols: List[str], ctx: Context):
            """批量获取股票实时行情"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_security_quotes, symbols
            )
            return rs or []
        
        @mcp_server.tool("get_history")
        async def mcp_get_history(symbol: str, period: int, count: int, ctx: Context):
            """获取历史K线数据"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_security_bars, symbol, period, count
            )
            return rs or []
        
        @mcp_server.tool("get_history_batch")
        async def mcp_get_history_batch(
            symbols: List[str], 
            period: int, 
            count: int, 
            batch_size: int = 10, 
            ctx: Optional[Context] = None
        ):
            """批量获取历史K线数据"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_batch_security_bars, symbols, period, count, batch_size
            )
            return rs or {}
        
        @mcp_server.tool("get_finance")
        async def mcp_get_finance(symbol: str, ctx: Context):
            """获取财务信息"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_finance_info, symbol
            )
            return rs or {}
        
        @mcp_server.tool("get_stock_info")
        async def mcp_get_stock_info(symbol: str, ctx: Context):
            """获取股票基本信息"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_instrument_info, symbol
            )
            return rs or {}
        
        @mcp_server.tool("get_blocks")
        async def mcp_get_blocks(ctx: Context):
            """获取板块数据"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_stock_blocks
            )
            return rs or []
        
        @mcp_server.tool("get_industries")
        async def mcp_get_industries(ctx: Context):
            """获取行业数据"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_industry_info
            )
            return rs or []
        
        return mcp_server
        
    except Exception as e:
        print(f"MCP 未启用: {e}")
        return None


def get_mcp_app():
    """获取MCP应用"""
    global mcp_server
    if mcp_server is None:
        setup_mcp()
    if mcp_server:
        return mcp_server.streamable_http_app()
    return None

