from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
from pytdx.hq import TdxHq_API
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor
import queue
import time
from threading import Thread, Timer
import os
import shutil
import tempfile
import random
from urllib.request import urlopen
import json

# 导入配置
from config import TDX_SERVERS

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

# 使用config.py中的服务器配置
# TDX_SERVERS 已经从 config.py 导入

class TDXConnectionPool:
    def __init__(self, max_connections=10, timeout=2, test_interval=300, default_server: Dict[str, Any] = None):
        self.max_connections = max_connections
        self.timeout = timeout
        self.test_interval = test_interval
        self._connection_pool = queue.Queue(maxsize=max_connections)
        self.server = default_server or TDX_SERVERS[0]
        self._connection_worker = Thread(target=self._connection_worker_thread, daemon=True)
        self._connection_worker.start()

    def set_server(self, server: Dict[str, Any]):
        self.server = server

    def _create_connection(self):
        api = TdxHq_API()
        ok = False
        try:
            ok = api.connect(self.server["ip"], self.server["port"])
        except Exception:
            ok = False
        if ok:
            return api
        try:
            api.disconnect()
        except Exception:
            pass
        return None

    def _connection_worker_thread(self):
        while True:
            try:
                if self._connection_pool.qsize() < self.max_connections:
                    api = self._create_connection()
                    if api is not None:
                        try:
                            self._connection_pool.put(api)
                        except Exception:
                            try:
                                api.disconnect()
                            except Exception:
                                pass
                time.sleep(self.test_interval)
            except Exception:
                time.sleep(5)

    def get_connection(self):
        try:
            if not self._connection_pool.empty():
                return self._connection_pool.get_nowait()
            api = self._create_connection()
            return api
        except Exception:
            return None

    def return_connection(self, api):
        try:
            if api and not self._connection_pool.full():
                self._connection_pool.put_nowait(api)
            else:
                try:
                    api.disconnect()
                except Exception:
                    pass
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass

    def close_all(self):
        while not self._connection_pool.empty():
            try:
                api = self._connection_pool.get_nowait()
                try:
                    api.disconnect()
                except Exception:
                    pass
            except Exception:
                pass

# 全局连接池实例
tdx_connection_pool = TDXConnectionPool(max_connections=5, timeout=2, default_server=TDX_SERVERS[0])

