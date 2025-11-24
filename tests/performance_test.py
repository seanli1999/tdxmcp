#!/usr/bin/env python3
"""
TDX数据服务性能测试脚本
测试API端点的性能指标：响应时间、吞吐量、并发处理能力
"""

import requests
import json
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple

BASE_URL = "http://localhost:8000"

class PerformanceTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.results = []
    
    def measure_response_time(self, endpoint: str, method: str = "GET", 
                             data: Any = None, params: Dict = None) -> Tuple[float, int]:
        """测量单个请求的响应时间"""
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = requests.get(url, params=params)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
            else:
                return -1, -1
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒
            return response_time, response.status_code
        except Exception as e:
            return -1, -1
    
    def test_single_endpoint(self, endpoint: str, method: str = "GET", 
                           data: Any = None, params: Dict = None, 
                           num_requests: int = 10) -> Dict[str, Any]:
        """测试单个端点的性能"""
        times = []
        success_count = 0
        
        for i in range(num_requests):
            response_time, status_code = self.measure_response_time(endpoint, method, data, params)
            if response_time >= 0 and status_code == 200:
                times.append(response_time)
                success_count += 1
            time.sleep(0.1)  # 避免请求过于密集
        
        if not times:
            return {
                "endpoint": endpoint,
                "success": False,
                "message": "所有请求失败"
            }
        
        return {
            "endpoint": endpoint,
            "success": True,
            "total_requests": num_requests,
            "successful_requests": success_count,
            "success_rate": success_count / num_requests * 100,
            "min_time_ms": min(times),
            "max_time_ms": max(times),
            "avg_time_ms": statistics.mean(times),
            "median_time_ms": statistics.median(times),
            "std_dev_ms": statistics.stdev(times) if len(times) > 1 else 0,
            "all_times_ms": times
        }
    
    def test_concurrent_requests(self, endpoint: str, method: str = "GET",
                               data: Any = None, params: Dict = None,
                               num_threads: int = 10, requests_per_thread: int = 5) -> Dict[str, Any]:
        """测试并发请求性能"""
        results = []
        
        def worker(thread_id):
            thread_results = []
            for i in range(requests_per_thread):
                response_time, status_code = self.measure_response_time(endpoint, method, data, params)
                thread_results.append({
                    "thread_id": thread_id,
                    "request_id": i,
                    "response_time_ms": response_time,
                    "status_code": status_code,
                    "success": response_time >= 0 and status_code == 200
                })
            return thread_results
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            
            for future in as_completed(futures):
                results.extend(future.result())
        
        end_time = time.time()
        
        total_time = (end_time - start_time) * 1000  # 毫秒
        total_requests = num_threads * requests_per_thread
        successful_requests = sum(1 for r in results if r["success"])
        response_times = [r["response_time_ms"] for r in results if r["success"] and r["response_time_ms"] >= 0]
        
        if not response_times:
            return {
                "endpoint": endpoint,
                "concurrency": num_threads,
                "success": False,
                "message": "所有并发请求失败"
            }
        
        throughput = (successful_requests / total_time) * 1000 if total_time > 0 else 0  # 请求/秒
        
        return {
            "endpoint": endpoint,
            "concurrency": num_threads,
            "requests_per_thread": requests_per_thread,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "success_rate": successful_requests / total_requests * 100,
            "total_time_ms": total_time,
            "throughput_rps": throughput,
            "min_time_ms": min(response_times),
            "max_time_ms": max(response_times),
            "avg_time_ms": statistics.mean(response_times),
            "median_time_ms": statistics.median(response_times),
            "std_dev_ms": statistics.stdev(response_times) if len(response_times) > 1 else 0
        }
    
    def run_comprehensive_performance_test(self):
        """运行全面的性能测试"""
        print("🚀 开始TDX数据服务性能测试")
        print("=" * 60)
        
        test_cases = [
            # 基本端点测试
            {"name": "服务状态", "endpoint": "/api/status", "method": "GET"},
            {"name": "服务器列表", "endpoint": "/api/servers", "method": "GET"},
            
            # 行情数据测试
            {"name": "单股票行情", "endpoint": "/api/quote/sh600000", "method": "GET"},
            {"name": "批量行情", "endpoint": "/api/quotes", "method": "POST", 
             "data": ["sh600036", "sz000002", "sh601318"]},
            
            # 历史数据测试
            {"name": "历史数据", "endpoint": "/api/history/sz000001", "method": "GET",
             "params": {"period": 9, "count": 10}},
            
            # 财务数据测试
            {"name": "财务信息", "endpoint": "/api/finance/sh600000", "method": "GET"},
            {"name": "公司报告", "endpoint": "/api/report/sz000001", "method": "GET",
             "params": {"report_type": 0}},
            
            # 股票信息测试
            {"name": "股票信息", "endpoint": "/api/stock/sh601988", "method": "GET"}
        ]
        
        # 单请求性能测试
        print("📊 单请求性能测试 (10次请求)")
        print("-" * 40)
        
        single_results = []
        for test_case in test_cases:
            print(f"测试: {test_case['name']}")
            result = self.test_single_endpoint(
                endpoint=test_case["endpoint"],
                method=test_case.get("method", "GET"),
                data=test_case.get("data"),
                params=test_case.get("params"),
                num_requests=10
            )
            
            if result["success"]:
                print(f"  平均响应时间: {result['avg_time_ms']:.2f}ms")
                print(f"  成功率: {result['success_rate']:.1f}%")
                single_results.append(result)
            else:
                print(f"  ❌ 测试失败: {result.get('message', '未知错误')}")
            print()
        
        # 并发性能测试 (重点测试行情接口)
        print("⚡ 并发性能测试 (10线程 × 5请求/线程)")
        print("-" * 40)
        
        concurrency_tests = [
            {"name": "单股票行情并发", "endpoint": "/api/quote/sh600000", "method": "GET"},
            {"name": "批量行情并发", "endpoint": "/api/quotes", "method": "POST",
             "data": ["sh600036", "sz000002", "sh601318"]}
        ]
        
        concurrent_results = []
        for test_case in concurrency_tests:
            print(f"测试: {test_case['name']}")
            result = self.test_concurrent_requests(
                endpoint=test_case["endpoint"],
                method=test_case.get("method", "GET"),
                data=test_case.get("data"),
                params=test_case.get("params"),
                num_threads=10,
                requests_per_thread=5
            )
            
            if result["success"]:
                print(f"  吞吐量: {result['throughput_rps']:.2f} 请求/秒")
                print(f"  平均响应时间: {result['avg_time_ms']:.2f}ms")
                print(f"  成功率: {result['success_rate']:.1f}%")
                concurrent_results.append(result)
            else:
                print(f"  ❌ 并发测试失败: {result.get('message', '未知错误')}")
            print()
        
        # 汇总结果
        print("🎯 性能测试汇总")
        print("=" * 60)
        
        if single_results:
            avg_times = [r["avg_time_ms"] for r in single_results if r["success"]]
            success_rates = [r["success_rate"] for r in single_results if r["success"]]
            
            print(f"单请求测试:")
            print(f"  • 平均响应时间: {statistics.mean(avg_times):.2f}ms")
            print(f"  • 最小响应时间: {min(avg_times):.2f}ms")
            print(f"  • 最大响应时间: {max(avg_times):.2f}ms")
            print(f"  • 平均成功率: {statistics.mean(success_rates):.1f}%")
        
        if concurrent_results:
            throughputs = [r["throughput_rps"] for r in concurrent_results if r["success"]]
            concurrency_rates = [r["success_rate"] for r in concurrent_results if r["success"]]
            
            print(f"\n并发测试:")
            print(f"  • 平均吞吐量: {statistics.mean(throughputs):.2f} 请求/秒")
            print(f"  • 最高吞吐量: {max(throughputs):.2f} 请求/秒")
            print(f"  • 平均成功率: {statistics.mean(concurrency_rates):.1f}%")
        
        print(f"\n📈 性能测试完成!")
        
        return {
            "single_results": single_results,
            "concurrent_results": concurrent_results
        }

def main():
    """主函数"""
    tester = PerformanceTester()
    
    try:
        # 先测试服务是否可用
        test_response = requests.get(f"{BASE_URL}/", timeout=5)
        if test_response.status_code != 200:
            print("❌ 服务不可用，请先启动TDX数据服务")
            print("运行命令: python start.py")
            return
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务，请确保服务正在运行")
        print("运行命令: python start.py")
        return
    
    # 运行性能测试
    results = tester.run_comprehensive_performance_test()
    
    # 保存详细结果到文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"performance_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 详细结果已保存到: {filename}")

if __name__ == "__main__":
    main()