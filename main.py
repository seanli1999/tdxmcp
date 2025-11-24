from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
from pytdx.hq import TdxHq_API
from pytdx.params import TDXParams
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
    """TDX连接池管理类"""
    def __init__(self, max_connections=10, timeout=2, test_interval=300):
        self.max_connections = max_connections
        self.timeout = timeout
        self.test_interval = test_interval
        self._connection_pool = queue.Queue(maxsize=max_connections)
        self._connection_worker = Thread(target=self._connection_worker_thread, daemon=True)
        self._connection_worker.start()
    
    def _test_server_speed(self, server_config):
        """测试服务器连接速度"""
        try:
            api = TdxHq_API(raise_exception=True, auto_retry=False)
            start_time = time.time()
            
            if api.connect(server_config["ip"], server_config["port"], time_out=self.timeout):
                # 测试连接是否有效
                security_count = api.get_security_count(0)  # 测试深圳市场
                if security_count > 0:
                    elapsed = time.time() - start_time
                    api.disconnect()
                    return elapsed
                api.disconnect()
            
            return float('inf')  # 连接失败或无效
        except Exception:
            return float('inf')  # 连接异常
    
    def _connection_worker_thread(self):
        """连接池工作线程，维护连接池"""
        while True:
            try:
                # 如果连接池不满，创建新连接
                if self._connection_pool.qsize() < self.max_connections:
                    # 测试所有服务器，选择最快的
                    best_server = None
                    best_speed = float('inf')
                    
                    for server in TDX_SERVERS:
                        speed = self._test_server_speed(server)
                        if speed < best_speed:
                            best_speed = speed
                            best_server = server
                    
                    if best_server and best_speed < self.timeout * 3:
                        try:
                            api = TdxHq_API(heartbeat=False)
                            api.connect(best_server["ip"], best_server["port"], time_out=self.timeout*2)
                            self._connection_pool.put(api)
                        except Exception:
                            pass
                
                # 定期清理和重新测试连接
                time.sleep(self.test_interval)
                
            except Exception:
                time.sleep(5)  # 发生异常时等待一段时间
    
    def get_connection(self):
        """从连接池获取一个连接"""
        try:
            if not self._connection_pool.empty():
                return self._connection_pool.get_nowait()
            else:
                # 如果没有可用连接，立即启动工作线程尝试创建连接
                Timer(0, self._connection_worker_thread).start()
                # 等待一段时间获取连接
                time.sleep(0.1)
                return self._connection_pool.get_nowait() if not self._connection_pool.empty() else None
        except Exception:
            return None
    
    def return_connection(self, api):
        """归还连接到连接池"""
        try:
            if api and not self._connection_pool.full():
                self._connection_pool.put_nowait(api)
        except Exception:
            pass
    
    def close_all(self):
        """关闭所有连接"""
        while not self._connection_pool.empty():
            try:
                api = self._connection_pool.get_nowait()
                api.disconnect()
            except Exception:
                pass

# 全局连接池实例
tdx_connection_pool = TDXConnectionPool(max_connections=5, timeout=2)

