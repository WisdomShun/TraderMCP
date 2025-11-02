"""
IBTraderMCP FastMCP Server
Interactive Brokers MCP Server for trading and market data
"""
import asyncio
from fastmcp import FastMCP

# Import all tool functions
from src.tools.account import (
    get_account_summary
)
from src.tools.positions import (
    get_positions,
    get_stock_positions,
    get_option_positions,
    get_position_summary
)
from src.tools.orders import (
    get_open_orders,
    get_order_history,
    get_order_by_id,
    place_order,
    modify_order,
    cancel_order
)
from src.tools.market_data import (
    get_historical_kline,
    get_daily_kline,
    get_weekly_kline,
    get_monthly_kline
)
from src.tools.quotes import (
    get_last_price,
    get_multiple_prices,
    get_bid_ask_spread
)
from src.tools.options import (
    get_option_chain,
    get_option_greeks,
    get_cached_option_chain,
    search_options_by_delta
)
from src.tools.calendar import (
    get_trading_calendar,
    is_trading_day,
    get_next_trading_day,
    get_previous_trading_day,
    count_trading_days
)
from src.tools.fundamentals import (
    get_company_info,
    get_company_overview,
    get_financial_summary,
    get_analyst_reports
)

from src.ib_client import get_ib_client
from src.logger import logger
from src.config import get_config

# Create FastMCP server
mcp = FastMCP("IBTraderMCP")

# Get instances
ib_client = get_ib_client()
config = get_config()


# ==================== Lifecycle Events ====================

@mcp.event("startup")
async def startup():
    """Connect to IB Gateway on startup"""
    logger.info("IBTraderMCP server starting...")
    logger.info(f"Connecting to IB Gateway at {config.ib.host}:{config.ib.port}...")
    
    success = await ib_client.connect()
    if success:
        logger.info("Successfully connected to IB Gateway")
    else:
        logger.error("Failed to connect to IB Gateway - some functions may not work")


@mcp.event("shutdown")
async def shutdown():
    """Disconnect from IB Gateway on shutdown"""
    logger.info("IBTraderMCP server shutting down...")
    ib_client.disconnect()
    logger.info("Disconnected from IB Gateway")


# ==================== Account Tools ====================

@mcp.tool()
async def account_summary() -> dict:
    """
    获取账户摘要信息，包括净资产、现金、可用资金、购买力等
    
    Returns:
        账户摘要字典
    """
    return await get_account_summary()


# ==================== Position Tools ====================

@mcp.tool()
async def positions(asset_type: str = "ALL") -> list:
    """
    获取仓位信息
    
    Args:
        asset_type: 资产类型 (STK=股票, OPT=期权, ALL=所有)
    
    Returns:
        仓位列表
    """
    return await get_positions(asset_type)


@mcp.tool()
async def stock_positions() -> list:
    """
    获取股票仓位
    
    Returns:
        股票仓位列表
    """
    return await get_stock_positions()


@mcp.tool()
async def option_positions() -> list:
    """
    获取期权仓位
    
    Returns:
        期权仓位列表
    """
    return await get_option_positions()


@mcp.tool()
async def position_summary() -> dict:
    """
    获取仓位汇总信息（总市值、总盈亏、仓位占比等）
    
    Returns:
        仓位汇总字典
    """
    return await get_position_summary()


# ==================== Order Tools ====================

@mcp.tool()
async def open_orders() -> list:
    """
    获取当前未成交订单
    
    Returns:
        未成交订单列表
    """
    return await get_open_orders()


@mcp.tool()
async def order_history(
    symbol: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 7
) -> list:
    """
    获取历史订单（已成交和已取消）
    
    Args:
        symbol: 股票代码过滤（可选）
        start_date: 开始日期（可选，格式：YYYY-MM-DD）
        end_date: 结束日期（可选，格式：YYYY-MM-DD）
        days: 查询天数（默认7天）
    
    Returns:
        历史订单列表
    """
    return await get_order_history(symbol, start_date, end_date, days)


@mcp.tool()
async def order_details(order_id: int) -> dict | None:
    """
    根据订单ID获取订单详情
    
    Args:
        order_id: 订单ID
    
    Returns:
        订单详情字典或None
    """
    return await get_order_by_id(order_id)


