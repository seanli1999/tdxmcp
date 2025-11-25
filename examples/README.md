# TDX数据服务示例程序

本目录包含TDX数据服务的示例程序，演示如何使用API进行数据获取和分析。

## 示例程序列表

### 1. API使用示例 (`api_usage_example.py`)

**功能**: 演示所有API端点的基本使用方法

**包含内容**:
- 基础服务状态检查
- 实时行情数据获取
- 历史K线数据获取
- 板块和行业数据查询
- 除权除息信息获取
- 连接池性能测试

**运行方式**:
```bash
python api_usage_example.py
```

### 2. 数据分析示例 (`data_analysis_example.py`)

**功能**: 演示如何使用API数据进行金融分析

**包含内容**:
- 股票表现对比分析
- 历史趋势分析（移动平均线计算）
- 板块分布统计
- 成交量分析
- 自动生成可视化图表

**运行方式**:
```bash
# 需要安装额外依赖
pip install pandas matplotlib numpy
python data_analysis_example.py
```

### 3. 快速测试脚本 (`quick_test.py`)

**功能**: 快速验证所有API端点是否正常工作

**包含内容**:
- 所有端点的快速连通性测试
- 连接池状态检查
- 测试结果汇总统计

**运行方式**:
```bash
python quick_test.py
```

## API端点参考

### 基础端点
- `GET /` - 服务根目录
- `GET /api/status` - 服务状态信息
- `GET /api/servers` - 可用服务器列表

### 实时数据端点
- `GET /api/quote/{symbol}` - 单只股票实时行情
- `POST /api/quotes` - 批量股票实时行情

### 历史数据端点  
- `GET /api/history/{symbol}` - 单只股票历史K线
- `POST /api/history/batch` - 批量股票历史K线

### 财务数据端点
- `GET /api/finance/{symbol}` - 财务信息
- `GET /api/stock/{symbol}` - 股票基本信息
- `GET /api/report/{symbol}` - 公司报告（目前不可用）

### 新增功能端点
- `GET /api/blocks` - 板块数据
- `GET /api/industries` - 行业数据
- `GET /api/xdxr/{symbol}` - 除权除息信息

## 使用说明

1. **启动服务**: 首先确保TDX数据服务正在运行
   ```bash
   python main.py
   ```

2. **运行示例**: 在另一个终端中运行示例程序
   ```bash
   cd examples
   python api_usage_example.py
   ```

3. **查看结果**: 示例程序会输出详细的操作结果和数据信息

## 注意事项

1. 服务必须运行在 `http://localhost:6999`
2. 数据分析示例需要安装额外的Python包：
   ```bash
   pip install pandas matplotlib numpy
   ```
3. 部分功能（如公司报告）可能由于服务器限制而不可用
4. 连接池功能会自动管理TDX服务器连接，无需手动干预

## 扩展开发

这些示例程序可以作为您自己应用程序的开发参考。主要开发模式包括：

1. **同步请求**: 使用 `requests` 库进行HTTP请求
2. **错误处理**: 所有示例都包含完整的错误处理
3. **数据解析**: 演示如何解析JSON响应数据
4. **数据分析**: 展示如何使用pandas进行数据分析

## 故障排除

如果示例程序运行失败，请检查：

1. ✅ TDX服务是否正常运行
2. ✅ 网络连接是否正常
3. ✅ 防火墙是否阻止了本地连接
4. ✅ Python依赖是否安装完整

## 技术支持

如有问题请参考主项目的README文档或提交Issue。