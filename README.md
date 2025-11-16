# IBTraderMCP - Interactive Brokers MCP Server

基于 FastMCP 框架的 Interactive Brokers 交易服务器，提供完整的账户查询、市场数据获取和分析功能。

## ✨ 功能特性

### 📊 账户与仓位查询
- 账户摘要查询(净资产、现金、购买力、保证金等)
- 股票仓位查询(包含市值、成本、未实现盈亏)
- 期权仓位查询(包含合约详情、市值、盈亏)
- 仓位汇总分析(总市值、总盈亏、持仓分布)

### 📉 市场数据获取
- 历史K线数据(支持1分钟至1个月多种周期)
- 智能缓存机制(SQLite本地缓存,提升查询速度)
- 灵活的时间范围和周期配置
- 日K/周K/月K便捷封装方法

### 📅 交易日历工具
- 获取指定日期范围的交易日
- 返回每日开盘收盘时间
- 支持多个交易所(NYSE、NASDAQ等)

### 📰 基本面数据查询
- 公司基本信息(无需订阅)
- 公司概览(需订阅)
- 财务摘要(需订阅)
- 分析师报告和评级(需订阅)

### 📝 日志记录
- 结构化日志存储(SQLite)
- 文件日志记录(便于审计)
- 操作追踪和错误记录

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- Interactive Brokers Gateway 或 TWS
- 有效的IB账户

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/WisdomShun/IBTraderMCP.git
cd IBTraderMCP

# 安装依赖
pip install -e .
```

### 3. 配置

复制配置文件模板并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置IB连接参数：

```bash
# IB Gateway 配置
IB_HOST=127.0.0.1
IB_PORT=7497  # 模拟盘7497，实盘7496
IB_CLIENT_ID=1
IB_ACCOUNT=DU123456  # 替换为您的IB账户

# 缓存和日志
CACHE_DB_PATH=./data/trading.db
LOG_LEVEL=INFO
LOG_PATH=./logs/
```

### 4. 配置IB Gateway
为安全起见，你需要将IB（模拟）账号密码信息配置到环境变量中
1. TWS_PASSWORD （IB实盘账号密码）
2. TWS_PASSWORD_PAPER（IB模拟账号密码）
3. TWS_USERID（IB实盘账号）
4. TWS_USERID_PAPER（IB模拟账号）

### 5. 启动 IB Gateway
在运行服务器前，确保：
1. IB Gateway 或 TWS 已启动
2. API 连接已启用（配置 -> API -> Settings）
3. 端口设置正确（模拟盘7497，实盘7496）

### 6. 运行服务器

```bash
python -m src.server
```

或使用 FastMCP CLI：

```bash
fastmcp run src/server.py
```

## 📖 使用示例

### 查询账户信息

```python
# 获取账户摘要
result = await account_summary()
# 返回账户净值、现金、可用资金、购买力等关键指标

# 获取股票仓位
stock_pos = await stock_positions()
# 返回所有股票仓位列表,包含代码、数量、市值、成本、盈亏

# 获取期权仓位
option_pos = await option_positions()
# 返回所有期权仓位,包含合约详情(执行价、到期日)、市值、盈亏

# 获取仓位汇总
summary = await position_summary()
# 返回总市值、总盈亏、持仓分布比例等汇总数据
```

### 获取市场数据

```python
# 获取日K线数据(带缓存)
data = await daily_kline(symbol="AAPL", days=365)
# 返回365个交易日的OHLCV数据

# 获取周K线数据
data = await weekly_kline(symbol="MSFT", weeks=52)
# 返回52周的OHLCV数据

# 获取月K线数据
data = await monthly_kline(symbol="GOOG", months=12)
# 返回12个月的OHLCV数据

# 灵活的历史数据查询
data = await historical_kline(
    symbol="TSLA",
    bar_size="1H",      # 1小时K线
    duration="1 M",     # 1个月数据
    use_cache=True      # 使用缓存
)
```

### 交易日历查询

```python
# 获取交易日历
days = trading_calendar(
    start_date="2024-01-01",
    end_date="2024-12-31",
    exchange="NYSE"
)
# 返回指定日期范围内的所有交易日及开盘收盘时间
```

### 基本面数据查询

```python
# 获取公司基本信息(无需订阅)
info = await company_info(symbol="AAPL")
# 返回公司名称、行业、板块、交易所等基础信息