@mcp.tool()
async def submit_order(
    symbol: str,
    action: str,
    quantity: int,
    order_type: str,
    reason: str,
    limit_price: float | None = None,
    stop_loss_price: float | None = None,
    take_profit_price: float | None = None,
    contract_type: str = "STK",
    option_expiration: str | None = None,
    option_strike: float | None = None,
    option_right: str | None = None
) -> dict:
    """
    下单（带风控检查和日志记录）
    
    **必须参数：**
    - symbol: 股票代码
    - action: 买卖方向 (BUY/SELL)
    - quantity: 数量
    - order_type: 订单类型 (MKT=市价, LMT=限价, STP=止损, STP LMT=止损限价)
    - reason: 下单原因（AI必须提供详细说明）
    
    **可选参数：**
    - limit_price: 限价（限价单必需）
    - stop_loss_price: 止损价（开仓时强制要求）
    - take_profit_price: 止盈价（可选）
    - contract_type: 合约类型 (STK=股票, OPT=期权)
    - option_expiration: 期权到期日（期权必需，格式：YYYYMMDD）
    - option_strike: 期权执行价（期权必需）
    - option_right: 期权类型（期权必需，C=看涨，P=看跌）
    
    **风控规则：**
    - 禁止融资交易
    - 开仓必须带止损
    - 单标的持仓不超过总资产20%
    - 总仓位不超过净资产85%
    - 期权总价值不超过总资产10%
    - 禁止裸卖看涨期权
    - 卖出看跌期权需100%现金或95%短期债券保证金
    
    Returns:
        订单结果字典
    """
    option_details = None
    if contract_type == "OPT":
        if not all([option_expiration, option_strike, option_right]):
            return {
                'success': False,
                'error': 'Option orders require expiration, strike, and right (C/P)',
                'symbol': symbol
            }
        option_details = {
            'expiration': option_expiration,
            'strike': option_strike,
            'right': option_right
        }
    
    return await place_order(
        symbol=symbol,
        action=action,
        quantity=quantity,
        order_type=order_type,
        reason=reason,
        limit_price=limit_price,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
        contract_type=contract_type,
        option_details=option_details
    )


@mcp.tool()
async def update_order(
    order_id: int,
    reason: str,
    new_quantity: int | None = None,
    new_price: float | None = None
) -> dict:
    """
    修改订单
    
    Args:
        order_id: 订单ID
        reason: 修改原因（AI必须提供）
        new_quantity: 新数量（可选）
        new_price: 新价格（可选）
    
    Returns:
        修改结果字典
    """
    return await modify_order(order_id, reason, new_quantity, new_price)


@mcp.tool()
async def cancel_order_by_id(order_id: int, reason: str) -> dict:
    """
    取消订单
    
    Args:
        order_id: 订单ID
        reason: 取消原因（AI必须提供）
    
    Returns:
        取消结果字典
    """
    return await cancel_order(order_id, reason)


# ==================== Market Data Tools ====================

@mcp.tool()
async def historical_kline(
    symbol: str,
    bar_size: str = "1D",
    duration: str = "1 Y",
    use_cache: bool = True
) -> list:
    """
    获取历史K线数据（带缓存）
    
    Args:
        symbol: 股票代码
        bar_size: K线类型 (1D=日K, 1W=周K, 1M=月K, 1H=小时, 30min, 15min, 5min, 1min)
        duration: 时间范围 (如 "1 Y", "6 M", "1 W", "1 D")
        use_cache: 是否使用缓存（默认True）
    
    Returns:
        K线数据列表，每项包含 datetime, open, high, low, close, volume
    """
    return await get_historical_kline(symbol, bar_size, duration, use_cache=use_cache)


@mcp.tool()
async def daily_kline(symbol: str, days: int = 365) -> list:
    """
    获取日K线数据
    
    Args:
        symbol: 股票代码
        days: 天数（默认365天）
    
    Returns:
        日K线数据列表
    """
    return await get_daily_kline(symbol, days)


@mcp.tool()
async def weekly_kline(symbol: str, weeks: int = 52) -> list:
    """
    获取周K线数据
    
    Args:
        symbol: 股票代码
        weeks: 周数（默认52周）
    
    Returns:
        周K线数据列表
    """
    return await get_weekly_kline(symbol, weeks)


@mcp.tool()
async def monthly_kline(symbol: str, months: int = 12) -> list:
    """
    获取月K线数据
    
    Args:
        symbol: 股票代码
        months: 月数（默认12个月）
    
    Returns:
        月K线数据列表
    """
    return await get_monthly_kline(symbol, months)


# ==================== Quote Tools ====================

@mcp.tool()
async def last_price(symbol: str, exchange: str = "SMART") -> dict:
    """
    获取标的最新价格（快照查询）
    支持盘中、盘前、盘后和夜盘价格
    
    Args:
        symbol: 股票代码
        exchange: 交易所（默认SMART自动路由）
    
    Returns:
        价格信息字典，包含 last, bid, ask, close, volume, time
    """
    return await get_last_price(symbol, exchange)


@mcp.tool()
async def multiple_prices(symbols: list[str]) -> dict:
    """
    批量获取多个标的的最新价格
    
    Args:
        symbols: 股票代码列表
    
    Returns:
        字典，键为symbol，值为价格信息
    """
    return await get_multiple_prices(symbols)


@mcp.tool()
async def bid_ask_spread(symbol: str) -> dict:
    """
    获取买卖价差信息
    
    Args:
        symbol: 股票代码
    
    Returns:
        买卖价差信息
    """
    return await get_bid_ask_spread(symbol)


# ==================== Option Tools ====================