class TDXClient:
    def __init__(self):
        self.connected = True
        self.current_server = None
        self._cache_dir = os.path.join(os.path.dirname(__file__), "cache")
        self._blocks_cache = None
        self._industries_cache = None
    
    def connect(self, server_config: Dict[str, Any]) -> bool:
        self.current_server = server_config
        try:
            tdx_connection_pool.set_server(server_config)
            return True
        except Exception:
            return False
    
    def _with_connection(self, func, *args, **kwargs):
        api = None
        created = False
        try:
            api = tdx_connection_pool.get_connection()
            created = api is None
            if created:
                api = TdxHq_API()
                server = tdx_connection_pool.server
                ok = False
                try:
                    ok = api.connect(server["ip"], server["port"])
                except Exception:
                    ok = False
                if not ok:
                    try:
                        api.disconnect()
                    except Exception:
                        pass
                    return None
            return func(api, *args, **kwargs)
        except Exception as e:
            print(f"操作执行失败: {e}")
            return None
        finally:
            try:
                if api is not None:
                    if created:
                        api.disconnect()
                    else:
                        tdx_connection_pool.return_connection(api)
            except Exception:
                pass
    
    def ensure_connected(self) -> bool:
        """确保连接状态"""
        return True  # 连接池模式下总是返回True
    
    def get_market_list(self):
        return [
            {"market": 0, "name": "深圳市场"},
            {"market": 1, "name": "上海市场"}
        ]
    
    def _parse_symbol(self, symbol: str):
        s = symbol.lower()
        market = 1 if s.startswith("sh") else 0
        code = s.replace("sh", "").replace("sz", "")
        return market, code

    def _json_safe_value(self, v):
        try:
            if isinstance(v, float):
                if np.isnan(v) or np.isinf(v):
                    return None
                return v
            if isinstance(v, (list, tuple)):
                return [self._json_safe_value(x) for x in v]
            if isinstance(v, dict):
                return {k: self._json_safe_value(val) for k, val in v.items()}
            return v
        except Exception:
            return v

    def _json_safe_records(self, records):
        try:
            if isinstance(records, pd.DataFrame):
                df = records.replace([np.inf, -np.inf], None)
                df = df.where(pd.notnull(df), None)
                return df.to_dict("records")
            if isinstance(records, list):
                return [self._json_safe_value(r) for r in records]
            if isinstance(records, dict):
                return self._json_safe_value(records)
            return records
        except Exception:
            return records

    def _enrich_xdxr(self, records: List[Dict[str, Any]]):
        cat_map = {
            1: "除权除息",
            2: "送股",
            3: "配股",
            4: "现金红利",
            5: "股本变化",
            6: "其他"
        }
        enriched = []
        for r in records:
            y = r.get("year")
            m = r.get("month")
            d = r.get("day")
            if r.get("date") is None and all(v is not None for v in [y, m, d]):
                try:
                    r["date"] = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
                except Exception:
                    r["date"] = f"{y}-{m}-{d}"
            cat = r.get("category")
            if r.get("category_meaning") is None:
                r["category_meaning"] = cat_map.get(cat, f"类别{cat}" if cat is not None else "类别未知")
            enriched.append(r)
        return enriched

    def get_instrument_info(self, symbol: str):
        def _get_instrument_info(api, symbol):
            market, code = self._parse_symbol(symbol)
            try:
                info = api.get_instrument_info(market, code)
            except Exception:
                info = None
            if info is not None:
                try:
                    return {
                        "code": getattr(info, "code", code),
                        "name": getattr(info, "name", f"股票{code}"),
                        "market": market,
                        "full_code": symbol
                    }
                except Exception:
                    pass
            try:
                quotes = api.get_security_quotes([(market, code)])
            except Exception:
                quotes = None
            if quotes and len(quotes) > 0:
                q = quotes[0]
                return {
                    "code": q.get("code", code) if isinstance(q, dict) else code,
                    "name": q.get("name", f"股票{code}") if isinstance(q, dict) else f"股票{code}",
                    "market": market,
                    "full_code": symbol
                }
            return {
                "code": code,
                "name": f"股票{code}",
                "market": market,
                "full_code": symbol
            }
        return self._with_connection(_get_instrument_info, symbol)
    
    def get_security_bars(self, symbol: str, period: int, count: int):
        def _get_security_bars(api, symbol, period, count):
            market, code = self._parse_symbol(symbol)
            category = period
            data = api.get_security_bars(category, market, code, 0, count)
            if (data is None or len(data) == 0) and period == 9:
                try:
                    data = api.get_security_bars(4, market, code, 0, count)
                except Exception:
                    data = None
            if data is None:
                return []
            try:
                df = api.to_df(data)
            except Exception:
                df = pd.DataFrame(data)
            return self._json_safe_records(df)
        return self._with_connection(_get_security_bars, symbol, period, count)
    
    def get_security_quotes(self, symbols: List[str]):
        def _get_security_quotes(api, symbols):
            req = [self._parse_symbol(s) for s in symbols]
            data = api.get_security_quotes(req)
            if data is None:
                return []
            try:
                df = api.to_df(data)
                return self._json_safe_records(df)
            except Exception:
                return self._json_safe_records(data)
        return self._with_connection(_get_security_quotes, symbols)
    


    def get_finance_info(self, symbol: str):
        def _get_finance_info(api, symbol):
            market, code = self._parse_symbol(symbol)
            data = api.get_finance_info(market, code)
            return self._json_safe_records(data) if isinstance(data, pd.DataFrame) else self._json_safe_value(data)
        return self._with_connection(_get_finance_info, symbol)

    def get_company_report(self, symbol: str, report_type: int = 0):
        def _get_company_report(api, symbol, report_type):
            return None
        return self._with_connection(_get_company_report, symbol, report_type)

    def get_batch_security_quotes(self, symbols: List[str], batch_size: int = 80):
        def _get_batch_security_quotes(api, symbols, batch_size):
            all_quotes = []
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                req = [self._parse_symbol(s) for s in batch_symbols]
                data = api.get_security_quotes(req)
                if data is None:
                    continue
                try:
                    df = api.to_df(data)
                    all_quotes.extend(self._json_safe_records(df))
                except Exception:
                    all_quotes.extend(self._json_safe_records(data))
            return all_quotes
        return self._with_connection(_get_batch_security_quotes, symbols, batch_size)
    
    def get_batch_security_bars(self, symbols: List[str], period: int = 9, count: int = 100, batch_size: int = 10):
        def _get_batch_security_bars(api, symbols, period, count, batch_size):
            all_bars = {}
            category = period
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                for symbol in batch_symbols:
                    market, code = self._parse_symbol(symbol)
                    data = api.get_security_bars(category, market, code, 0, count)
                    if data is None:
                        if period == 9:
                            try:
                                data = api.get_security_bars(4, market, code, 0, count)
                            except Exception:
                                data = None
                        if data is None:
                            all_bars[symbol] = []
                            continue
                    try:
                        df = api.to_df(data)
                        all_bars[symbol] = self._json_safe_records(df)
                    except Exception:
                        all_bars[symbol] = self._json_safe_records(data)
            return all_bars
        return self._with_connection(_get_batch_security_bars, symbols, period, count, batch_size)

    def get_stock_blocks(self):
        def _get_stock_blocks(api):
            try:
                print("开始获取板块数据")
            except Exception:
                pass
            try:
                if isinstance(self._blocks_cache, list) and len(self._blocks_cache) > 0:
                    return self._blocks_cache
            except Exception:
                pass
            def _ensure_cache_dir():
                try:
                    os.makedirs(self._cache_dir, exist_ok=True)
                except Exception:
                    pass
            def _load_cache(name, max_age=86400):
                try:
                    _ensure_cache_dir()
                    p = os.path.join(self._cache_dir, name)
                    if not os.path.exists(p):
                        return None
                    with open(p, "r", encoding="utf-8") as f:
                        obj = json.load(f)
                    ts = obj.get("cached_at")
                    data = obj.get("data")
                    if not ts or data is None:
                        return None
                    try:
                        t0 = datetime.fromisoformat(ts)
                        if (datetime.now() - t0).total_seconds() > max_age:
                            return None
                    except Exception:
                        return None
                    return data
                except Exception:
                    return None
            def _save_cache(name, data):
                try:
                    _ensure_cache_dir()
                    p = os.path.join(self._cache_dir, name)
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump({"cached_at": datetime.now().isoformat(), "data": data}, f, ensure_ascii=False)
                except Exception:
                    pass
            cached = _load_cache("blocks.json")
            if isinstance(cached, list) and len(cached) > 0:
                try:
                    self._blocks_cache = cached
                except Exception:
                    pass
                return cached
            files = [
                ("block.dat", "yb"),
                ("block_fg.dat", "fg"),
                ("block_gn.dat", "gn"),
                ("block_zs.dat", "zs"),
                ("hkblock.dat", "hk"),
                ("jjblock.dat", "jj"),
            ]
            dfs = []
            for fn, bt in files:
                try:
                    df = api.to_df(api.get_and_parse_block_info(fn)).assign(blocktype=bt)
                    dfs.append(df)
                except Exception:
                    pass
            if len(dfs) == 0:
                return []
            try:
                data = pd.concat(dfs, sort=False)
            except Exception:
                return []
            try:
                data["code"] = data["code"].astype(str)
            except Exception:
                pass
            def _is_a_share(c: str):
                try:
                    return (
                        c.startswith("000") or c.startswith("001") or c.startswith("002") or
                        c.startswith("003") or c.startswith("200") or c.startswith("300") or
                        c.startswith("301") or c.startswith("600") or c.startswith("601") or
                        c.startswith("603") or c.startswith("605") or c.startswith("688")
                    ) and len(c) == 6
                except Exception:
                    return False
            try:
                data = data[data["code"].apply(_is_a_share)]
                data = data.drop_duplicates(subset=["blockname", "code", "blocktype"], keep="first")
            except Exception:
                pass
            blocks = []
            try:
                if "blockname" in data.columns and "code" in data.columns:
                    for (bn, bt), group in data.groupby(["blockname", "blocktype"], as_index=False):
                        stocks = sorted(set(group["code"].tolist()))
                        blocks.append({"blockname": bn, "blocktype": bt, "stocks": stocks})
            except Exception:
                return []
            try:
                self._blocks_cache = blocks
                _save_cache("blocks.json", blocks)
            except Exception:
                pass
            return blocks
        return self._with_connection(_get_stock_blocks)
    
    def get_industry_info(self):
        def _get_industry_info(api):
            try:
                print("开始获取行业数据")
            except Exception:
                pass
            try:
                if isinstance(self._industries_cache, list) and len(self._industries_cache) > 0:
                    return self._industries_cache
            except Exception:
                pass
            def _ensure_cache_dir():
                try:
                    os.makedirs(self._cache_dir, exist_ok=True)
                except Exception:
                    pass
            def _load_cache(name, max_age=86400):
                try:
                    _ensure_cache_dir()
                    p = os.path.join(self._cache_dir, name)
                    if not os.path.exists(p):
                        return None
                    with open(p, "r", encoding="utf-8") as f:
                        obj = json.load(f)
                    ts = obj.get("cached_at")
                    data = obj.get("data")
                    if not ts or data is None:
                        return None
                    try:
                        t0 = datetime.fromisoformat(ts)
                        if (datetime.now() - t0).total_seconds() > max_age:
                            return None
                    except Exception:
                        return None
                    return data
                except Exception:
                    return None
            def _save_cache(name, data):
                try:
                    _ensure_cache_dir()
                    p = os.path.join(self._cache_dir, name)
                    with open(p, "w", encoding="utf-8") as f:
                        json.dump({"cached_at": datetime.now().isoformat(), "data": data}, f, ensure_ascii=False)
                except Exception:
                    pass
            cached = _load_cache("industries.json")
            if isinstance(cached, list) and len(cached) > 0:
                try:
                    self._industries_cache = cached
                except Exception:
                    pass
                return cached
            incon_block_info = None
            try:
                content = api.get_block_dat_ver_up("incon.dat")
                if content:
                    try:
                        text = content.decode("GB18030")
                        incon_block_info = self._parse_block_name_info(text)
                    except Exception:
                        pass
            except Exception:
                pass
            data = self._get_tdx_industry_data(incon_block_info=incon_block_info)
            if not data:
                return []
            try:
                rs = [{
                    "code": r.get("industry_code"),
                    "name": r.get("industry_name"),
                    "stocks": r.get("stocks", []),
                    "count": r.get("stock_count", 0)
                } for r in data]
                try:
                    self._industries_cache = rs
                    _save_cache("industries.json", rs)
                except Exception:
                    pass
                return rs
            except Exception:
                return []
        return self._with_connection(_get_industry_info)
    
    def _parse_block_name_info(self, incon_content: str):
        """解析行业代码对照表"""
        incon_content = incon_content.splitlines()
        incon_dict = []
        section = "Unknown"
        for i in incon_content:
            if len(i) <= 0: 
                continue
            if i[0] == '#' and i[1] != '#':
                section = i[1:].strip("\n ")
            elif i[1] != '#':
                item = i.strip('\n ').split('|')
                incon_dict.append({
                    'hycode': item[0], 
                    'blockname': item[-1], 
                    'type': section
                })
        
        return pd.DataFrame(incon_dict)
    
    def _download_tdx_file(self, withZHB: bool = True):
        """下载通达信数据文件"""
        urls = [
            'http://www.tdx.com.cn/products/data/data/dbf/base.zip',
            'http://www.tdx.com.cn/products/data/data/dbf/gbbq.zip',
        ]
        tmpdir_root = tempfile.gettempdir()
        subdir_name = 'tdx_' + str(random.randint(0, 1000000))
        tmpdir = os.path.join(tmpdir_root, subdir_name)
        shutil.rmtree(tmpdir, ignore_errors=True)
        os.makedirs(tmpdir)
        
        try:
            for url in urls if withZHB else urls[:-1]:
                file = tmpdir + '/' + 'tmp.zip'
                f = urlopen(url)
                data = f.read()
                with open(file, 'wb') as code:
                    code.write(data)
                f.close()
                shutil.unpack_archive(file, extract_dir=tmpdir)
                zhb = os.path.join(tmpdir, "zhb.zip")
                if os.path.exists(zhb):
                    shutil.unpack_archive(zhb, extract_dir=tmpdir)
                os.remove(file)
        except Exception as e:
            print(f"下载通达信文件失败: {e}")
        
        return tmpdir
    
    def _read_industry(self, folder: str):
        """读取行业分类文件"""
        fhy = folder + '/tdxhy.cfg'
        try:
            with open(fhy, encoding='GB18030', mode='r') as f:
                hy = f.readlines()
            hy = [line.replace('\n', '') for line in hy]
            hy = pd.DataFrame(line.split('|') for line in hy)
            # 过滤代码
            hy = hy[~hy[1].str.startswith('9')]
            hy = hy[~hy[1].str.startswith('2')]
            
            df = hy.rename({0: 'sse', 1: 'code', 2: 'tdx_code', 3: 'sw_code', 5: 'tdxrshy_code'}, axis=1). \
                reset_index(drop=True). \
                melt(id_vars=('sse', 'code'), value_name='hycode')
            return df
        except Exception as e:
            print(f"读取行业文件失败: {e}")
            return pd.DataFrame()
    
    def _get_tdx_industry_data(self, incon_block_info=None):
        try:
            folder = self._download_tdx_file(False if isinstance(incon_block_info, pd.DataFrame) else True)
            if not isinstance(incon_block_info, pd.DataFrame):
                incon_path = os.path.join(folder, "incon.dat")
                if not os.path.exists(incon_path):
                    zhb = os.path.join(folder, "zhb.zip")
                    if os.path.exists(zhb):
                        shutil.unpack_archive(zhb, extract_dir=folder)
                with open(incon_path, encoding='GB18030', mode='r') as f:
                    incon_content = f.read()
                incon_block_info = self._parse_block_name_info(incon_content)
            
            df = self._read_industry(folder).merge(incon_block_info, on='hycode')
            df.set_index('code', drop=False, inplace=True)
            
            # 转换为行业信息列表
            industry_info = []
            for hycode, group in df.groupby('hycode'):
                industry_info.append({
                    'industry_code': hycode,
                    'industry_name': group['blockname'].iloc[0],
                    'stock_count': len(group),
                    'stocks': group['code'].tolist()
                })
            
            return industry_info
            
        except Exception as e:
            print(f"获取行业数据失败: {e}")
            return None
        finally:
            if folder:
                shutil.rmtree(folder, ignore_errors=True)

    def get_xdxr_info(self, symbol: str):
        def _get_xdxr_info(api):
            market, code = self._parse_symbol(symbol)
            data = api.get_xdxr_info(market, code)
            if data is None:
                return []
            try:
                df = api.to_df(data)
                rs = self._json_safe_records(df)
                return self._enrich_xdxr(rs)
            except Exception:
                rs = self._json_safe_records(data)
                return self._enrich_xdxr(rs if isinstance(rs, list) else [rs])
        return self._with_connection(_get_xdxr_info)

