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
        
        mcp_server = FastMCP("TDX MCP", streamable_http_path="/")
        
        @mcp_server.tool("get_quote")
        async def mcp_get_quote(symbol: str, ctx: Context):
            """获取单个股票实时行情（完整TDX原始API字段）
            输入: symbol=sh/sz/bj+6位代码（必填）
            输出: 完整行情对象（含TDX原始API所有字段）
            完整字段列表: market, code, active1, price, last_close, open, high, low, servertime, reversed_bytes0, reversed_bytes1, vol, cur_vol, amount, s_vol, b_vol, reversed_bytes2, reversed_bytes3, bid1, ask1, bid_vol1, ask_vol1, bid2, ask2, bid_vol2, ask_vol2, bid3, ask3, bid_vol3, ask_vol3, bid4, ask4, bid_vol4, ask_vol4, bid5, ask5, bid_vol5, ask_vol5, reversed_bytes4, reversed_bytes5, reversed_bytes6, reversed_bytes7, reversed_bytes8, reversed_bytes9, active2
            限制: 建议单次1只股票，交易时间内调用
            示例: 输入{"symbol":"sz000001"}，输出{"market":0,"code":"000001","active1":4046,"price":10.91,"last_close":10.91,"open":10.93,"high":10.95,"low":10.88,"servertime":"15:32:58.860","vol":602512,"cur_vol":8758,"amount":657487680.0,"s_vol":290377,"b_vol":312135,"bid1":10.91,"ask1":10.92,"bid_vol1":5442,"ask_vol1":121,"bid2":10.9,"ask2":10.93,"bid_vol2":10573,"ask_vol2":1789,"bid3":10.89,"ask3":10.94,"bid_vol3":13832,"ask_vol3":5066,"bid4":10.88,"ask4":10.95,"bid_vol4":17178,"ask_vol4":5753,"bid5":10.87,"ask5":10.96,"bid_vol5":5583,"ask_vol5":4449}
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_security_quotes, [symbol]
            )
            return rs[0] if rs else {}
        
        @mcp_server.tool("get_quotes")
        async def mcp_get_quotes(symbols: List[str], ctx: Context):
            """批量获取实时行情（完整TDX原始API字段）
            输入: symbols=["sh600000","sz000001"]（必填，股票代码列表）
            输出: 行情对象列表（含TDX原始API所有字段）
            完整字段列表: market, code, active1, price, last_close, open, high, low, servertime, reversed_bytes0, reversed_bytes1, vol, cur_vol, amount, s_vol, b_vol, reversed_bytes2, reversed_bytes3, bid1, ask1, bid_vol1, ask_vol1, bid2, ask2, bid_vol2, ask_vol2, bid3, ask3, bid_vol3, ask_vol3, bid4, ask4, bid_vol4, ask_vol4, bid5, ask5, bid_vol5, ask_vol5, reversed_bytes4, reversed_bytes5, reversed_bytes6, reversed_bytes7, reversed_bytes8, reversed_bytes9, active2
            限制: 建议<=100只股票，交易时间内调用
            示例: 输入{"symbols":["sh600000","sz000001"]}，输出[{"market":1,"code":"600000","price":10.1,"last_close":10.05,"open":10.08,"high":10.15,"low":10.02,"vol":1234567,"bid1":10.09,"ask1":10.1,"bid_vol1":5000,"ask_vol1":3000},{"market":0,"code":"000001","price":10.91,"last_close":10.91,"open":10.93,"high":10.95,"low":10.88,"vol":602512,"bid1":10.91,"ask1":10.92,"bid_vol1":5442,"ask_vol1":121}]
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_security_quotes, symbols
            )
            return rs or []
        
        @mcp_server.tool("get_history")
        async def mcp_get_history(symbol: str, period: int, count: int, ctx: Context):
            """获取单只股票历史K线（完整TDX原始API字段）
            输入: symbol=sh/sz/bj+6位代码（必填）, period=K线周期(0-10), count=获取数量(<=1000)
            输出: K线数据列表（含TDX原始API所有字段）
            完整字段列表: datetime, open, high, low, close, vol, amount, year, month, day, hour, minute, datetime_stamp, up_count, down_count
            周期说明: 0=5分钟, 1=15分钟, 2=30分钟, 3=1小时, 4=日线, 5=周线, 6=月线, 7=1分钟, 8=1分钟, 9=日线, 10=季线
            限制: count建议<=1000条，交易时间内调用
            示例: 输入{"symbol":"sz000001","period":9,"count":5}，输出[{"datetime":"2025-02-01 00:00:00","open":10.1,"high":10.3,"low":10.05,"close":10.25,"vol":123456,"amount":1264256.78},{"datetime":"2025-01-31 00:00:00","open":10.15,"high":10.28,"low":10.08,"close":10.12,"vol":987654,"amount":1012345.67}]
            """
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
            """批量获取历史K线（完整TDX原始API字段）
            输入: symbols=股票代码列表（必填）, period=K线周期(0-10), count=获取数量(<=1000), batch_size=批量大小(默认10)
            输出: 按symbol分组的K线字典（含TDX原始API所有字段）
            完整字段列表: datetime, open, high, low, close, vol, amount, year, month, day, hour, minute, datetime_stamp, up_count, down_count
            周期说明: 0=5分钟, 1=15分钟, 2=30分钟, 3=1小时, 4=日线, 5=周线, 6=月线, 7=1分钟, 8=1分钟, 9=日线, 10=季线
            限制: count建议<=1000条，batch_size建议<=20，交易时间内调用
            示例: 输入{"symbols":["sh600000","sz000001"],"period":9,"count":3,"batch_size":10}，输出{"sh600000":[{"datetime":"2025-02-01 00:00:00","open":10.08,"high":10.15,"low":10.02,"close":10.1,"vol":1234567,"amount":12456789.0},{"datetime":"2025-01-31 00:00:00","open":10.05,"high":10.12,"low":9.98,"close":10.08,"vol":987654,"amount":9876543.21}],"sz000001":[{"datetime":"2025-02-01 00:00:00","open":10.93,"high":10.95,"low":10.88,"close":10.91,"vol":602512,"amount":657487680.0},{"datetime":"2025-01-31 00:00:00","open":10.89,"high":10.92,"low":10.85,"close":10.88,"vol":543210,"amount":543210987.65}]}
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_batch_security_bars, symbols, period, count, batch_size
            )
            return rs or {}
        
        @mcp_server.tool("get_finance")
        async def mcp_get_finance(symbol: str, ctx: Context):
            """获取财务信息（完整TDX原始API字段）
            输入: symbol=sh/sz/bj+6位代码（必填）
            输出: 财务指标字典（含TDX原始API所有字段）
            完整字段列表: code, name, eps, bvps, total_shares, float_shares, reserved, reserved_pershare, profit, profit_four, revenue, revenue_four, n_income, n_income_four, t_share, l_share, share_restrict, cash_flow, cash_flow_four, update_time
            限制: 建议单次1只股票，非交易时间也可调用
            示例: 输入{"symbol":"sh600000"}，输出{"code":"600000","name":"浦发银行","eps":1.23,"bvps":15.67,"total_shares":29300000000,"float_shares":29300000000,"reserved":45678900000,"reserved_pershare":1.56,"profit":12345678900,"revenue":98765432100,"n_income":36200000000,"t_share":0.0,"l_share":0.0,"cash_flow":1234567800,"update_time":"2025-06-30"}
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_finance_info, symbol
            )
            return rs or {}
        
        @mcp_server.tool("get_stock_info")
        async def mcp_get_stock_info(symbol: str, ctx: Context):
            """获取股票基本信息（完整TDX原始API字段）
            输入: symbol=sh/sz/bj+6位代码（必填）
            输出: 股票基本信息字典（含TDX原始API所有字段）
            完整字段列表: code, name, market, full_code
            限制: 建议单次1只股票，非交易时间也可调用
            示例: 输入{"symbol":"sz000001"}，输出{"code":"000001","name":"平安银行","market":0,"full_code":"sz000001"}
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_instrument_info, symbol
            )
            return rs or {}
        
        @mcp_server.tool("get_blocks")
        async def mcp_get_blocks(ctx: Context):
            """获取板块数据（完整TDX原始API字段）
            输出: 板块数据列表（含TDX原始API所有字段）
            完整字段列表: blockname, blocktype, stocks
            板块类型说明: yb=一般板块, fg=风格板块, gn=概念板块, zs=指数板块, hk=港股板块, jj=基金板块
            限制: 非交易时间也可调用
            示例: 输出[{"blockname":"银行","blocktype":"gn","stocks":["600000","600036","601166","601169","601328","601398","601818","601939","601988","601998","000001","002142","002807","002839","002936","002948"]},{"blockname":"保险","blocktype":"gn","stocks":["601318","601336","601319","601601","601628","601628"]}]
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_stock_blocks
            )
            return rs or []
        
        @mcp_server.tool("get_industries")
        async def mcp_get_industries(ctx: Context):
            """获取行业数据（完整TDX原始API字段）
            输出: 行业分类数据列表（含TDX原始API所有字段）
            完整字段列表: code, name, stocks, count
            限制: 非交易时间也可调用
            示例: 输出[{"code":"B01","name":"银行","stocks":["600000","600036","601166","601169","601328","601398","601818","601939","601988","601998","000001","002142","002807","002839","002936","002948"],"count":16},{"code":"B02","name":"保险","stocks":["601318","601336","601319","601601","601628","601628"],"count":6}]
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_industry_info
            )
            return rs or []

        @mcp_server.tool("get_quotes_batch")
        async def mcp_get_quotes_batch(symbols: List[str], batch_size: int = 80, ctx: Context = None):
            """大批量实时行情（完整TDX原始API字段）
            输入: symbols=股票代码列表（必填）, batch_size=批量大小(默认80)
            输出: 行情对象列表（含TDX原始API所有字段）
            完整字段列表: market, code, active1, price, last_close, open, high, low, servertime, reversed_bytes0, reversed_bytes1, vol, cur_vol, amount, s_vol, b_vol, reversed_bytes2, reversed_bytes3, bid1, ask1, bid_vol1, ask_vol1, bid2, ask2, bid_vol2, ask_vol2, bid3, ask3, bid_vol3, ask_vol3, bid4, ask4, bid_vol4, ask_vol4, bid5, ask5, bid_vol5, ask_vol5, reversed_bytes4, reversed_bytes5, reversed_bytes6, reversed_bytes7, reversed_bytes8, reversed_bytes9, active2
            限制: 建议<=500只股票，batch_size建议<=80，交易时间内调用
            示例: 输入{"symbols":["sh600000","sz000001","sh601318"],"batch_size":80}，输出[{"market":1,"code":"600000","price":10.1,"last_close":10.05,"open":10.08,"high":10.15,"low":10.02,"vol":1234567,"bid1":10.09,"ask1":10.1,"bid_vol1":5000,"ask_vol1":3000},{"market":0,"code":"000001","price":10.91,"last_close":10.91,"open":10.93,"high":10.95,"low":10.88,"vol":602512,"bid1":10.91,"ask1":10.92,"bid_vol1":5442,"ask_vol1":121},{"market":1,"code":"601318","price":45.67,"last_close":45.23,"open":45.45,"high":45.89,"low":45.12,"vol":234567,"bid1":45.65,"ask1":45.68,"bid_vol1":1234,"ask_vol1":987}]
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_batch_security_quotes, symbols, batch_size
            )
            return rs or []

        @mcp_server.tool("get_xdxr")
        async def mcp_get_xdxr(symbol: str, ctx: Context):
            """获取除权除息信息（完整TDX原始API字段）
            输入: symbol=sh/sz/bj+6位代码（必填）
            输出: 除权除息记录列表（含TDX原始API所有字段）
            完整字段列表: year, month, day, date, category, category_meaning, fenhong, peigu, songzhuangu, peiguprice, suogu, panqianliutong, panhouliutong, qianzongguben, houzongguben, fqri, gqdjr, notice
            类别说明: 1=除权除息, 2=送股, 3=配股, 4=现金红利, 5=股本变化, 6=其他
            限制: 建议单次1只股票，非交易时间也可调用
            示例: 输入{"symbol":"sz000001"}，输出[{"year":2024,"month":7,"day":1,"date":"2024-07-01","category":4,"category_meaning":"现金红利","fenhong":0.5,"peigu":0.0,"songzhuangu":0.0,"peiguprice":0.0,"suogu":0.0,"panqianliutong":19600000000,"panhouliutong":19600000000,"qianzongguben":19600000000,"houzongguben":19600000000,"fqri":"20240701","gqdjr":"20240701","notice":"2023年度分红派息实施公告"}]
            """
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_xdxr_info, symbol
            )
            return rs or []

        @mcp_server.tool("get_markets")
        async def mcp_get_markets(ctx: Context):
            """获取市场列表。输出: 市场列表（字段: market,name）。示例: 输出[{"market":0,"name":"深圳市场"},{"market":1,"name":"上海市场"}]"""
            rs = await asyncio.get_event_loop().run_in_executor(
                executor, tdx_client.get_market_list
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


def get_mcp_server():
    global mcp_server
    if mcp_server is None:
        setup_mcp()
    return mcp_server
