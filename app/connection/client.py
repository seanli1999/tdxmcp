"""TDX客户端"""
import os
import json
import shutil
import tempfile
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from urllib.request import urlopen

import pandas as pd
import numpy as np
from pytdx.hq import TdxHq_API

from .pool import tdx_connection_pool


class TDXClient:
    """TDX数据客户端，封装所有数据获取逻辑"""
    
    def __init__(self):
        self.connected = True
        self.current_server = None
        self._cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cache")
        self._blocks_cache = None
        self._industries_cache = None
    
    def connect(self, server_config: Dict[str, Any]) -> bool:
        """连接到指定服务器"""
        self.current_server = server_config
        try:
            tdx_connection_pool.set_server(server_config)
            return True
        except Exception:
            return False
    
    def _with_connection(self, func, *args, **kwargs):
        """使用连接池执行操作"""
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
    
    def get_market_list(self) -> List[Dict[str, Any]]:
        """获取市场列表"""
        return [
            {"market": 0, "name": "深圳市场"},
            {"market": 1, "name": "上海市场"}
        ]
    
    def _parse_symbol(self, symbol: str):
        """解析股票代码"""
        s = symbol.lower()
        if s.startswith("sh"):
            market = 1  # 上海市场
        elif s.startswith("sz"):
            market = 0  # 深圳市场
        else:
            market = 1  # 默认上海市场
        code = s.replace("sh", "").replace("sz", "")
        return market, code

    def _json_safe_value(self, v):
        """确保值可被JSON序列化"""
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
        """确保记录列表可被JSON序列化"""
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

    def _enrich_xdxr(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """丰富除权除息数据"""
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

    def get_instrument_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
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

    def get_security_bars(self, symbol: str, period: int, count: int) -> List[Dict[str, Any]]:
        """获取K线数据"""
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

    def get_security_quotes(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取实时行情"""
        def _get_security_quotes(api, symbols):
            print(f"[TDX DEBUG] 开始获取实时行情: symbols={symbols}")
            req = [self._parse_symbol(s) for s in symbols]
            print(f"[TDX DEBUG] 解析后的请求: req={req}")

            data = api.get_security_quotes(req)
            print(f"[TDX DEBUG] 原始API返回数据: data={data}")

            if data is None:
                print(f"[TDX ERROR] API返回数据为None: symbols={symbols}")
                return []

            try:
                df = api.to_df(data)
                print(f"[TDX DEBUG] 转换为DataFrame成功: shape={df.shape if hasattr(df, 'shape') else 'N/A'}")
                return self._json_safe_records(df)
            except Exception as e:
                print(f"[TDX ERROR] 转换为DataFrame失败: {e}")
                print(f"[TDX DEBUG] 尝试直接返回原始数据")
                return self._json_safe_records(data)
        return self._with_connection(_get_security_quotes, symbols)

    def get_finance_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取财务信息"""
        def _get_finance_info(api, symbol):
            market, code = self._parse_symbol(symbol)
            data = api.get_finance_info(market, code)
            return self._json_safe_records(data) if isinstance(data, pd.DataFrame) else self._json_safe_value(data)
        return self._with_connection(_get_finance_info, symbol)

    def get_company_report(self, symbol: str, report_type: int = 0):
        """获取公司报告"""
        def _get_company_report(api, symbol, report_type):
            return None
        return self._with_connection(_get_company_report, symbol, report_type)

    def get_batch_security_quotes(self, symbols: List[str], batch_size: int = 80) -> List[Dict[str, Any]]:
        """批量获取实时行情"""
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

    def get_batch_security_bars(self, symbols: List[str], period: int = 9, count: int = 100, batch_size: int = 10) -> Dict[str, List]:
        """批量获取K线数据"""
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

    def get_xdxr_info(self, symbol: str) -> List[Dict[str, Any]]:
        """获取除权除息信息"""
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

    def get_stock_blocks(self) -> List[Dict[str, Any]]:
        """获取板块数据"""
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

            from ..services.cache import CacheService
            cache_service = CacheService(self._cache_dir)

            cached = cache_service.load_cache("blocks.json")
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
                cache_service.save_cache("blocks.json", blocks)
            except Exception:
                pass
            return blocks
        return self._with_connection(_get_stock_blocks)

    def get_industry_info(self) -> List[Dict[str, Any]]:
        """获取行业数据"""
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

            from ..services.cache import CacheService
            cache_service = CacheService(self._cache_dir)

            cached = cache_service.load_cache("industries.json")
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
                    cache_service.save_cache("industries.json", rs)
                except Exception:
                    pass
                return rs
            except Exception:
                return []
        return self._with_connection(_get_industry_info)

    def _parse_block_name_info(self, incon_content: str) -> pd.DataFrame:
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

    def _download_tdx_file(self, withZHB: bool = True) -> str:
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

    def _read_industry(self, folder: str) -> pd.DataFrame:
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

    def _get_tdx_industry_data(self, incon_block_info=None) -> Optional[List[Dict[str, Any]]]:
        """获取通达信行业数据"""
        folder = None
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


# 全局TDX客户端实例
tdx_client = TDXClient()

