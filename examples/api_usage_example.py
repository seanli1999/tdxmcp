#!/usr/bin/env python3
"""
TDX数据服务API使用示例
演示如何使用所有API端点进行数据获取和分析
"""

import requests
import json
import pandas as pd
from typing import Dict, List, Any
import time

BASE_URL = "http://localhost:6999"

def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")

def get_api_data(endpoint: str, params: Dict = None) -> Dict:
    """通用API数据获取函数"""
    try:
        if params:
            response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        else:
            response = requests.get(f"{BASE_URL}{endpoint}")
        
        # 检查HTTP状态码
        if response.status_code != 200:
            error_detail = response.json().get('detail', '未知错误')
            print(f"获取 {endpoint} 数据失败: HTTP {response.status_code} - {error_detail}")
            return {}
            
        data = response.json()
        return data
    except Exception as e:
        print(f"获取 {endpoint} 数据失败: {e}")
        return {}

def post_api_data(endpoint: str, data: Any) -> Dict:
    """通用API数据提交函数"""
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(data)
        )
        
        # 检查HTTP状态码
        if response.status_code != 200:
            error_detail = response.json().get('detail', '未知错误')
            print(f"提交 {endpoint} 数据失败: HTTP {response.status_code} - {error_detail}")
            return {}
            
        data = response.json()
        return data
    except Exception as e:
        print(f"提交 {endpoint} 数据失败: {e}")
        return {}

def example_basic_usage():
    """基础使用示例"""
    print_section("1. 基础使用示例")
    
    # 检查服务状态
    status = get_api_data("/api/status")
    print(f"服务状态: {'已连接' if status.get('connected') else '未连接'}")
    print(f"当前服务器: {status.get('current_server', '未知')}")
    
    # 获取服务器列表
    servers = get_api_data("/api/servers")
    print(f"可用服务器数量: {len(servers.get('servers', []))}")

def example_real_time_data():
    """实时数据示例"""
    print_section("2. 实时数据示例")
    
    # 获取单只股票实时行情
    quote = get_api_data("/api/quote/sz000001")  # 平安银行
    if quote and quote.get('quote'):
        q = quote['quote']
        print(f"平安银行实时行情:")
        print(f"  最新价: {q.get('price', 0):.2f}")
        # 计算涨跌幅: (当前价 - 昨收价) / 昨收价 * 100
        last_close = q.get('last_close', 0)
        current_price = q.get('price', 0)
        if last_close and last_close != 0:
            percent_change = ((current_price - last_close) / last_close) * 100
            print(f"  涨跌幅: {percent_change:.2f}%")
        else:
            print(f"  涨跌幅: 0.00%")
        print(f"  成交量: {q.get('vol', 0):,.0f} 手")
    else:
        print("获取平安银行行情失败")
    
    # 批量获取实时行情
    symbols = ["sh600036", "sz000002", "sh601318"]  # 招商银行, 万科A, 中国平安
    batch_quotes = post_api_data("/api/quotes", symbols)
    
    if batch_quotes and batch_quotes.get('quotes'):
        print(f"\n批量行情数据 ({len(batch_quotes['quotes'])} 只股票):")
        for quote in batch_quotes['quotes']:
            if quote:
                # 计算涨跌幅: (当前价 - 昨收价) / 昨收价 * 100
                last_close = quote.get('last_close', 0)
                current_price = quote.get('price', 0)
                if last_close and last_close != 0:
                    percent_change = ((current_price - last_close) / last_close) * 100
                    change_sign = "+" if percent_change >= 0 else ""
                    print(f"  {quote.get('code')}: {current_price:.2f} ({change_sign}{percent_change:.2f}%)")
                else:
                    print(f"  {quote.get('code')}: {current_price:.2f} (0.00%)")
    else:
        print("批量获取行情失败")