class TDXClient:
    def __init__(self):
        self.connected = True  # 连接池模式下总是连接状态
        self.current_server = None
    
    def _with_connection(self, func, *args, **kwargs):
        """使用连接池执行操作"""
        api = tdx_connection_pool.get_connection()
        if not api:
            # 如果无法获取连接，尝试创建临时连接
            try:
                temp_api = TdxHq_API()
                # 尝试连接最快的服务器
                for server in TDX_SERVERS:
                    try:
                        if temp_api.connect(server["ip"], server["port"]):
                            result = func(temp_api, *args, **kwargs)
                            temp_api.disconnect()
                            return result
                    except Exception:
                        continue
                return None
            except Exception:
                return None
        
        try:
            result = func(api, *args, **kwargs)
            return result
        except Exception as e:
            print(f"操作执行失败: {e}")
            return None
        finally:
            tdx_connection_pool.return_connection(api)
    
    def ensure_connected(self) -> bool:
        """确保连接状态"""
        return True  # 连接池模式下总是返回True
    
    def get_market_list(self):
        """获取市场列表"""
        # 由于pytdx没有直接的get_market_list方法，我们返回模拟的市场列表
        return [
            {"market": 0, "name": "深圳市场"},
            {"market": 1, "name": "上海市场"}
        ]
    
    def get_instrument_info(self, symbol: str):
        """获取股票基本信息"""
        def _get_instrument_info(api, symbol):
            # 解析市场代码和股票代码
            market = 0  # 默认深圳
            if symbol.startswith('sh') or symbol.startswith('6'):
                market = 1  # 上海
            
            code = symbol.replace('sh', '').replace('sz', '')
            
            # 由于 get_security_list 返回 None，我们使用其他方式获取股票信息
            # 尝试通过实时行情获取基本信息
            quotes = api.get_security_quotes([(market, code)])
            
            if quotes and len(quotes) > 0:
                quote = quotes[0]
                # 从行情数据中提取基本信息
                stock_name = f"股票{code}"  # 默认名称
                
                # 尝试从行情数据中获取更多信息
                return {
                    'code': code,
                    'name': stock_name,
                    'market': market,
                    'full_code': symbol,
                    'price': quote.get('price', 0),
                    'last_close': quote.get('last_close', 0)
                }
            
            # 如果实时行情也失败，返回基本结构
            return {
                'code': code,
                'name': f"股票{code}",
                'market': market,
                'full_code': symbol
            }
        
        return self._with_connection(_get_instrument_info, symbol)
    
    def get_security_bars(self, symbol: str, period: int, count: int):
        """获取K线数据"""
        def _get_security_bars(api, symbol, period, count):
            market = 0  # 深圳
            if symbol.startswith('sh') or symbol.startswith('6'):
                market = 1  # 上海
            
            code = symbol.replace('sh', '').replace('sz', '')
            bars = api.get_security_bars(period, market, code, 0, count)
            
            if bars:
                df = pd.DataFrame(bars)
                df['datetime'] = pd.to_datetime(df['datetime'])
                return df.to_dict('records')
            return []
        
        return self._with_connection(_get_security_bars, symbol, period, count)
    
    def get_security_quotes(self, symbols: List[str]):
        """获取实时行情"""
        def _get_security_quotes(api, symbols):
            market_codes = []
            for symbol in symbols:
                market = 0  # 深圳
                if symbol.startswith('sh') or symbol.startswith('6'):
                    market = 1  # 上海
                code = symbol.replace('sh', '').replace('sz', '')
                market_codes.append((market, code))
            
            quotes = api.get_security_quotes(market_codes)
            return quotes
        
        return self._with_connection(_get_security_quotes, symbols)
    


    def get_finance_info(self, symbol: str):
        """获取财务信息"""
        def _get_finance_info(api, symbol):
            market = 0  # 深圳
            if symbol.startswith('sh') or symbol.startswith('6'):
                market = 1  # 上海
            
            code = symbol.replace('sh', '').replace('sz', '')
            finance_info = api.get_finance_info(market, code)
            
            if finance_info:
                # 将财务信息转换为字典格式
                finance_dict = {}
                for i, item in enumerate(finance_info):
                    finance_dict[f'field_{i}'] = item
                return finance_dict
            return None
        
        return self._with_connection(_get_finance_info, symbol)

    def get_company_report(self, symbol: str, report_type: int = 0):
        """获取公司报告文件"""
        def _get_company_report(api, symbol, report_type):
            market = 0  # 深圳
            if symbol.startswith('sh') or symbol.startswith('6'):
                market = 1  # 上海
            
            code = symbol.replace('sh', '').replace('sz', '')
            report_data = api.get_report_file(market, code, report_type)
            return report_data
        
        return self._with_connection(_get_company_report, symbol, report_type)

    def get_batch_security_quotes(self, symbols: List[str], batch_size: int = 80):
        """批量获取实时行情数据"""
        def _get_batch_security_quotes(api, symbols, batch_size):
            all_quotes = []
            
            # 分批处理
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                
                market_codes = []
                for symbol in batch_symbols:
                    market = 0  # 深圳
                    if symbol.startswith('sh') or symbol.startswith('6'):
                        market = 1  # 上海
                    code = symbol.replace('sh', '').replace('sz', '')
                    market_codes.append((market, code))
                
                quotes = api.get_security_quotes(market_codes)
                if quotes:
                    all_quotes.extend(quotes)
            
            return all_quotes
        
        return self._with_connection(_get_batch_security_quotes, symbols, batch_size)
    
    def get_batch_security_bars(self, symbols: List[str], period: int = 9, count: int = 100, batch_size: int = 10):
        """批量获取K线数据"""
        def _get_batch_security_bars(api, symbols, period, count, batch_size):
            all_bars = {}
            
            # 分批处理
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                
                for symbol in batch_symbols:
                    market = 0  # 深圳
                    if symbol.startswith('sh') or symbol.startswith('6'):
                        market = 1  # 上海
                    
                    code = symbol.replace('sh', '').replace('sz', '')
                    bars = api.get_security_bars(period, market, code, 0, count)
                    
                    if bars:
                        df = pd.DataFrame(bars)
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        all_bars[symbol] = df.to_dict('records')
                    else:
                        all_bars[symbol] = []
            
            return all_bars
        
        return self._with_connection(_get_batch_security_bars, symbols, period, count, batch_size)

    def get_stock_blocks(self):
        """获取股票板块数据"""
        def _get_stock_blocks(api):
            try:
                # 获取各种板块数据
                block_types = [
                    ("block.dat", "yb"),      # 一般板块
                    ("block_fg.dat", "fg"),  # 风格板块
                    ("block_gn.dat", "gn"),  # 概念板块
                    ("block_zs.dat", "zs"),  # 指数板块
                    ("hkblock.dat", "hk"),   # 港股板块
                    ("jjblock.dat", "jj")    # 基金板块
                ]
                
                all_blocks = []
                
                for block_file, block_type in block_types:
                    try:
                        block_data = api.get_and_parse_block_info(block_file)
                        if block_data:
                            # 使用api.to_df()转换数据，与QATdx.py保持一致
                            df = api.to_df(block_data)
                            df['block_type'] = block_type
                            df['block_file'] = block_file
                            
                            # 处理不同的数据结构
                            if 'stock_list' in df.columns:
                                # 展开stock_list中的多个股票代码
                                expanded_blocks = []
                                for _, row in df.iterrows():
                                    if row['stock_list']:
                                        for code in row['stock_list']:
                                            expanded_blocks.append({
                                                'code': code,
                                                'block_name': row['blockname'],
                                                'block_type': block_type,
                                                'block_file': block_file
                                            })
                                all_blocks.extend(expanded_blocks)
                            elif 'code' in df.columns:
                                # 直接使用code字段
                                for _, row in df.iterrows():
                                    if row['code']:
                                        all_blocks.append({
                                            'code': row['code'],
                                            'block_name': row['blockname'],
                                            'block_type': block_type,
                                            'block_file': block_file
                                        })
                            else:
                                print(f"警告: {block_file} 中的板块数据格式异常，无法找到stock_list或code字段")
                                continue
                    except Exception as e:
                        # 特别处理hkblock和jjblock的解析错误
                        error_msg = str(e)
                        if 'unpack' in error_msg and 'buffer' in error_msg:
                            print(f"警告: {block_file} 解析失败，可能是二进制格式不匹配或数据损坏: {error_msg}")
                        elif 'struct' in error_msg:
                            print(f"警告: {block_file} 结构解析错误: {error_msg}")
                        else:
                            print(f"获取板块数据 {block_file} 失败: {error_msg}")
                        continue
                
                return all_blocks
                
            except Exception as e:
                print(f"获取板块数据失败: {e}")
                return []
        
        return self._with_connection(_get_stock_blocks)
    
    def get_industry_info(self):
        """获取行业信息"""
        def _get_industry_info(api):
            try:
                # 获取行业代码对照表
                incon_content = api.get_block_dat_ver_up("incon.dat")
                if incon_content:
                    incon_content = incon_content.decode("GB18030")
                    incon_block_info = self._parse_block_name_info(incon_content)
                else:
                    incon_block_info = None
                
                # 获取行业数据
                industry_data = self._get_tdx_industry_data(incon_block_info)
                
                if industry_data is not None and len(industry_data) > 0:
                    return industry_data
                else:
                    # 返回默认行业信息作为fallback
                    return [
                        {"industry_code": "HY001", "industry_name": "银行", "stock_count": 50},
                        {"industry_code": "HY002", "industry_name": "证券", "stock_count": 45},
                        {"industry_code": "HY003", "industry_name": "保险", "stock_count": 30},
                        {"industry_code": "HY004", "industry_name": "房地产", "stock_count": 120},
                        {"industry_code": "HY005", "industry_name": "医药", "stock_count": 200}
                    ]
                
            except Exception as e:
                print(f"获取行业信息失败: {e}")
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
        """获取通达信行业数据"""
        try:
            folder = None
            if not isinstance(incon_block_info, pd.DataFrame):
                folder = self._download_tdx_file(False if isinstance(incon_block_info, pd.DataFrame) else True)
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
        """获取除权除息信息"""
        def _get_xdxr_info(api):
            try:
                # 获取市场代码
                market_code = 1 if symbol.startswith(('0', '3', '8', '9')) else 0
                
                # 获取除权除息数据
                xdxr_data = api.get_xdxr_info(market_code, symbol)
                
                if xdxr_data:
                    # 转换为DataFrame格式
                    df = pd.DataFrame(xdxr_data)
                    
                    # 定义类别映射
                    category_map = {
                        '1': '除权除息', '2': '送配股上市', '3': '非流通股上市', '4': '未知股本变动',
                        '5': '股本变化', '6': '增发新股', '7': '股份回购', '8': '增发新股上市', 
                        '9': '转配股上市', '10': '可转债上市', '11': '扩缩股', '12': '非流通股缩股',
                        '13': '送认购权证', '14': '送认沽权证'
                    }
                    
                    # 处理数据
                    if len(df) >= 1:
                        df = df.assign(
                            date=pd.to_datetime(df[['year', 'month', 'day']]),
                            category_meaning=df['category'].astype(str).map(category_map),
                            code=symbol
                        ).drop(['year', 'month', 'day'], axis=1)
                        
                        # 重命名列
                        df = df.rename(columns={
                            'panhouliutong': 'liquidity_after',
                            'panqianliutong': 'liquidity_before',
                            'houzongguben': 'shares_after',
                            'qianzongguben': 'shares_before'
                        })
                        
                        # 转换为字典列表返回
                        result = df.to_dict('records')
                        
                        # 处理日期格式
                        for item in result:
                            if 'date' in item and hasattr(item['date'], 'strftime'):
                                item['date'] = item['date'].strftime('%Y-%m-%d')
                        
                        return result
                    else:
                        return []
                else:
                    return []
                    
            except Exception as e:
                print(f"获取除权除息信息失败: {e}")
                return []
        
        return self._with_connection(_get_xdxr_info)

