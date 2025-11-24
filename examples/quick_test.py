#!/usr/bin/env python3
"""
TDX数据服务快速测试脚本
快速验证所有API端点是否正常工作
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_endpoint(endpoint, method="GET", data=None, name=None):
    """测试单个端点"""
    try:
        if method == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        else:
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=10
            )
        
        success = response.status_code == 200
        status = "✅" if success else "❌"
        
        if name:
            print(f"{status} {name}")
        else:
            print(f"{status} {endpoint}")
        
        if not success:
            print(f"  错误: HTTP {response.status_code}")
        
        return success
        
    except Exception as e:
        print(f"❌ {endpoint}")
        print(f"  异常: {e}")
        return False

def main():
    """主函数"""
    print("TDX数据服务快速测试")
    print("=" * 50)
    
    results = []
    
    # 测试基础端点
    results.append(test_endpoint("/", name="服务根目录"))
    results.append(test_endpoint("/api/status", name="服务状态"))
    results.append(test_endpoint("/api/servers", name="服务器列表"))
    
    time.sleep(0.5)
    
    # 测试实时数据端点
    results.append(test_endpoint("/api/quote/sz000001", name="单只股票行情"))
    results.append(test_endpoint(
        "/api/quotes", 
        method="POST", 
        data=["sh600036", "sz000002"],
        name="批量股票行情"
    ))
    
    time.sleep(0.5)
    
    # 测试历史数据端点
    results.append(test_endpoint(
        "/api/history/sz000001?period=9&count=5", 
        name="单只股票历史数据"
    ))
    results.append(test_endpoint(
        "/api/history/batch",
        method="POST",
        data={"symbols": ["sh600036", "sz000002"], "period": 9, "count": 3},
        name="批量历史数据"
    ))
    
    time.sleep(0.5)
    
    # 测试财务数据端点
    results.append(test_endpoint("/api/finance/sz000001", name="财务数据"))
    results.append(test_endpoint("/api/stock/sz000001", name="股票信息"))
    
    # 测试新增端点
    results.append(test_endpoint("/api/blocks", name="板块数据"))
    results.append(test_endpoint("/api/industries", name="行业数据"))
    results.append(test_endpoint("/api/xdxr/sz000001", name="除权除息信息"))
    
    time.sleep(0.5)
    
    # 测试连接池
    results.append(test_endpoint("/api/quote/sh600000", name="连接池测试1"))
    results.append(test_endpoint("/api/quote/sz000001", name="连接池测试2"))
    results.append(test_endpoint("/api/quote/sh601318", name="连接池测试3"))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print(f"总测试数: {len(results)}")
    print(f"通过数: {sum(results)}")
    print(f"失败数: {len(results) - sum(results)}")
    print(f"通过率: {sum(results)/len(results)*100:.1f}%")
    
    if all(results):
        print("\n🎉 所有测试通过! 服务运行正常。")
    else:
        print("\n⚠️  部分测试失败，请检查服务状态。")
    
    # 显示连接池状态
    try:
        status_response = requests.get(f"{BASE_URL}/api/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            pool_size = status_data.get('connection_pool', {}).get('size', 0)
            print(f"\n当前连接池大小: {pool_size} 个连接")
    except:
        pass

if __name__ == "__main__":
    main()