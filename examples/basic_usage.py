#!/usr/bin/env python3
"""
TDX数据服务基础使用示例
演示如何使用API获取各种数据
"""

import requests
import json
import pandas as pd
from datetime import datetime

class TDXClientExample:
    def __init__(self, base_url="http://localhost:6999"):
        self.base_url = base_url
    
    def get_service_info(self):
        """获取服务信息"""
        print("=== 服务信息 ===")
        response = requests.get(f"{self.base_url}/")
        print(f"服务版本: {response.json()['version']}")
        
        response = requests.get(f"{self.base_url}/api/status")
        status = response.json()
        print(f"连接状态: {status['connected']}")
        print(f"当前时间: {status['timestamp']}")
    
    def list_servers(self):
        """列出可用服务器"""
        print("\n=== 可用服务器 ===")
        response = requests.get(f"{self.base_url}/api/servers")
        servers = response.json()['servers']
        
        for i, server in enumerate(servers):
            print(f"{i+1}. {server['name']} - {server['ip']}:{server['port']}")
    
    def get_single_quote(self, symbol):
        """获取单个股票行情"""
        print(f"\n=== {symbol} 实时行情 ===")
        response = requests.get(f"{self.base_url}/api/quote/{symbol}")
        
        if response.status_code != 200:
            print(f"获取行情失败: {response.json().get('detail', '未知错误')}")
            return None
            
        data = response.json()
        if 'quote' not in data:
            print("返回数据格式错误")
            return None
            
        quote = data['quote']
        print(f"股票代码: {quote.get('code', 'N/A')}")
        print(f"股票名称: {quote.get('name', 'N/A')}")
        print(f"当前价格: {quote.get('price', 0):.2f}")
        # 计算涨跌幅: (当前价 - 昨收价) / 昨收价 * 100
        last_close = quote.get('last_close', 0)
        current_price = quote.get('price', 0)
        if last_close and last_close != 0:
            percent_change = ((current_price - last_close) / last_close) * 100
            print(f"涨跌幅: {percent_change:.2f}%")
        else:
            print(f"涨跌幅: 0.00%")
        print(f"成交量: {quote.get('vol', 0)}")
        
        return quote
    
    def get_batch_quotes(self, symbols):
        """批量获取行情"""
        print(f"\n=== 批量行情查询 ===")
        response = requests.post(
            f"{self.base_url}/api/quotes",
            headers={"Content-Type": "application/json"},
            data=json.dumps(symbols)
        )
        
        quotes = response.json()['quotes']
        print(f"查询股票数: {len(symbols)}")
        print(f"返回数据数: {len(quotes)}")
        
        for i, quote in enumerate(quotes):
            if quote:
                # 计算涨跌幅: (当前价 - 昨收价) / 昨收价 * 100
                last_close = quote.get('last_close', 0)
                current_price = quote.get('price', 0)
                if last_close and last_close != 0:
                    percent_change = ((current_price - last_close) / last_close) * 100
                    change_sign = "+" if percent_change >= 0 else ""
                    print(f"{i+1}. {quote.get('code', 'N/A')}: {current_price:.2f} ({change_sign}{percent_change:.2f}%)")
                else:
                    print(f"{i+1}. {quote.get('code', 'N/A')}: {current_price:.2f} (0.00%)")
        
        return quotes
    
    def get_history_data(self, symbol, period=9, count=20):
        """获取历史K线数据"""
        print(f"\n=== {symbol} 历史数据 ===")
        response = requests.get(f"{self.base_url}/api/history/{symbol}?period={period}&count={count}")
        data = response.json()
        
        print(f"数据周期: {data['period']}")
        print(f"数据条数: {len(data['data'])}")
        
        # 转换为DataFrame便于分析
        df = pd.DataFrame(data['data'])
        if not df.empty:
            print("\n最近5条K线数据:")
            print(df[['datetime', 'open', 'high', 'low', 'close', 'vol']].head())
        
        return df
    
    def get_finance_info(self, symbol):
        """获取财务信息"""
        print(f"\n=== {symbol} 财务信息 ===")
        response = requests.get(f"{self.base_url}/api/finance/{symbol}")
        
        if response.status_code != 200:
            print(f"获取财务信息失败: {response.json().get('detail', '未知错误')}")
            return None
            
        data = response.json()
        if 'finance_info' not in data:
            print("返回数据格式错误")
            return None
            
        finance_info = data['finance_info']
        print(f"财务字段数: {len(finance_info)}")
        
        # 显示重要的财务指标
        important_fields = ['field_0', 'field_1', 'field_2', 'field_3', 'field_4']
        for field in important_fields:
            if field in finance_info:
                print(f"{field}: {finance_info[field]}")
        
        return finance_info
    
    def get_stock_info(self, symbol):
        """获取股票基本信息"""
        print(f"\n=== {symbol} 基本信息 ===")
        response = requests.get(f"{self.base_url}/api/stock/{symbol}")
        data = response.json()
        
        info = data['info']
        if info:
            print(f"股票详情: {info}")
        else:
            print("未找到股票信息")
        
        return info

def main():
    """主函数 - 演示所有功能"""
    client = TDXClientExample()
    
    # 1. 显示服务信息
    client.get_service_info()
    
    # 2. 显示服务器列表
    client.list_servers()
    
    # 3. 获取单个股票行情
    client.get_single_quote("sh600000")  # 浦发银行
    client.get_single_quote("sz000001")  # 平安银行
    
    # 4. 批量查询行情
    symbols = ["sh601318", "sz000002", "sh601988", "sz000858"]  # 中国平安, 万科A, 中国银行, 五粮液
    client.get_batch_quotes(symbols)
    
    # 5. 获取历史数据
    client.get_history_data("sz000001", period=9, count=10)  # 平安银行日线数据
    
    # 6. 获取财务信息
    client.get_finance_info("sh600036")  # 招商银行
    
    # 7. 获取股票基本信息
    client.get_stock_info("sh601857")  # 中国石油
    
    print("\n=== 示例程序执行完成 ===")

if __name__ == "__main__":
    main()