#!/usr/bin/env python3
"""
使用 pytdx 测试基础行情与K线接口
"""

from pytdx.hq import TdxHq_API
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import TDX_SERVERS

def parse_symbol(s: str):
    s = s.lower()
    m = 1 if s.startswith("sh") else 0
    c = s.replace("sh", "").replace("sz", "")
    return m, c

api = TdxHq_API()
server = TDX_SERVERS[0]
connected = api.connect(server["ip"], server["port"])

print("=== 测试实时行情(单/多标的) ===")
try:
    m1, c1 = parse_symbol("sz000001")
    data_single = api.get_security_quotes([(m1, c1)])
    print(data_single[0] if data_single else {})
    req = [parse_symbol(s) for s in ["sz000001", "sh600000"]]
    data_multi = api.get_security_quotes(req)
    print(len(data_multi) if data_multi else 0)
except Exception as e:
    print(f"实时行情测试失败: {e}")

print("\n=== 测试历史K线(日/周/月) ===")
try:
    m, c = parse_symbol("sz000001")
    day = api.get_security_bars(4, m, c, 0, 5)
    print(len(day) if day else 0)
    week = api.get_security_bars(5, m, c, 0, 5)
    print(len(week) if week else 0)
    month = api.get_security_bars(6, m, c, 0, 5)
    print(len(month) if month else 0)
except Exception as e:
    print(f"历史K线测试失败: {e}")

print("\n=== 测试分钟线(5分钟) ===")
try:
    m, c = parse_symbol("sz000001")
    mins = api.get_security_bars(0, m, c, 0, 5)
    print(len(mins) if mins else 0)
except Exception as e:
    print(f"分钟线测试失败: {e}")

print("\n=== 测试财务数据 ===")
try:
    m, c = parse_symbol("sh600000")
    fin = api.get_finance_info(m, c)
    print(len(fin) if isinstance(fin, dict) else 0)
except Exception as e:
    print(f"财务数据测试失败: {e}")

print("\n=== 测试除权除息 ===")
try:
    m, c = parse_symbol("sz000001")
    xdxr = api.get_xdxr_info(m, c)
    print(len(xdxr) if xdxr else 0)
except Exception as e:
    print(f"除权除息测试失败: {e}")

try:
    api.disconnect()
except Exception:
    pass