# 全局TDX客户端实例
tdx_client = TDXClient()

@app.on_event("startup")
async def preload_caches():
    try:
        cache_dir = os.path.join(os.path.dirname(__file__), "cache")
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
    return {"message": "TDX数据源管理服务", "version": "1.0.0"}

try:
    from mcp.server.fastmcp import FastMCP, Context
    mcp_server = FastMCP(title="TDX MCP")
    @mcp_server.tool("get_quote")
    async def mcp_get_quote(symbol: str, ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_security_quotes, [symbol])
        return rs[0] if rs else {}
    @mcp_server.tool("get_quotes")
    async def mcp_get_quotes(symbols: List[str], ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_security_quotes, symbols)
        return rs or []
    @mcp_server.tool("get_history")
    async def mcp_get_history(symbol: str, period: int, count: int, ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_security_bars, symbol, period, count)
        return rs or []
    @mcp_server.tool("get_history_batch")
    async def mcp_get_history_batch(symbols: List[str], period: int, count: int, batch_size: int = 10, ctx: Context = None):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_batch_security_bars, symbols, period, count, batch_size)
        return rs or {}
    @mcp_server.tool("get_finance")
    async def mcp_get_finance(symbol: str, ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_finance_info, symbol)
        return rs or {}
    @mcp_server.tool("get_stock_info")
    async def mcp_get_stock_info(symbol: str, ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_instrument_info, symbol)
        return rs or {}
    @mcp_server.tool("get_blocks")
    async def mcp_get_blocks(ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_stock_blocks)
        return rs or []
    @mcp_server.tool("get_industries")
    async def mcp_get_industries(ctx: Context):
        rs = await asyncio.get_event_loop().run_in_executor(executor, tdx_client.get_industry_info)
        return rs or []
    app.mount("/mcp", mcp_server.http_app())
