#!/usr/bin/env python3
"""
TDX数据服务数据分析示例
演示如何使用API数据进行简单的金融分析
"""

import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

BASE_URL = "http://localhost:8000"

def get_api_data(endpoint: str, params: Dict = None) -> Dict:
    """通用API数据获取函数"""
    try:
        if params:
            response = requests.get(f"{BASE_URL}{endpoint}", params=params)
        else:
            response = requests.get(f"{BASE_URL}{endpoint}")
        
        response.raise_for_status()
        return response.json()
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
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"提交 {endpoint} 数据失败: {e}")
        return {}

def analyze_stock_performance():
    """分析股票表现"""
    print("\n=== 股票表现分析 ===")
    
    # 获取多只银行股数据
    bank_stocks = ["sh600036", "sh600000", "sz000001", "sh601398"]  # 招商, 浦发, 平安, 工商银行
    
    performance_data = []
    
    for symbol in bank_stocks:
        # 获取实时行情
        quote = get_api_data(f"/api/quote/{symbol}")
        
        if quote.get('quote'):
            q = quote['quote']
            performance_data.append({
                'symbol': symbol,
                'name': q.get('name', symbol),
                'price': q.get('price', 0),
                'updown': q.get('updown', 0),
                'volume': q.get('volume', 0)
            })
    
    if performance_data:
        df = pd.DataFrame(performance_data)
        df = df.sort_values('updown', ascending=False)
        
        print("银行股表现排名:")
        print(df[['symbol', 'name', 'price', 'updown', 'volume']].to_string(index=False))
        
        # 可视化
        plt.figure(figsize=(10, 6))
        plt.bar(df['name'], df['updown'], color=['green' if x >= 0 else 'red' for x in df['updown']])
        plt.title('银行股涨跌幅对比')
        plt.xlabel('股票名称')
        plt.ylabel('涨跌幅 (%)')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('bank_stocks_performance.png')
        print("图表已保存为 bank_stocks_performance.png")

def analyze_historical_trend():
    """分析历史趋势"""
    print("\n=== 历史趋势分析 ===")
    
    # 获取平安银行历史数据
    history = get_api_data("/api/history/sz000001", {"period": 9, "count": 20})  # 20个交易日
    
    if history.get('data'):
        df = pd.DataFrame(history['data'])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df.set_index('datetime', inplace=True)
        
        # 计算移动平均
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        
        print("平安银行近期走势:")
        print(f"最新收盘价: {df['close'].iloc[-1]:.2f}")
        print(f"5日均价: {df['MA5'].iloc[-1]:.2f}")
        print(f"20日均价: {df['MA20'].iloc[-1]:.2f}")
        
        # 可视化
        plt.figure(figsize=(12, 6))
        plt.plot(df.index, df['close'], label='收盘价', linewidth=2)
        plt.plot(df.index, df['MA5'], label='5日均线', linestyle='--')
        plt.plot(df.index, df['MA20'], label='20日均线', linestyle='-.')
        plt.title('平安银行股价走势')
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig('stock_trend_analysis.png')
        print("图表已保存为 stock_trend_analysis.png")

def analyze_sector_distribution():
    """分析板块分布"""
    print("\n=== 板块分布分析 ===")
    
    # 获取板块数据
    blocks = get_api_data("/api/blocks")
    
    if blocks.get('blocks'):
        block_data = []
        
        for block in blocks['blocks']:
            if block.get('stocks'):
                block_data.append({
                    'block_name': block.get('blockname', '未知'),
                    'stock_count': len(block.get('stocks', [])),
                    'block_type': block.get('blocktype', '未知')
                })
        
        df = pd.DataFrame(block_data)
        
        # 按股票数量排序
        df = df.sort_values('stock_count', ascending=False)
        
        print("板块股票数量排名 (前10):")
        print(df.head(10)[['block_name', 'stock_count', 'block_type']].to_string(index=False))
        
        # 按板块类型统计
        type_stats = df.groupby('block_type')['stock_count'].sum().sort_values(ascending=False)
        
        print("\n按板块类型统计:")
        for block_type, count in type_stats.items():
            print(f"  {block_type}: {count} 只股票")

def analyze_volume_analysis():
    """成交量分析"""
    print("\n=== 成交量分析 ===")
    
    # 获取几只活跃股票
    active_stocks = ["sh601318", "sz000002", "sh600036", "sz000001"]  # 中国平安, 万科A, 招商银行, 平安银行
    
    volume_data = []
    
    for symbol in active_stocks:
        quote = get_api_data(f"/api/quote/{symbol}")
        
        if quote.get('quote'):
            q = quote['quote']
            volume_data.append({
                'symbol': symbol,
                'name': q.get('name', symbol),
                'volume': q.get('volume', 0),
                'amount': q.get('amount', 0),
                'price': q.get('price', 0)
            })
    
    if volume_data:
        df = pd.DataFrame(volume_data)
        df = df.sort_values('volume', ascending=False)
        
        print("股票成交量排名:")
        print(df[['symbol', 'name', 'volume', 'amount']].to_string(index=False))
        
        # 计算成交额
        total_amount = df['amount'].sum()
        print(f"\n总成交额: {total_amount:,.0f} 元")
        
        # 计算占比
        df['amount_pct'] = (df['amount'] / total_amount) * 100
        
        print("\n成交额占比:")
        for _, row in df.iterrows():
            print(f"  {row['name']}: {row['amount_pct']:.1f}%")

def main():
    """主函数"""
    print("TDX数据服务数据分析示例")
    print("本示例演示如何使用API数据进行金融分析")
    
    try:
        analyze_stock_performance()
        analyze_historical_trend()
        analyze_sector_distribution()
        analyze_volume_analysis()
        
        print("\n=== 分析完成 ===")
        print("所有分析已完成! 生成的图表文件:")
        print("- bank_stocks_performance.png (银行股表现对比)")
        print("- stock_trend_analysis.png (股价趋势分析)")
        
    except Exception as e:
        print(f"分析程序执行出错: {e}")
        print("请确保TDX数据服务正在运行 (http://localhost:8000)")
        print("并已安装必要的依赖: pip install pandas matplotlib numpy")

if __name__ == "__main__":
    main()