# 全局TDX客户端实例
tdx_client = TDXClient()

@app.get("/")
async def root():
    return {"message": "TDX数据源管理服务", "version": "1.0.0"}

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
async def get_batch_history_data(
    symbols: List[str],
    period: int = 9,  # 9: 日线, 0: 5分钟, 1: 15分钟等
    count: int = 100,
    batch_size: int = 10
):
    """批量获取历史K线数据"""
    if len(symbols) > 100:
        raise HTTPException(status_code=400, detail="一次最多查询100只股票")
    
    if count > 1000:
        raise HTTPException(status_code=400, detail="一次最多获取1000条数据")
    
    bars = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_batch_security_bars, symbols, period, count, batch_size
    )
    
    return {"symbols": symbols, "period": period, "data": bars}

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
    
    return {"blocks": blocks, "count": len(blocks) if blocks else 0}

@app.get("/api/industries")
async def get_industries():
    """获取行业信息数据"""
    industries = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_industry_info
    )
    
    if industries is None:
        raise HTTPException(status_code=404, detail="行业数据获取失败")
    
    return {"industries": industries, "count": len(industries) if industries else 0}

@app.get("/api/xdxr/{symbol}")
async def get_xdxr_info(symbol: str):
    """获取除权除息信息"""
    xdxr_info = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.get_xdxr_info, symbol
    )
    
    if xdxr_info is None:
        raise HTTPException(status_code=404, detail="除权除息信息获取失败")
    
    return {"symbol": symbol, "xdxr_info": xdxr_info, "count": len(xdxr_info) if xdxr_info else 0}

@app.get("/api/status")
async def get_service_status():
    """获取服务状态"""
    return {
        "connected": tdx_client.connected,
        "current_server": tdx_client.current_server,
        "connection_pool": {
            "size": len(tdx_client.connection_pool.available_connections) if hasattr(tdx_client, 'connection_pool') else 0,
            "max_size": tdx_client.connection_pool.max_size if hasattr(tdx_client, 'connection_pool') else 0,
            "available": len(tdx_client.connection_pool.available_connections) if hasattr(tdx_client, 'connection_pool') else 0,
            "in_use": len(tdx_client.connection_pool.in_use_connections) if hasattr(tdx_client, 'connection_pool') else 0
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)