except Exception as _mcp_err:
    try:
        print(f"MCP 未启用: {_mcp_err}")
    except Exception:
        pass

@app.get("/api/servers")
async def get_servers():
    """获取可用的TDX服务器列表"""
    return {"servers": TDX_SERVERS, "current": tdx_client.current_server}

@app.post("/api/connect")
async def connect_server(server_index: int = 0):
    """连接到指定的TDX服务器"""
    if server_index >= len(TDX_SERVERS):
        raise HTTPException(status_code=400, detail="服务器索引超出范围")
    
    success = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.connect, TDX_SERVERS[server_index]
    )
    
    return {"success": success, "server": TDX_SERVERS[server_index] if success else None}

@app.get("/api/markets")
async def get_markets():
    """获取市场列表"""
    markets = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_market_list
    )
    return {"markets": markets}

@app.get("/api/stock/{symbol}")
async def get_stock_info(symbol: str):
    """获取股票基本信息"""
    info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_instrument_info, symbol
    )
    
    if info is None:
        raise HTTPException(status_code=404, detail="股票信息获取失败")
    
    return {"symbol": symbol, "info": info}

@app.get("/api/quote/{symbol}")
async def get_real_time_quote(symbol: str):
    """获取单个股票的实时行情"""
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_security_quotes, [symbol]
    )
    
    if not quotes:
        raise HTTPException(status_code=404, detail="实时行情获取失败")
    
    return {"symbol": symbol, "quote": quotes[0]}

