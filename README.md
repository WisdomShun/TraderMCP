# IBTraderMCP - Interactive Brokers MCP Server

基于 FastMCP 框架的 Interactive Brokers 交易服务器，提供完整的账户查询、交易执行、市场数据获取和风险管理功能。

## ✨ 功能特性

### 📊 账户与仓位管理
- 账户摘要查询（净资产、现金、购买力等）
- 股票和期权仓位查询
- 仓位汇总分析
- 保证金信息查询

### 📈 订单管理
- 查询未成交订单
- 查询历史订单
- 支持4种订单类型：
  - 市价单 (MKT)
  - 限价单 (LMT)
  - 止损单 (STP)
  - 止损限价单 (STP LMT)
- Bracket订单（自动止损止盈）
- 订单修改和取消

### 📉 市场数据
- 历史K线数据（日K、周K、月K等）
- 智能缓存机制（SQLite）
- 实时报价查询
- 买卖价差分析

### 🎯 期权交易
- 期权链查询
- 希腊值获取（Delta、Gamma、Theta、Vega）
- 隐含波动率查询
- 按Delta搜索期权合约
- 期权交易支持

### 📅 交易日历
- 交易日查询
- 下一个/上一个交易日
- 交易日计数

### 📰 基本面数据
- 公司基本信息
- 财务摘要
- 分析师报告

### 🛡️ 风险管理（基于查理·芒格投资理念）

#### 强制规则（BLOCK）
- ❌ **禁止融资交易**：不允许使用杠杆
- ✅ **强制止损**：所有BUY订单必须设置止损价
- ⚖️ **单标的持仓限制**：单个标的不超过总资产20%
- 📊 **总仓位限制**：总仓位不超过净资产85%
- 📉 **最大回撤控制**：单标的亏损达到10%强制平仓提示
- 🎯 **期权仓位限制**：期权总价值不超过总资产10%

#### 期权特殊规则
- ✅ **Covered Call**：卖出看涨期权必须持有正股
- ✅ **Protective Put**：保护性看跌期权
- ✅ **Naked Put**：卖出看跌期权需100%现金或95%短期债券作为保证金
- ❌ **禁止裸卖看涨期权**

#### 警告规则（WARNING）
- ⚠️ 集中度检查：单一行业持仓过高
- ⚠️ 波动率检查：高波动率标的
- ⚠️ 流动性检查：低流动性标的

### 📝 双重日志记录
- **数据库日志**：结构化存储，便于查询分析
- **文本日志**：人类可读格式，便于审计
- 记录所有交易操作及原因（AI必须提供）

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

# 风控参数
RISK_MAX_SINGLE_POSITION_PCT=20
RISK_MAX_TOTAL_POSITION_PCT=85
RISK_MAX_DRAWDOWN_PCT=10
RISK_MAX_OPTION_POSITION_PCT=10
RISK_ALLOW_MARGIN=false
RISK_REQUIRE_STOP_LOSS=true
RISK_BOND_MARGIN_PCT=95

# 缓存和日志
CACHE_DB_PATH=./data/trading.db
LOG_LEVEL=INFO
LOG_PATH=./logs/
```

### 4. 启动 IB Gateway

在运行服务器前，确保：
1. IB Gateway 或 TWS 已启动
2. API 连接已启用（配置 -> API -> Settings）
3. 端口设置正确（模拟盘7497，实盘7496）

### 5. 运行服务器

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
await account_summary()
# 返回: {'net_liquidation': 100000.0, 'total_cash': 50000.0, ...}

# 获取仓位
await positions(asset_type="STK")  # 股票仓位
await positions(asset_type="OPT")  # 期权仓位
await positions(asset_type="ALL")  # 所有仓位
```

### 获取市场数据

```python
# 获取日K线（带缓存）
await daily_kline(symbol="AAPL", days=365)

# 获取实时报价
await last_price(symbol="AAPL")
# 返回: {'symbol': 'AAPL', 'last': 150.25, 'bid': 150.20, 'ask': 150.30, ...}
```

### 下单交易

```python
# 市价单买入（带止损）
await submit_order(
    symbol="AAPL",
    action="BUY",
    quantity=100,
    order_type="MKT",
    stop_loss_price=145.00,
    reason="技术突破，RSI超卖反弹，目标价160"
)

# 限价单买入（Bracket订单，带止损止盈）
await submit_order(
    symbol="AAPL",
    action="BUY",
    quantity=100,
    order_type="LMT",
    limit_price=150.00,
    stop_loss_price=145.00,
    take_profit_price=160.00,
    reason="价格回调至支撑位，风险回报比1:2"
)
```

