#!/usr/bin/env python3
"""
TDX数据服务API测试脚本
测试所有API端点的功能完整性
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

def test_connection():
    """测试服务连接"""
    print("=== 测试服务连接 ===")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"连接测试失败: {e}")
        return False

def test_server_status():
    """测试服务器状态"""
    print("\n=== 测试服务器状态 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        data = response.json()
        print(f"连接状态: {data['connected']}")
        print(f"当前服务器: {data['current_server']}")
        return response.status_code == 200
    except Exception as e:
        print(f"状态测试失败: {e}")
        return False

def test_servers_list():
    """测试服务器列表"""
    print("\n=== 测试服务器列表 ===")
    try:
        response = requests.get(f"{BASE_URL}/api/servers")
        data = response.json()
        print(f"可用服务器数量: {len(data['servers'])}")
        for server in data['servers']:
            print(f"  - {server['name']}: {server['ip']}:{server['port']}")
        return response.status_code == 200
    except Exception as e:
        print(f"服务器列表测试失败: {e}")
        return False

def test_real_time_quote():
    """测试实时行情"""
    print("\n=== 测试实时行情 ===")
    test_symbols = ["sh600000", "sz000001"]  # 平安银行, 平安银行
    
    for symbol in test_symbols:
        try:
            response = requests.get(f"{BASE_URL}/api/quote/{symbol}")
            data = response.json()
            print(f"{symbol} 行情: {data['quote']['price'] if 'quote' in data else '无数据'}")
        except Exception as e:
            print(f"{symbol} 行情测试失败: {e}")
            return False
    
    return True

def test_batch_quotes():
    """测试批量行情"""
    print("\n=== 测试批量行情 ===")
    symbols = ["sh600036", "sz000002", "sh601318"]  # 招商银行, 万科A, 中国平安
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/quotes",
            headers={"Content-Type": "application/json"},
            data=json.dumps(symbols)
        )
        data = response.json()
        print(f"批量查询结果: {len(data['quotes'])} 条数据")
        for quote in data['quotes']:
            if quote:
                print(f"  - {quote.get('code', '未知')}: {quote.get('price', 0)}")
        return response.status_code == 200
    except Exception as e:
        print(f"批量行情测试失败: {e}")
        return False

def test_history_data():
    """测试历史数据"""
    print("\n=== 测试历史数据 ===")
    symbol = "sz000001"  # 平安银行
    
    try:
        response = requests.get(f"{BASE_URL}/api/history/{symbol}?period=9&count=10")
        data = response.json()
        print(f"历史数据条数: {len(data['data'])}")
        if data['data']:
            print(f"最新K线: {data['data'][0]}")
        return response.status_code == 200
    except Exception as e:
        print(f"历史数据测试失败: {e}")
        return False

def test_finance_data():
    """测试财务数据"""
    print("\n=== 测试财务数据 ===")
    symbol = "sh600000"  # 浦发银行
    
    try:
        response = requests.get(f"{BASE_URL}/api/finance/{symbol}")
        data = response.json()
        print(f"财务信息字段数: {len(data['finance_info'])}")
        print(f"财务数据示例: {list(data['finance_info'].items())[:5]}")  # 显示前5个字段
        return response.status_code == 200
    except Exception as e:
        print(f"财务数据测试失败: {e}")
        return False

def test_company_report():
    """测试公司报告"""
    print("\n=== 测试公司报告 ===")
    symbol = "sz000001"  # 平安银行
    
    try:
        response = requests.get(f"{BASE_URL}/api/report/{symbol}?report_type=0")
        data = response.json()
        print(f"报告数据大小: {data['data_size']} 字节")
        print(f"是否有数据: {data['has_data']}")
        return response.status_code == 200
    except Exception as e:
        print(f"公司报告测试失败: {e}")
        return False

def test_stock_info():
    """测试股票信息"""
    print("\n=== 测试股票信息 ===")
    symbol = "sh601988"  # 中国银行
    
    try:
        response = requests.get(f"{BASE_URL}/api/stock/{symbol}")
        data = response.json()
        print(f"股票信息: {data['info']}")
        return response.status_code == 200
    except Exception as e:
        print(f"股票信息测试失败: {e}")
        return False

def test_batch_history_data():
    """测试批量历史数据"""
    print("\n=== 测试批量历史数据 ===")
    symbols = ["sh600036", "sz000002", "sh601318"]  # 招商银行, 万科A, 中国平安
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/history/batch",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "symbols": symbols,
                "period": 9,  # 日线
                "count": 5    # 5条数据
            })
        )
        data = response.json()
        print(f"批量历史数据结果: {len(data['data'])} 只股票")
        for symbol, klines in data['data'].items():
            print(f"  - {symbol}: {len(klines)} 条K线")
        return response.status_code == 200
    except Exception as e:
        print(f"批量历史数据测试失败: {e}")
        return False

def test_stock_blocks():
    """测试板块数据"""
    print("\n=== 测试板块数据 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/blocks")
        data = response.json()
        print(f"板块数据: {len(data['blocks'])} 个板块")
        if data['blocks']:
            # 显示前3个板块的信息
            for i, block in enumerate(data['blocks'][:3]):
                print(f"  - {block.get('blockname', '未知')}: {len(block.get('stocks', []))} 只股票")
        return response.status_code == 200
    except Exception as e:
        print(f"板块数据测试失败: {e}")
        return False

def test_industry_info():
    """测试行业数据"""
    print("\n=== 测试行业数据 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/api/industries")
        data = response.json()
        print(f"行业数据: {len(data['industries'])} 个行业")
        if data['industries']:
            # 显示前3个行业的信息
            for i, industry in enumerate(data['industries'][:3]):
                print(f"  - {industry.get('name', '未知')}: {len(industry.get('stocks', []))} 只股票")
        return response.status_code == 200
    except Exception as e:
        print(f"行业数据测试失败: {e}")
        return False

def test_xdxr_info():
    """测试除权除息信息"""
    print("\n=== 测试除权除息信息 ===")
    symbol = "sz000001"  # 平安银行
    
    try:
        response = requests.get(f"{BASE_URL}/api/xdxr/{symbol}")
        data = response.json()
        print(f"除权除息信息: {len(data['xdxr_info'])} 条记录")
        if data['xdxr_info']:
            # 显示前3条记录
            for i, record in enumerate(data['xdxr_info'][:3]):
                print(f"  - {record.get('date', '未知')}: {record.get('category_meaning', '未知')}")
        return response.status_code == 200
    except Exception as e:
        print(f"除权除息信息测试失败: {e}")
        return False

def test_connection_pool():
    """测试连接池功能"""
    print("\n=== 测试连接池功能 ===")
    
    try:
        # 测试并发请求以验证连接池
        symbols = ["sh600000", "sz000001", "sh601398", "sz000002", "sh601318"]
        
        results = []
        for symbol in symbols:
            response = requests.get(f"{BASE_URL}/api/quote/{symbol}", timeout=10)
            if response.status_code == 200:
                results.append(True)
                print(f"  {symbol}: 请求成功")
            else:
                results.append(False)
                print(f"  {symbol}: 请求失败")
        
        # 检查连接池状态
        status_response = requests.get(f"{BASE_URL}/api/status")
        status_data = status_response.json()
        print(f"连接池状态: {status_data.get('connection_pool', {}).get('size', 0)} 个连接")
        
        return all(results) and len(results) == len(symbols)
    except Exception as e:
        print(f"连接池测试失败: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("开始运行TDX数据服务API测试...")
    print("=" * 50)
    
    tests = [
        test_connection,
        test_server_status,
        test_servers_list,
        test_real_time_quote,
        test_batch_quotes,
        test_history_data,
        test_finance_data,
        test_company_report,
        test_stock_info,
        test_batch_history_data,
        test_stock_blocks,
        test_industry_info,
        test_xdxr_info,
        test_connection_pool
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            time.sleep(1)  # 避免请求过于频繁
        except Exception as e:
            print(f"测试执行异常: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"总测试数: {len(results)}")
    print(f"通过数: {sum(results)}")
    print(f"失败数: {len(results) - sum(results)}")
    print(f"通过率: {sum(results)/len(results)*100:.1f}%")
    
    if all(results):
        print("\n✅ 所有测试通过!")
        return True
    else:
        print("\n❌ 部分测试失败!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)