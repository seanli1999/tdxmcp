#!/usr/bin/env python3
"""
测试pytdx库中各个方法的可用性和返回值
"""

from pytdx.hq import TdxHq_API

# 连接到用户发现的可用服务器
api = TdxHq_API()

# 测试连接
if api.connect('129.204.230.128', 7709):
    print("✅ 连接成功")
    
    # 测试各个方法
    methods_to_test = [
        'get_security_quotes',
        'get_finance_info', 
        'get_report_file',
        'get_security_list',
        'get_security_count',
        'get_history_minute_time_data',
        'get_history_day_data',
        'get_security_bars'
    ]
    
    for method_name in methods_to_test:
        if hasattr(api, method_name):
            print(f"✅ {method_name}: 方法存在")
            
            # 尝试调用一些基本方法
            if method_name == 'get_security_count':
                try:
                    result = api.get_security_count(0)  # 深圳市场
                    print(f"  深圳市场证券数量: {result}")
                except Exception as e:
                    print(f"  ❌ 调用失败: {e}")
            
            elif method_name == 'get_security_list':
                try:
                    result = api.get_security_list(0, 0, 10)  # 深圳市场，前10只
                    print(f"  返回值类型: {type(result)}")
                    if result is not None:
                        print(f"  获取到 {len(result)} 条证券数据")
                        if result:
                            print(f"  示例: {result[0]}")
                    else:
                        print("  ❌ 返回值为None")
                except Exception as e:
                    print(f"  ❌ 调用失败: {e}")
        else:
            print(f"❌ {method_name}: 方法不存在")
    
    # 测试实时行情方法
    print("\n=== 测试实时行情 ===")
    try:
        # 测试平安银行(000001)和浦发银行(600000)
        quotes = api.get_security_quotes([(0, '000001'), (1, '600000')])
        print(f"实时行情返回值类型: {type(quotes)}")
        if quotes is not None:
            print(f"获取到 {len(quotes)} 条行情数据")
            for quote in quotes:
                print(f"  行情: {quote}")
        else:
            print("❌ 实时行情返回None")
    except Exception as e:
        print(f"❌ 实时行情调用失败: {e}")
    
    # 测试财务信息方法
    print("\n=== 测试财务信息 ===")
    try:
        finance_info = api.get_finance_info(0, '000001')  # 平安银行
        print(f"财务信息返回值类型: {type(finance_info)}")
        if finance_info is not None:
            print(f"财务信息: {finance_info}")
        else:
            print("❌ 财务信息返回None")
    except Exception as e:
        print(f"❌ 财务信息调用失败: {e}")
    
    api.disconnect()
else:
    print("❌ 连接失败")