def example_history_data():
    """历史数据示例"""
    print_section("3. 历史数据示例")
    
    # 获取单只股票历史K线
    history = get_api_data("/api/history/sz000001", {"period": 9, "count": 10})  # 平安银行日线
    
    if history.get('data'):
        print(f"平安银行最近10个交易日K线:")
        df = pd.DataFrame(history['data'])
        print(df[['datetime', 'open', 'close', 'high', 'low', 'vol']].to_string(index=False))
    
    # 批量获取历史数据
    symbols = ["sh600036", "sz000002"]  # 招商银行, 万科A
    batch_history = post_api_data("/api/history/batch", {
        "symbols": symbols,
        "period": 9,  # 日线
        "count": 5    # 5条数据
    })
    
    if batch_history.get('data'):
        print(f"\n批量历史数据:")
        for symbol, klines in batch_history['data'].items():
            print(f"  {symbol}: {len(klines)} 条K线")
            if klines:
                last_kline = klines[-1]
                print(f"    最新: {last_kline.get('datetime')} 收盘价: {last_kline.get('close'):.2f}")

def example_sector_industry_data():
    """板块行业数据示例"""
    print_section("4. 板块行业数据示例")
    
    # 获取板块数据
    blocks = get_api_data("/api/blocks")
    if blocks.get('blocks'):
        print(f"板块数量: {len(blocks['blocks'])}")
        
        # 显示前5个板块
        for block in blocks['blocks'][:5]:
            print(f"  {block.get('blockname')}: {len(block.get('stocks', []))} 只股票")
    
    # 获取行业数据
    industries = get_api_data("/api/industries")
    if industries.get('industries'):
        print(f"\n行业数量: {len(industries['industries'])}")
        
        # 显示前5个行业
        for industry in industries['industries'][:5]:
            print(f"  {industry.get('name')}: {len(industry.get('stocks', []))} 只股票")

def example_corporate_actions():
    """公司行动数据示例"""
    print_section("5. 公司行动数据示例")
    
    # 获取除权除息信息
    xdxr_info = get_api_data("/api/xdxr/sz000001")  # 平安银行
    
    if xdxr_info.get('xdxr_info'):
        print(f"平安银行除权除息记录: {len(xdxr_info['xdxr_info'])} 条")
        
        for record in xdxr_info['xdxr_info'][:3]:  # 显示最近3条
            print(f"  {record.get('date')}: {record.get('category_meaning')}")
            print(f"    流通股前: {record.get('liquidity_before', 0):,.0f}")
            print(f"    流通股后: {record.get('liquidity_after', 0):,.0f}")

def example_advanced_usage():
    """高级使用示例"""
    print_section("6. 高级使用示例")
    
    # 连接池性能测试
    print("测试连接池并发性能:")
    
    symbols = ["sh600000", "sz000001", "sh601398", "sz000002", "sh601318"]
    
    start_time = time.time()
    
    results = []
    for symbol in symbols:
        quote = get_api_data(f"/api/quote/{symbol}")
        if quote.get('quote'):
            results.append(True)
            print(f"  {symbol}: ✓")
        else:
            results.append(False)
            print(f"  {symbol}: ✗")
    
    end_time = time.time()
    
    print(f"并发请求完成时间: {end_time - start_time:.2f} 秒")
    print(f"成功率: {sum(results)}/{len(results)}")

def main():
    """主函数"""
    print("TDX数据服务API使用示例")
    print("本示例演示如何使用所有API端点进行数据获取和分析")
    
    try:
        example_basic_usage()
        time.sleep(1)
        
        example_real_time_data()
        time.sleep(1)
        
        example_history_data()
        time.sleep(1)
        
        example_sector_industry_data()
        time.sleep(1)
        
        example_corporate_actions()
        time.sleep(1)
        
        example_advanced_usage()
        
        print_section("示例程序执行完成")
        print("所有API端点使用示例已演示完成!")
        
    except Exception as e:
        print(f"示例程序执行出错: {e}")
        print("请确保TDX数据服务正在运行 (http://localhost:6999)")

if __name__ == "__main__":
    main()