@mcp.tool()
async def option_chain(symbol: str, expiration_date: str | None = None) -> list:
    """
    获取期权链数据（包含希腊值、隐含波动率等）
    
    Args:
        symbol: 标的股票代码
        expiration_date: 到期日过滤（可选，格式：YYYYMMDD）
    
    Returns:
        期权链列表，包含合约信息、Delta、Gamma、Theta、Vega、IV等
    """
    return await get_option_chain(symbol, expiration_date)


@mcp.tool()
async def option_greeks(
    symbol: str,
    expiration: str,
    strike: float,
    right: str
) -> dict:
    """
    获取单个期权合约的希腊值和市场数据
    
    Args:
        symbol: 标的股票代码
        expiration: 到期日（格式：YYYYMMDD）
        strike: 执行价
        right: 期权类型（C=看涨，P=看跌）
    
    Returns:
        期权详细数据，包含Delta、Gamma、Theta、Vega、隐含波动率等
    """
    return await get_option_greeks(symbol, expiration, strike, right)


@mcp.tool()
async def cached_option_chain(symbol: str, expiration_date: str | None = None) -> list:
    """
    从缓存获取期权链数据（不请求IB，速度快）
    
    Args:
        symbol: 标的股票代码
        expiration_date: 到期日过滤（可选）
    
    Returns:
        缓存的期权链数据
    """
    return await get_cached_option_chain(symbol, expiration_date)


@mcp.tool()
async def find_options_by_delta(
    symbol: str,
    target_delta: float,
    delta_range: float = 0.05,
    expiration_date: str | None = None
) -> list:
    """
    根据Delta值搜索期权
    
    Args:
        symbol: 标的股票代码
        target_delta: 目标Delta值（如0.3表示30 delta）
        delta_range: Delta容差范围（默认±0.05）
        expiration_date: 到期日过滤（可选）
    
    Returns:
        符合Delta条件的期权列表
    """
    return await search_options_by_delta(symbol, target_delta, delta_range, expiration_date)


# ==================== Calendar Tools ====================

@mcp.tool()
async def trading_calendar(
    start_date: str,
    end_date: str,
    exchange: str = "NYSE"
) -> list:
    """
    获取交易日历
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        exchange: 交易所代码（默认NYSE）
    
    Returns:
        交易日列表，包含日期、开盘收盘时间等
    """
    return get_trading_calendar(start_date, end_date, exchange)


@mcp.tool()
async def check_trading_day(date: str, exchange: str = "NYSE") -> dict:
    """
    检查指定日期是否为交易日
    
    Args:
        date: 日期（YYYY-MM-DD）
        exchange: 交易所代码
    
    Returns:
        包含是否交易日和开盘收盘时间的字典
    """
    return is_trading_day(date, exchange)


@mcp.tool()
async def next_trading_day(date: str, exchange: str = "NYSE") -> dict:
    """
    获取下一个交易日
    
    Args:
        date: 起始日期（YYYY-MM-DD）
        exchange: 交易所代码
    
    Returns:
        下一个交易日信息
    """
    return get_next_trading_day(date, exchange)


@mcp.tool()
async def previous_trading_day(date: str, exchange: str = "NYSE") -> dict:
    """
    获取上一个交易日
    
    Args:
        date: 起始日期（YYYY-MM-DD）
        exchange: 交易所代码
    
    Returns:
        上一个交易日信息
    """
    return get_previous_trading_day(date, exchange)


@mcp.tool()
async def trading_days_count(
    start_date: str,
    end_date: str,
    exchange: str = "NYSE"
) -> dict:
    """
    计算两个日期之间的交易日数量
    
    Args:
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        exchange: 交易所代码
    
    Returns:
        交易日数量信息
    """
    return count_trading_days(start_date, end_date, exchange)


# ==================== Fundamental Tools ====================

@mcp.tool()
async def company_info(symbol: str) -> dict:
    """
    获取公司基本信息（不需要额外订阅）
    包含公司名称、行业、分类、交易所等
    
    Args:
        symbol: 股票代码
    
    Returns:
        公司基本信息字典
    """
    return await get_company_info(symbol)


@mcp.tool()
async def company_overview(symbol: str) -> dict:
    """
    获取公司概况（需要IB基本面数据订阅）
    
    Args:
        symbol: 股票代码
    
    Returns:
        公司概况数据
    """
    return await get_company_overview(symbol)


@mcp.tool()
async def financial_summary(symbol: str) -> dict:
    """
    获取财务摘要（需要IB基本面数据订阅）
    
    Args:
        symbol: 股票代码
    
    Returns:
        财务摘要数据
    """
    return await get_financial_summary(symbol)


@mcp.tool()
async def analyst_reports(symbol: str) -> dict:
    """
    获取分析师报告（需要IB基本面数据订阅）
    
    Args:
        symbol: 股票代码
    
    Returns:
        分析师报告数据
    """
    return await get_analyst_reports(symbol)


# ==================== Server Runner ====================

if __name__ == "__main__":
    logger.info("Starting IBTraderMCP server...")
    mcp.run()