# 获取公司概览(需订阅)
overview = await company_overview(symbol="AAPL")
# 返回公司业务描述、运营概要等详细信息

# 获取财务摘要(需订阅)
financials = await financial_summary(symbol="AAPL")
# 返回营收、利润、市盈率、EPS等财务指标

# 获取分析师报告(需订阅)
analysts = await analyst_reports(symbol="AAPL")
# 返回分析师评级、目标价、推荐变化等信息
```

## 🗂️ 项目结构

```
IBTraderMCP/
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP服务器主入口(包含所有工具定义)
│   ├── config.py              # 配置管理
│   ├── logger.py              # 日志管理
│   ├── ib_client.py           # IB客户端封装
│   ├── models.py              # 数据模型定义
│   ├── cache/                 # 缓存模块
│   │   ├── __init__.py
│   │   ├── db_manager.py      # SQLite数据库管理
│   │   └── cache_utils.py     # 缓存装饰器和工具
│   └── tools/                 # 工具模块(底层实现)
│       ├── __init__.py
│       ├── account.py         # 账户查询实现
│       ├── positions.py       # 仓位查询实现
│       ├── market_data.py     # 市场数据实现
│       ├── calendar.py        # 交易日历实现
│       └── fundamentals.py    # 基本面数据实现
├── data/                      # 数据缓存目录
│   └── trading.db             # SQLite数据库
├── logs/                      # 日志目录
├── examples/                  # 示例代码
├── .env.example               # 配置文件模板
├── pyproject.toml             # 项目配置
└── README.md                  # 本文件
```

## ⚠️ 重要注意事项

### IB Gateway 要求
- 需要预先启动 IB Gateway 或 TWS
- 在 IB 配置中启用 API 连接
- 注意区分实盘(7496)和模拟盘(7497)端口
- 确保账户有足够的权限

### 数据限制
- 历史数据有请求频率限制
- 实时数据需要市场数据订阅
- 某些基本面数据需要额外订阅

### 风险提示
⚠️ **本项目仅供学习和研究使用**
- 本系统仅提供数据查询功能,不包含交易执行
- 实盘连接请谨慎使用,避免误操作
- 请在模拟盘充分测试后再连接实盘

## 🔧 配置参数说明

### IB连接配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| IB_HOST | 127.0.0.1 | IB Gateway主机地址 |
| IB_PORT | 7497 | IB Gateway端口(7497=模拟盘,7496=实盘) |
| IB_CLIENT_ID | 1 | 客户端ID |
| IB_ACCOUNT | - | IB账户号(必填) |

### 缓存配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| CACHE_DB_PATH | ./data/trading.db | SQLite数据库路径 |
| CACHE_KLINE_DAYS | 365 | K线数据缓存天数 |

### 日志配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| LOG_LEVEL | INFO | 日志级别 |
| LOG_PATH | ./logs/ | 日志文件目录 |
| LOG_MAX_BYTES | 10485760 | 单个日志文件最大大小(10MB) |
| LOG_BACKUP_COUNT | 5 | 保留的日志备份文件数量 |

### 其他配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| TIMEZONE | America/New_York | 时区设置(美东时间) |

## 📊 数据库表结构

### kline_data(K线数据缓存)
- `symbol`: 股票代码(如 AAPL)
- `bar_size`: K线周期(1D=日K, 1W=周K, 1M=月K等)
- `datetime`: 时间戳
- `open`, `high`, `low`, `close`: 开高低收价格
- `volume`: 成交量
- `cached_at`: 缓存时间

### trading_logs(操作日志)
- `timestamp`: 时间戳
- `operation`: 操作类型(query_account, get_kline等)
- `symbol`: 相关标的代码
- `reason`: 操作原因描述
- `result`: 操作结果(success/error)
- `error_message`: 错误信息(如有)
- `additional_data`: 额外数据(JSON格式)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [FastMCP](https://github.com/jlowin/fastmcp) - MCP 框架
- [ib_insync](https://github.com/erdewit/ib_insync) - IB API 封装
- [pandas-market-calendars](https://github.com/rsheftel/pandas_market_calendars) - 交易日历

---

**免责声明**：本项目仅供学习研究使用，不构成任何投资建议。使用本项目进行实盘交易的风险由使用者自行承担。