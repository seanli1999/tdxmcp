#!/usr/bin/env python3
"""
详细调试公司报告获取问题 - 增强版
包含详细日志和所有服务器的测试
"""

from pytdx.hq import TdxHq_API
import time

def debug_company_report_detailed():
    """详细调试公司报告获取，包含所有服务器测试"""
    print("=== 详细调试公司报告获取 - 增强版 ===")
    
    # 所有可用的服务器列表
    servers = [
        ('129.204.230.128', 7709),  # 用户发现的服务器
        ('124.70.133.119', 7709),   # 用户提供的服务器1
        ('139.159.239.163', 7709),  # 用户提供的服务器2
        ('119.147.212.81', 7709),   # 默认服务器
        ('114.80.63.45', 7709),     # 默认服务器
    ]
    
    # 测试参数
    report_types = [0, 1, 2, 3]  # 常见的报告类型
    symbols = ['000001', '600000']  # 平安银行, 浦发银行
    markets = [0, 1]  # 深圳, 上海
    
    for server_ip, server_port in servers:
        print(f"\n{'='*60}")
        print(f"测试服务器: {server_ip}:{server_port}")
        print(f"{'='*60}")
        
        api = TdxHq_API()
        
        # 连接服务器
        connect_start = time.time()
        if api.connect(server_ip, server_port):
            connect_time = time.time() - connect_start
            print(f"✅ 连接成功 (耗时: {connect_time:.3f}秒)")
            
            # 测试不同的报告类型
            for market in markets:
                print(f"\n--- 测试市场 {market} (0=深圳, 1=上海) ---")
                
                for symbol in symbols:
                    print(f"\n测试股票 {symbol}:")
                    
                    for report_type in report_types:
                        print(f"  报告类型 {report_type}:")
                        
                        try:
                            # 调用get_report_file方法
                            call_start = time.time()
                            result = api.get_report_file(market, symbol, report_type)
                            call_time = time.time() - call_start
                            
                            print(f"    方法调用: get_report_file({market}, '{symbol}', {report_type})")
                            print(f"    调用耗时: {call_time:.3f}秒")
                            print(f"    返回值类型: {type(result)}")
                            
                            if result is None:
                                print("     ❌ 返回None - 服务器可能没有该报告数据")
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
            print(f"\n--- 测试服务器 {server_ip}:{server_port} 的其他方法 ---")
            
            # 检查所有可用的方法
            all_methods = [method for method in dir(api) if not method.startswith('_')]
            report_related = [method for method in all_methods if any(keyword in method.lower() for keyword in ['report', 'file', 'info', 'data', 'content'])]
            
            print(f"所有方法数量: {len(all_methods)}")
            print(f"报告相关方法: {report_related}")
            
            # 测试报告相关的方法
            for method_name in report_related:
                print(f"\n测试方法 {method_name}:")
                try:
                    call_start = time.time()
                    
                    # 根据方法名尝试不同的参数
                    if method_name == 'get_report_file':
                        # 已经测试过了
                        continue
                    elif method_name == 'get_report_file_by_size':
                        # 这个方法需要额外的文件名参数
                        result = getattr(api, method_name)(0, '000001', 0, 'temp_report.txt')
                    elif method_name in ['get_security_quotes', 'get_security_bars']:
                        # 这些方法需要特定的参数格式
                        result = getattr(api, method_name)([(0, '000001')])
                    elif method_name in ['get_company_info', 'get_finance_info']:
                        # 这些方法需要市场和代码参数
                        result = getattr(api, method_name)(0, '000001')
                    elif method_name in ['get_security_count', 'get_security_list']:
                        # 这些方法需要市场参数
                        result = getattr(api, method_name)(0)
                    else:
                        # 尝试无参数调用
                        result = getattr(api, method_name)()
                    
                    call_time = time.time() - call_start
                    print(f"  调用耗时: {call_time:.3f}秒")
                    print(f"  返回值类型: {type(result)}")
                    
                    if result is None:
                        print("  返回None")
                    elif isinstance(result, (list, tuple)):
                        print(f"  返回列表/元组，长度: {len(result)}")
                        if len(result) > 0:
                            print(f"  第一个元素: {result[0]}")
                    elif isinstance(result, bytes):
                        print(f"  返回字节数据，长度: {len(result)} 字节")
                        if len(result) > 0:
                            print(f"  前16字节: {result[:16]}")
                    else:
                        print(f"  返回值: {result}")
                        
                except Exception as e:
                    print(f"  调用异常: {e}")
            
            api.disconnect()
            print(f"🔌 已断开与服务器 {server_ip}:{server_port} 的连接")
        else:
            print(f"❌ 连接失败: {server_ip}:{server_port}")
        
        # 添加短暂的延迟，避免服务器压力
        time.sleep(1)

if __name__ == "__main__":
    debug_company_report_detailed()
    print("\n=== 调试完成 ===")