#!/usr/bin/env python3
"""
详细调试公司报告获取问题
"""

from pytdx.hq import TdxHq_API

def debug_company_report():
    """调试公司报告获取"""
    print("=== 详细调试公司报告获取 ===")
    
    # 连接到用户发现的可用服务器
    api = TdxHq_API()
    
    if api.connect('129.204.230.128', 7709):
        print("✅ 连接成功")
        
        # 测试不同的报告类型
        report_types = [0, 1, 2, 3]  # 常见的报告类型
        symbols = ['000001', '600000']  # 平安银行, 浦发银行
        markets = [0, 1]  # 深圳, 上海
        
        for market in markets:
            print(f"\n--- 测试市场 {market} (0=深圳, 1=上海) ---")
            
            for symbol in symbols:
                print(f"\n测试股票 {symbol}:")
                
                for report_type in report_types:
                    print(f"  报告类型 {report_type}:")
                    
                    try:
                        # 调用get_report_file方法
                        result = api.get_report_file(market, symbol, report_type)
                        print(f"    返回值: {type(result)}")
                        
                        if result is None:
                            print("     ❌ 返回None")
                        elif isinstance(result, bytes):
                            print(f"     ✅ 返回字节数据，长度: {len(result)} 字节")
                            if len(result) > 0:
                                # 尝试解析前几个字节
                                print(f"     前16字节: {result[:16]}")
                                # 尝试解码为文本
                                try:
                                    text_preview = result[:100].decode('gbk', errors='ignore')
                                    print(f"     文本预览: {text_preview}")
                                except:
                                    print("     无法解码为文本")
                            else:
                                print("     ⚠️  返回空字节数据")
                        else:
                            print(f"     ❓ 未知返回类型: {result}")
                            
                    except Exception as e:
                        print(f"     ❌ 调用异常: {e}")
        
        # 测试其他可能的相关方法
        print("\n--- 测试其他可能的方法 ---")
        
        # 检查是否有其他报告相关的方法
        methods = [method for method in dir(api) if 'report' in method.lower() or 'file' in method.lower()]
        print(f"可能的报告相关方法: {methods}")
        
        # 测试这些方法
        for method_name in methods:
            if hasattr(api, method_name):
                print(f"\n测试方法 {method_name}:")
                try:
                    # 尝试不同的参数组合
                    if method_name == 'get_report_file':
                        # 已经测试过了
                        continue
                    elif method_name == 'get_report_file_by_size':
                        # 测试这个方法，需要文件名参数
                        result = getattr(api, method_name)(0, '000001', 0, 'report.txt')
                        print(f"  返回值: {type(result)}")
                        if result is not None:
                            print(f"  结果长度: {len(result) if hasattr(result, '__len__') else 'N/A'}")
                    elif 'param' in method_name.lower():
                        # 可能需要参数的方法
                        result = getattr(api, method_name)(0, '000001')
                        print(f"  返回值: {type(result)}")
                        if result is not None:
                            print(f"  结果: {result}")
                    else:
                        # 无参数方法
                        result = getattr(api, method_name)()
                        print(f"  返回值: {type(result)}")
                        if result is not None:
                            print(f"  结果: {result}")
                except Exception as e:
                    print(f"  调用异常: {e}")
        
        # 测试其他可能的数据获取方法
        print("\n--- 测试其他数据获取方法 ---")
        other_methods = ['get_company_info', 'get_info', 'get_content', 'get_data']
        for method_name in other_methods:
            if hasattr(api, method_name):
                print(f"\n测试方法 {method_name}:")
                try:
                    # 尝试调用
                    result = getattr(api, method_name)(0, '000001')
                    print(f"  返回值: {type(result)}")
                    if result is not None:
                        print(f"  结果: {result}")
                except Exception as e:
                    print(f"  调用异常: {e}")
        
        api.disconnect()
    else:
        print("❌ 连接失败")

if __name__ == "__main__":
    debug_company_report()