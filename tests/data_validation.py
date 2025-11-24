#!/usr/bin/env python3
"""
TDX数据服务数据验证脚本
验证API返回数据的完整性、格式正确性和数据质量
"""

import requests
import json
import time
from typing import Dict, List, Any, Set
from datetime import datetime

BASE_URL = "http://localhost:8000"

class DataValidator:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.validation_results = []
    
    def validate_quote_data(self, symbol: str) -> Dict[str, Any]:
        """验证股票行情数据"""
        result = {
            "symbol": symbol,
            "data_type": "quote",
            "issues": [],
            "valid": True
        }
        
        try:
            response = requests.get(f"{self.base_url}/api/quote/{symbol}", timeout=10)
            
            if response.status_code != 200:
                result["issues"].append(f"HTTP错误: {response.status_code}")
                result["valid"] = False
                return result
            
            data = response.json()
            
            if "quote" not in data:
                result["issues"].append("缺少quote字段")
                result["valid"] = False
                return result
            
            quote = data["quote"]
            
            # 检查必需字段
            required_fields = ["code", "price", "volume", "amount"]
            for field in required_fields:
                if field not in quote:
                    result["issues"].append(f"缺少必需字段: {field}")
                    result["valid"] = False
            
            # 检查数据格式
            if "price" in quote and not isinstance(quote["price"], (int, float)):
                result["issues"].append("价格字段格式错误")
                result["valid"] = False
            
            if "volume" in quote and not isinstance(quote["volume"], (int, float)):
                result["issues"].append("成交量字段格式错误")
                result["valid"] = False
            
            # 检查数据合理性
            if "price" in quote and quote["price"] <= 0:
                result["issues"].append("价格数据不合理")
                result["valid"] = False
            
            if "volume" in quote and quote["volume"] < 0:
                result["issues"].append("成交量数据不合理")
                result["valid"] = False
            
            result["data_sample"] = {
                "price": quote.get("price"),
                "volume": quote.get("volume"),
                "amount": quote.get("amount")
            }
            
        except Exception as e:
            result["issues"].append(f"验证异常: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_history_data(self, symbol: str, period: int = 9, count: int = 10) -> Dict[str, Any]:
        """验证历史数据"""
        result = {
            "symbol": symbol,
            "data_type": "history",
            "period": period,
            "count": count,
            "issues": [],
            "valid": True
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/api/history/{symbol}",
                params={"period": period, "count": count},
                timeout=15
            )
            
            if response.status_code != 200:
                result["issues"].append(f"HTTP错误: {response.status_code}")
                result["valid"] = False
                return result
            
            data = response.json()
            
            if "data" not in data:
                result["issues"].append("缺少data字段")
                result["valid"] = False
                return result
            
            history_data = data["data"]
            
            # 检查数据条数
            if len(history_data) < min(5, count):  # 至少返回5条或请求数量
                result["issues"].append(f"数据条数不足: {len(history_data)}/{count}")
                result["valid"] = False
            
            # 检查K线数据格式
            for i, kline in enumerate(history_data):
                if not isinstance(kline, (list, tuple)) or len(kline) < 6:
                    result["issues"].append(f"第{i}条K线数据格式错误")
                    result["valid"] = False
                    continue
                
                # 检查价格数据合理性
                open_price, high, low, close, volume, amount = kline[:6]
                
                if not all(isinstance(x, (int, float)) for x in [open_price, high, low, close, volume, amount]):
                    result["issues"].append(f"第{i}条K线数据类型错误")
                    result["valid"] = False
                
                if high < low or high < open_price or high < close or low > open_price or low > close:
                    result["issues"].append(f"第{i}条K线价格逻辑错误")
                    result["valid"] = False
                
                if volume < 0 or amount < 0:
                    result["issues"].append(f"第{i}条K线成交量/成交额错误")
                    result["valid"] = False
            
            result["data_count"] = len(history_data)
            if history_data:
                result["data_sample"] = history_data[0]
            
        except Exception as e:
            result["issues"].append(f"验证异常: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_finance_data(self, symbol: str) -> Dict[str, Any]:
        """验证财务数据"""
        result = {
            "symbol": symbol,
            "data_type": "finance",
            "issues": [],
            "valid": True
        }
        
        try:
            response = requests.get(f"{self.base_url}/api/finance/{symbol}", timeout=10)
            
            if response.status_code != 200:
                result["issues"].append(f"HTTP错误: {response.status_code}")
                result["valid"] = False
                return result
            
            data = response.json()
            
            if "finance_info" not in data:
                result["issues"].append("缺少finance_info字段")
                result["valid"] = False
                return result
            
            finance_info = data["finance_info"]
            
            # 检查财务数据字段
            if not isinstance(finance_info, dict):
                result["issues"].append("财务信息格式错误")
                result["valid"] = False
                return result
            
            # 检查是否有数据
            if not finance_info:
                result["issues"].append("财务信息为空")
                result["valid"] = False
                return result
            
            # 检查字段数量（pytdx通常返回大量字段）
            if len(finance_info) < 10:
                result["issues"].append(f"财务字段数量过少: {len(finance_info)}")
                result["valid"] = False
            
            # 检查关键财务字段是否存在
            important_fields = ['field_0', 'field_1', 'field_2', 'field_3', 'field_4']
            missing_fields = [field for field in important_fields if field not in finance_info]
            if missing_fields:
                result["issues"].append(f"缺少关键财务字段: {missing_fields}")
                result["valid"] = False
            
            result["field_count"] = len(finance_info)
            result["data_sample"] = {k: finance_info[k] for k in list(finance_info.keys())[:5]}
            
        except Exception as e:
            result["issues"].append(f"验证异常: {str(e)}")
            result["valid"] = False
        
        return result
    
    def validate_batch_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """验证批量行情数据"""
        result = {
            "data_type": "batch_quotes",
            "symbol_count": len(symbols),
            "issues": [],
            "valid": True
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/quotes",
                headers={"Content-Type": "application/json"},
                data=json.dumps(symbols),
                timeout=15
            )
            
            if response.status_code != 200:
                result["issues"].append(f"HTTP错误: {response.status_code}")
                result["valid"] = False
                return result
            
            data = response.json()
            
            if "quotes" not in data:
                result["issues"].append("缺少quotes字段")
                result["valid"] = False
                return result
            
            quotes = data["quotes"]
            
            # 检查返回数据数量
            if len(quotes) != len(symbols):
                result["issues"].append(f"返回数据数量不匹配: {len(quotes)}/{len(symbols)}")
                result["valid"] = False
            
            # 检查数据完整性
            valid_quotes = 0
            for i, quote in enumerate(quotes):
                if quote and isinstance(quote, dict) and "code" in quote:
                    valid_quotes += 1
                else:
                    result["issues"].append(f"第{i}个股票数据无效: {symbols[i]}")
            
            if valid_quotes < len(symbols) * 0.8:  # 至少80%的数据有效
                result["issues"].append(f"有效数据比例过低: {valid_quotes}/{len(symbols)}")
                result["valid"] = False
            
            result["valid_count"] = valid_quotes
            result["success_rate"] = valid_quotes / len(symbols) * 100
            
        except Exception as e:
            result["issues"].append(f"验证异常: {str(e)}")
            result["valid"] = False
        
        return result
    
    def run_comprehensive_validation(self):
        """运行全面的数据验证"""
        print("🔍 开始TDX数据服务数据验证")
        print("=" * 60)
        
        test_symbols = [
            "sh600000",  # 浦发银行
            "sz000001",  # 平安银行
            "sh601318",  # 中国平安
            "sz000002",  # 万科A
            "sh600036"   # 招商银行
        ]
        
        validation_results = []
        
        # 验证单个股票行情
        print("📈 验证单个股票行情数据")
        print("-" * 40)
        for symbol in test_symbols[:3]:  # 测试前3个
            result = self.validate_quote_data(symbol)
            validation_results.append(result)
            
            status = "✅" if result["valid"] else "❌"
            print(f"{status} {symbol}: {result['data_type']}")
            if not result["valid"]:
                for issue in result["issues"]:
                    print(f"  问题: {issue}")
            else:
                print(f"  样例: 价格={result['data_sample']['price']}, 成交量={result['data_sample']['volume']}")
        
        # 验证历史数据
        print("\n📊 验证历史数据")
        print("-" * 40)
        for symbol in test_symbols[:2]:  # 测试前2个
            result = self.validate_history_data(symbol)
            validation_results.append(result)
            
            status = "✅" if result["valid"] else "❌"
            print(f"{status} {symbol}: {result['data_type']} (周期{result['period']})")
            if not result["valid"]:
                for issue in result["issues"]:
                    print(f"  问题: {issue}")
            else:
                print(f"  数据条数: {result['data_count']}")
                print(f"  样例K线: {result['data_sample']}")
        
        # 验证财务数据
        print("\n💰 验证财务数据")
        print("-" * 40)
        for symbol in test_symbols[:3]:  # 测试前3个
            result = self.validate_finance_data(symbol)
            validation_results.append(result)
            
            status = "✅" if result["valid"] else "❌"
            print(f"{status} {symbol}: {result['data_type']}")
            if not result["valid"]:
                for issue in result["issues"]:
                    print(f"  问题: {issue}")
            else:
                print(f"  字段数量: {result['field_count']}")
                print(f"  样例字段: {result['data_sample']}")
        
        # 验证批量行情
        print("\n🔄 验证批量行情数据")
        print("-" * 40)
        batch_result = self.validate_batch_quotes(test_symbols)
        validation_results.append(batch_result)
        
        status = "✅" if batch_result["valid"] else "❌"
        print(f"{status} 批量行情: {batch_result['symbol_count']}只股票")
        if not batch_result["valid"]:
            for issue in batch_result["issues"]:
                print(f"  问题: {issue}")
        else:
            print(f"  有效数据: {batch_result['valid_count']}/{batch_result['symbol_count']}")
            print(f"  成功率: {batch_result['success_rate']:.1f}%")
        
        # 汇总结果
        print("\n🎯 数据验证汇总")
        print("=" * 60)
        
        total_tests = len(validation_results)
        passed_tests = sum(1 for r in validation_results if r["valid"])
        failed_tests = total_tests - passed_tests
        
        print(f"总验证项: {total_tests}")
        print(f"通过项: {passed_tests}")
        print(f"失败项: {failed_tests}")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        
        # 显示失败详情
        if failed_tests > 0:
            print("\n❌ 失败详情:")
            for result in validation_results:
                if not result["valid"]:
                    print(f"  • {result.get('symbol', '批量数据')} - {result['data_type']}")
                    for issue in result["issues"]:
                        print(f"    - {issue}")
        
        if passed_tests == total_tests:
            print("\n🎉 所有数据验证通过!")
        else:
            print(f"\n⚠️  有{failed_tests}项验证失败，请检查数据服务")
        
        return validation_results

def main():
    """主函数"""
    validator = DataValidator()
    
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
    
    # 运行数据验证
    results = validator.run_comprehensive_validation()
    
    # 保存详细结果到文件
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"validation_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📁 详细验证结果已保存到: {filename}")

if __name__ == "__main__":
    main()