### 期权交易

```python
# 获取期权链
await option_chain(symbol="AAPL", expiration_date="20250117")

# 查找特定Delta的期权
await find_options_by_delta(
    symbol="AAPL",
    target_delta=0.3,  # 30 delta
    delta_range=0.05
)

# 卖出Covered Call
await submit_order(
    symbol="AAPL",
    action="SELL",
    quantity=1,  # 1张合约 = 100股
    order_type="LMT",
    limit_price=2.50,
    contract_type="OPT",
    option_expiration="20250117",
    option_strike=160.0,
    option_right="C",
    reason="持有100股AAPL正股，卖出OTM看涨期权获取收益"
)
```

### 查询订单

```python
# 获取未成交订单
await open_orders()

# 查询历史订单
await order_history(symbol="AAPL", days=30)

# 修改订单
await update_order(
    order_id=12345,
    new_price=151.00,
    reason="价格调整，提高成交概率"
)

# 取消订单
await cancel_order_by_id(
    order_id=12345,
    reason="市场环境变化，取消订单"
)
```

## 🗂️ 项目结构

```
IBTraderMCP/
├── src/
│   ├── __init__.py
│   ├── server.py              # FastMCP服务器主入口
│   ├── config.py              # 配置管理
│   ├── logger.py              # 日志管理
│   ├── ib_client.py           # IB客户端封装
│   ├── cache/                 # 缓存模块
│   │   ├── __init__.py
│   │   └── db_manager.py      # SQLite数据库管理
│   ├── risk/                  # 风控模块
│   │   ├── __init__.py
│   │   └── risk_manager.py    # 风控引擎
│   └── tools/                 # MCP工具
│       ├── __init__.py
│       ├── account.py         # 账户查询
│       ├── positions.py       # 仓位查询
│       ├── orders.py          # 订单管理
│       ├── market_data.py     # 市场数据
│       ├── quotes.py          # 实时报价
│       ├── options.py         # 期权工具
│       ├── calendar.py        # 交易日历
│       └── fundamentals.py    # 基本面数据
├── data/                      # 数据缓存目录
│   └── trading.db             # SQLite数据库
├── logs/                      # 日志目录
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
- 实盘交易有风险，投资需谨慎
- 请在模拟盘充分测试后再使用实盘
- 风控规则仅供参考，不构成投资建议
- 请根据个人风险承受能力调整参数

## 🔧 配置参数说明

### 风控参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| RISK_MAX_SINGLE_POSITION_PCT | 20 | 单标的最大仓位占比(%) |
| RISK_MAX_TOTAL_POSITION_PCT | 85 | 总仓位占比(%) |
| RISK_MAX_DRAWDOWN_PCT | 10 | 最大回撤(%) |
| RISK_MAX_OPTION_POSITION_PCT | 10 | 期权仓位占比(%) |
| RISK_ALLOW_MARGIN | false | 是否允许融资 |
| RISK_REQUIRE_STOP_LOSS | true | 是否强制止损 |
| RISK_BOND_MARGIN_PCT | 95 | 短期债券作为保证金的折扣(%) |

### 警告阈值

| 参数 | 默认值 | 说明 |
|------|--------|------|
| RISK_WARN_SECTOR_CONCENTRATION_PCT | 40 | 单一行业持仓警告阈值(%) |
| RISK_WARN_HIGH_VOLATILITY_THRESHOLD | 50 | 高波动率警告阈值(年化%) |
| RISK_WARN_LOW_VOLUME_THRESHOLD | 100000 | 低流动性警告阈值(日均成交量) |

## 📊 数据库表结构

### kline_data（K线数据）
- symbol: 股票代码
- bar_size: K线类型
- datetime: 时间
- open/high/low/close/volume: OHLCV数据

### trading_logs（交易日志）
- timestamp: 时间戳
- operation: 操作类型
- symbol: 标的代码
- reason: 操作原因
- risk_checks: 风控检查结果（JSON）
- result: 操作结果

### option_chains（期权链缓存）
- symbol: 标的代码
- contract_symbol: 期权合约代码
- expiration_date: 到期日
- strike: 执行价
- delta/gamma/theta/vega: 希腊值
- implied_volatility: 隐含波动率

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