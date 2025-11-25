# TDX数据源管理服务

基于pytdx的股票数据API服务，提供实时行情、历史数据、基本信息和新闻数据。

## 功能特性

- ✅ 实时行情数据获取
- ✅ 历史K线数据查询  
- ✅ 股票基本信息查询
- ✅ **财务数据查询**
- ✅ 公司报告文件获取
- ✅ 批量数据查询支持
- ✅ 多服务器自动切换
- ✅ RESTful API接口
- ✅ 跨域请求支持

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
# 方式1: 直接运行
python main.py

# 方式2: 使用启动脚本
python start.py

# 方式3: 使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 6999 --reload
```

服务启动后访问: http://localhost:6999

## API接口文档

启动服务后访问: http://localhost:6999/docs

### 主要接口

#### 1. 服务状态
- `GET /` - 服务基本信息
- `GET /api/status` - 服务连接状态
- `GET /api/servers` - 可用服务器列表

#### 2. 实时行情
- `GET /api/quote/{symbol}` - 获取单个股票实时行情
- `POST /api/quotes` - 批量获取实时行情

#### 3. 历史数据  
- `GET /api/history/{symbol}` - 获取K线数据
  - 参数: `period` (周期), `count` (数量)

#### 4. 基本信息
- `GET /api/stock/{symbol}` - 获取股票基本信息
- `GET /api/markets` - 获取市场列表

#### 5. 财务数据
- `GET /api/finance/{symbol}` - 获取财务信息
- `GET /api/report/{symbol}` - 获取公司报告文件
  - 参数: `report_type` (报告类型, 0-默认)

#### 6. 新闻数据
- `GET /api/news` - 获取新闻信息

## 股票代码格式

- 上海股票: `sh600000` 或 `600000`
- 深圳股票: `sz000001` 或 `000001`
- 北京股票: `bj830000` 或 `830000`

## K线周期参数

| 参数值 | 周期说明 |
|--------|----------|
| 0 | 5分钟 |
| 1 | 15分钟 |
| 2 | 30分钟 |
| 3 | 1小时 |
| 4 | 日线 |
| 5 | 周线 |
| 6 | 月线 |
| 7 | 年线 |
| 8 | 1分钟 |
| 9 | 日线 |
| 10 | 季度线 |

## 使用示例

### 获取实时行情
```bash
curl "http://localhost:6999/api/quote/sh600000"
```

### 获取历史K线
```bash
curl "http://localhost:6999/api/history/sz000001?period=9&count=50"
```

### 批量查询
```bash
curl -X POST "http://localhost:6999/api/quotes" \
  -H "Content-Type: application/json" \
  -d '["sh600000", "sz000001", "bj430000"]'
```

### 获取财务数据
```bash
# 获取财务信息
curl "http://localhost:6999/api/finance/sh600000"

# 获取公司报告
curl "http://localhost:6999/api/report/sz000001?report_type=0"
```

## 配置说明

修改 `config.py` 文件可以:
- 添加/修改TDX服务器配置
- 调整API参数限制
- 配置市场代码映射

## 注意事项

1. 确保网络可以访问TDX服务器
2. 批量查询建议不超过100只股票
3. 历史数据查询数量建议不超过1000条
4. 服务会自动重连失败的服务器

## 开发扩展

服务基于FastAPI框架开发，可以轻松扩展:
- 添加新的数据接口
- 实现数据缓存
- 添加认证机制
- 集成数据库存储