@app.post("/api/quotes")
async def get_batch_quotes(symbols: List[str]):
    """批量获取实时行情"""
    if len(symbols) > 100:
        raise HTTPException(status_code=400, detail="一次最多查询100只股票")
    
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_security_quotes, symbols
    )
    
    return {"quotes": quotes}

class BatchHistoryRequest(BaseModel):
    symbols: List[str]
    period: int = 9
    count: int = 100
    batch_size: int = 10

@app.post("/api/quotes/batch")
async def get_large_batch_quotes(symbols: List[str], batch_size: int = 80):
    """批量获取实时行情（支持大量股票）"""
    if len(symbols) > 500:
        raise HTTPException(status_code=400, detail="一次最多查询500只股票")
    
    quotes = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_batch_security_quotes, symbols, batch_size
    )
    
    return {"quotes": quotes, "count": len(quotes) if quotes else 0}

@app.post("/api/history/batch")
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

@app.get("/api/history/{symbol}")
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

@app.get("/api/finance/{symbol}")
async def get_finance_data(symbol: str):
    """获取财务信息"""
    finance_info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_finance_info, symbol
    )
    
    if finance_info is None:
        raise HTTPException(status_code=404, detail="财务信息获取失败")
    
    return {"symbol": symbol, "finance_info": finance_info}

@app.get("/api/report/{symbol}")
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

@app.get("/api/news")
async def get_news():
    """获取新闻信息（需要扩展实现）"""
    # 这里可以扩展实现新闻数据获取
    return {"news": [], "message": "新闻功能待实现"}

@app.get("/api/blocks")
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

@app.get("/api/industries")
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

@app.get("/api/xdxr/{symbol}")
async def get_xdxr_info(symbol: str):
    """获取除权除息信息"""
    xdxr_info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_xdxr_info, symbol
    )
    
    if xdxr_info is None:
        raise HTTPException(status_code=404, detail="除权除息信息获取失败")
    
    safe_info = tdx_client._json_safe_records(xdxr_info)
    return {"symbol": symbol, "xdxr_info": safe_info, "count": len(safe_info) if safe_info else 0}

@app.get("/api/status")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)