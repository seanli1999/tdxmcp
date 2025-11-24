#!/usr/bin/env python3
"""
TDX数据源管理服务启动脚本
"""
import uvicorn
import sys
import os

if __name__ == "__main__":
    # 添加当前目录到Python路径
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )