#!/usr/bin/env python3
"""
测试扩展行情服务器 113.45.175.47:7727 的公司报告功能
"""

from pytdx.hq import TdxHq_API
import time

def test_extended_server():
    """测试扩展行情服务器"""
    print("=== 测试扩展行情服务器 113.45.175.47:7727 ===")
    
    # 扩展行情服务器
    extended_server = ('113.45.175.47', 7727)
    
    api = TdxHq_API()
    
    # 连接服务器
    connect_start = time.time()
    if api.connect(extended_server[0], extended_server[1]):
        connect_time = time.time() - connect_start
        print(f"✅ 连接成功 (耗时: {connect_time:.3f}秒)")
        
        # 测试公司报告
        print("\n--- 测试公司报告获取 ---")
        
        test_cases = [
            (0, '000001', 0),  # 深圳平安银行，报告类型0
            (1, '600000', 0),  # 上海浦发银行，报告类型0
            (0, '000001', 1),  # 深圳平安银行，报告类型1
            (1, '600000', 1),  # 上海浦发银行，报告类型1
        ]
        
        for market, symbol, report_type in test_cases:
            print(f"\n测试: 市场={market}, 代码={symbol}, 报告类型={report_type}")
            
            try:
                # 调用get_report_file方法
                call_start = time.time()
                result = api.get_report_file(market, symbol, report_type)
                call_time = time.time() - call_start
                
                print(f"  方法调用: get_report_file({market}, '{symbol}', {report_type})")
                print(f"  调用耗时: {call_time:.3f}秒")
                print(f"  返回值类型: {type(result)}")
                
                if result is None:
                    print("   ❌ 返回None")
                elif isinstance(result, bytes):
                    print(f"   ✅ 返回字节数据，长度: {len(result)} 字节")
                    if len(result) > 0:
                        # 尝试解析前几个字节
                        print(f"   前16字节: {result[:16]}")
                        # 尝试解码为文本
                        try:
                            text_preview = result[:100].decode('gbk', errors='ignore')
                            print(f"   文本预览: {text_preview}")
                        except:
                            print("   无法解码为文本")
                    else:
                        print("   ⚠️  返回空字节数据")
                else:
                    print(f"   ❓ 未知返回类型: {result}")
                    
            except Exception as e:
                print(f"   ❌ 调用异常: {e}")
        
        # 测试其他可能的方法
        print("\n--- 测试其他相关方法 ---")
        
        # 测试财务信息
        try:
            print("\n测试 get_finance_info:")
            finance_info = api.get_finance_info(0, '000001')
            print(f"  返回值类型: {type(finance_info)}")
            if finance_info:
                print(f"  数据可用: {len(finance_info)} 个字段")
                # 显示一些关键字段
                keys = list(finance_info.keys())[:5]
                print(f"  前5个字段: {keys}")
            else:
                print("  返回None")
        except Exception as e:
            print(f"  调用异常: {e}")
        
        # 测试实时行情
        try:
            print("\n测试 get_security_quotes:")
            quotes = api.get_security_quotes([(0, '000001')])
            print(f"  返回值类型: {type(quotes)}")
            if quotes and len(quotes) > 0:
                print(f"  获取到 {len(quotes)} 条行情数据")
                print(f"  第一条数据: {quotes[0]}")
            else:
                print("  返回空列表")
        except Exception as e:
            print(f"  调用异常: {e}")
        
        api.disconnect()
        print(f"\n🔌 已断开与服务器 {extended_server[0]}:{extended_server[1]} 的连接")
    else:
        print(f"❌ 连接失败: {extended_server[0]}:{extended_server[1]}")

if __name__ == "__main__":
    test_extended_server()
    print("\n=== 测试完成 ===")