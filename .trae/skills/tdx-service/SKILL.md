---
name: "tdx-service"
description: "管理TDX数据服务MCP的启动、停止和配置。在需要运行TDX数据服务或配置MCP连接时调用。"
---

# TDX数据服务MCP管理

## 服务概述

这是一个基于FastAPI的TDX（通达信）数据服务MCP，提供股票实时行情、历史数据、财务信息等API接口。

## 快速启动

### 1. 启动TDX数据服务
```bash
# 在项目根目录下运行
uvicorn main:app --host 0.0.0.0 --port 6999
```

### 2. 验证服务状态
```bash
curl http://localhost:6999/api/status
```

## API端点

### 实时数据
- `GET /api/quote/{symbol}` - 获取单个股票实时行情
- `POST /api/quotes` - 批量获取股票行情

### 历史数据  
- `GET /api/history/{symbol}` - 获取历史K线数据
- `POST /api/history/batch` - 批量获取历史数据

### 基础信息
- `GET /api/servers` - 获取可用服务器列表
- `GET /api/blocks` - 获取板块数据
- `GET /api/industries` - 获取行业数据
- `GET /api/finance/{symbol}` - 获取财务信息
- `GET /api/stock/{symbol}` - 获取股票基本信息

## 在其他项目中调用

### Python项目调用示例

```python
import requests
import json

class TDXClient:
    def __init__(self, base_url="http://localhost:6999"):
        self.base_url = base_url
    
    def get_quote(self, symbol):
        """获取单个股票行情"""
        response = requests.get(f"{self.base_url}/api/quote/{symbol}")
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_batch_quotes(self, symbols):
        """批量获取行情"""
        response = requests.post(
            f"{self.base_url}/api/quotes",
            headers={"Content-Type": "application/json"},
            data=json.dumps(symbols)
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def get_history(self, symbol, period=9, count=100):
        """获取历史数据"""
        params = {"period": period, "count": count}
        response = requests.get(f"{self.base_url}/api/history/{symbol}", params=params)
        if response.status_code == 200:
            return response.json()
        return None

# 使用示例
if __name__ == "__main__":
    client = TDXClient()
    
    # 获取单只股票行情
    quote = client.get_quote("sz000001")
    print(quote)
    
    # 批量获取行情
    symbols = ["sh600036", "sz000002", "sh601318"]
    quotes = client.get_batch_quotes(symbols)
    print(quotes)
```

### Node.js项目调用示例

```javascript
const axios = require('axios');

class TDXClient {
    constructor(baseUrl = 'http://localhost:6999') {
        this.baseUrl = baseUrl;
    }
    
    async getQuote(symbol) {
        try {
            const response = await axios.get(`${this.baseUrl}/api/quote/${symbol}`);
            return response.data;
        } catch (error) {
            console.error('获取行情失败:', error.message);
            return null;
        }
    }
    
    async getBatchQuotes(symbols) {
        try {
            const response = await axios.post(
                `${this.baseUrl}/api/quotes`,
                symbols,
                { headers: { 'Content-Type': 'application/json' } }
            );
            return response.data;
        } catch (error) {
            console.error('批量获取行情失败:', error.message);
            return null;
        }
    }
}

// 使用示例
async function main() {
    const client = new TDXClient();
    
    const quote = await client.getQuote('sz000001');
    console.log(quote);
    
    const symbols = ['sh600036', 'sz000002', 'sh601318'];
    const quotes = await client.getBatchQuotes(symbols);
    console.log(quotes);
}

main();
```

## 配置说明

### 服务器配置
编辑 `config.py` 文件修改TDX服务器配置：

```python
TDX_SERVERS = [
    {"ip": "129.204.230.128", "port": 7709, "name": "电信主站"},
    {"ip": "124.70.133.119", "port": 7709, "name": "移动主站"},
    {"ip": "139.159.239.163", "port": 7709, "name": "联通主站"},
]
```

### 环境要求
- Python 3.7+
- 需要的依赖：`fastapi`, `uvicorn`, `pytdx`, `pandas`, `requests`

## 故障排除

### 常见问题
1. **实时数据获取失败**: 检查是否为交易时间，TDX服务器可能在非交易时间不提供实时数据
2. **连接超时**: 尝试切换不同的TDX服务器
3. **服务无法启动**: 检查端口6999是否被占用

### 日志查看
服务启动后会显示详细的调试日志，包括：
- 连接状态
- API调用详情
- 错误信息

## 开发测试

项目包含多个示例程序：
- `examples/basic_usage.py` - 基础使用示例
- `examples/api_usage_example.py` - API使用示例
- `examples/data_analysis_example.py` - 数据分析示例

运行测试：
```bash
python examples/basic_usage.py
```