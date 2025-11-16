"""
IBTraderMCP FastMCP Server
Interactive Brokers MCP Server for trading and market data
"""
import asyncio
import nest_asyncio
nest_asyncio.apply()
from contextlib import asynccontextmanager
from fastmcp import FastMCP

# Import all tool functions
from src.tools.account import (
    get_account_summary
)
from src.tools.positions import (
    get_stock_positions,
    get_option_positions,
    get_position_summary
)
from src.tools.market_data import (
    get_historical_kline,
    get_daily_kline,
    get_weekly_kline,
    get_monthly_kline
)
from src.tools.calendar import (
    get_trading_calendar,
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

# Get instances
ib_client = get_ib_client()
config = get_config()


# ==================== Lifecycle Management ====================

@asynccontextmanager
async def lifespan(app):
    """Manage IB Gateway connection lifecycle"""
    # Startup
    logger.info("IBTraderMCP server starting...")
    logger.info(f"Connecting to IB Gateway at {config.ib_host}:{config.ib_port}...")
    
    success = await ib_client.connect()
    if success:
        logger.info("Successfully connected to IB Gateway")
    else:
        logger.error("Failed to connect to IB Gateway - some functions may not work")

    account_updates_success = await ib_client.requestAccountUpdates()
    if account_updates_success:
        logger.info("Requested account updates successfully")
    else:
        logger.error("Failed to request account updates")
    
    yield
    
    # Shutdown
    logger.info("IBTraderMCP server shutting down...")
    ib_client.disconnect()
    logger.info("Disconnected from IB Gateway")


# Create FastMCP server with lifespan
mcp = FastMCP("IBTraderMCP", lifespan=lifespan)


# ==================== Account Tools ====================

@mcp.tool(
    name="get_account_summary",
    description="Get account summary including net liquidation value, cash balance, available funds, buying power, and margin information"
)
async def account_summary() -> dict:
    """Get account summary including net liquidation value, cash balance, available funds, and buying power.
    
    Returns:
        Account summary dictionary with key financial metrics
    """
    return await get_account_summary()


# ==================== Position Tools ====================

@mcp.tool(
    name="get_stock_positions",
    description="Retrieve all current stock positions with details including symbol, quantity, market value, average cost, and unrealized P&L"
)
async def stock_positions() -> list:
    """Get all current stock positions with market values, costs, and P&L.
    
    Returns:
        List of stock positions including symbol, quantity, market value, and unrealized P&L
    """
    return await get_stock_positions()


@mcp.tool(
    name="get_option_positions",
    description="Retrieve all current option positions with contract specifications (strike, expiry, right), quantity, market value, and unrealized P&L"
)
async def option_positions() -> list:
    """Get all current option positions with contract details, market values, and P&L.
    
    Returns:
        List of option positions including contract specifications, quantity, market value, and unrealized P&L
    """
    return await get_option_positions()


@mcp.tool(
    name="get_position_summary",
    description="Get comprehensive position summary with total market value, total P&L, position allocation percentages, and breakdown of stocks vs options"
)
async def position_summary() -> dict:
    """Get comprehensive position summary including total market value, total P&L, and position allocation breakdown.
    
    Returns:
        Position summary with aggregated metrics for stocks and options
    """
    return await get_position_summary()


# ==================== Market Data Tools ====================

@mcp.tool(
    name="get_historical_kline",
    description="Get historical candlestick (OHLCV) data with flexible timeframes. Supports multiple bar sizes (1min to 1M) and durations. Uses caching for better performance."
)
async def historical_kline(
    symbol: str,
    bar_size: str = "1D",
    duration: str = "1 Y",
    use_cache: bool = True
) -> list:
    """Get historical candlestick (OHLCV) data with optional caching for faster repeated queries.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        bar_size: Bar interval - '1D' (daily), '1W' (weekly), '1M' (monthly), '1H' (hourly), '30min', '15min', '5min', '1min'
        duration: Time range - e.g., '1 Y' (1 year), '6 M' (6 months), '1 W' (1 week), '1 D' (1 day)
        use_cache: Whether to use cached data for faster retrieval (default: True)
    
    Returns:
        List of candles, each containing datetime, open, high, low, close, and volume
    """
    return await get_historical_kline(symbol, bar_size, duration, use_cache=use_cache)


@mcp.tool(
    name="get_daily_kline",
    description="Get daily candlestick data for a specified number of trading days. Convenient wrapper for daily OHLCV data retrieval."
)
async def daily_kline(symbol: str, days: int = 365) -> list:
    """Get daily candlestick data for the specified number of trading days.
    
    Args:
        symbol: Stock ticker symbol
        days: Number of trading days to retrieve (default: 365)
    
    Returns:
        List of daily candles with OHLCV data
    """
    return await get_daily_kline(symbol, days)


@mcp.tool(
    name="get_weekly_kline",
    description="Get weekly candlestick data for a specified number of weeks. Useful for medium-term trend analysis."
)
async def weekly_kline(symbol: str, weeks: int = 52) -> list:
    """Get weekly candlestick data for the specified number of weeks.
    
    Args:
        symbol: Stock ticker symbol
        weeks: Number of weeks to retrieve (default: 52)
    
    Returns:
        List of weekly candles with OHLCV data
    """
    return await get_weekly_kline(symbol, weeks)


@mcp.tool(
    name="get_monthly_kline",
    description="Get monthly candlestick data for a specified number of months. Ideal for long-term trend analysis and historical performance review."
)
async def monthly_kline(symbol: str, months: int = 12) -> list:
    """Get monthly candlestick data for the specified number of months.
    
    Args:
        symbol: Stock ticker symbol
        months: Number of months to retrieve (default: 12)
    
    Returns:
        List of monthly candles with OHLCV data
    """
    return await get_monthly_kline(symbol, months)

# ==================== Calendar Tools ====================

@mcp.tool(
    name="get_trading_calendar",
    description="Get trading calendar with market open/close times for a date range. Returns list of trading days excluding weekends and holidays."
)
def trading_calendar(
    start_date: str,
    end_date: str,
    exchange: str = "NYSE"
) -> list:
    """Get trading calendar with market open/close times for the specified date range.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        exchange: Exchange code (default: 'NYSE')
    
    Returns:
        List of trading days with opening and closing times
    """
    return get_trading_calendar(start_date, end_date, exchange)

# ==================== Fundamental Tools ====================

@mcp.tool(
    name="get_company_info",
    description="Get basic company information including company name, industry classification, sector, primary exchange, and currency. No IB subscription required."
)
async def company_info(symbol: str) -> dict:
    """Get basic company information including name, industry, sector, and exchange. No subscription required.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Dictionary with company name, industry classification, primary exchange, and other basic details
    """
    return await get_company_info(symbol)


@mcp.tool(
    name="get_company_overview",
    description="Get comprehensive company overview including business description, operations summary, and corporate structure. Requires IB fundamental data subscription."
)
async def company_overview(symbol: str) -> dict:
    """Get comprehensive company overview including business description and key metrics. Requires IB fundamental data subscription.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Detailed company overview data
    """
    return await get_company_overview(symbol)


@mcp.tool(
    name="get_financial_summary",
    description="Get financial summary with key metrics including revenue, earnings, profit margins, P/E ratio, EPS, and other fundamental indicators. Requires IB fundamental data subscription."
)
async def financial_summary(symbol: str) -> dict:
    """Get financial summary with key metrics, ratios, and performance indicators. Requires IB fundamental data subscription.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Financial summary including revenue, earnings, margins, and other key financial metrics
    """
    return await get_financial_summary(symbol)


@mcp.tool(
    name="get_analyst_reports",
    description="Get analyst recommendations, consensus ratings, price targets, and recent rating changes from Wall Street analysts. Requires IB fundamental data subscription."
)
async def analyst_reports(symbol: str) -> dict:
    """Get analyst recommendations, ratings, and price targets. Requires IB fundamental data subscription.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        Analyst reports with consensus ratings, price targets, and recommendation changes
    """
    return await get_analyst_reports(symbol)


# ==================== Server Runner ====================

async def test_server():
    await ib_client.connect()

    account_updates_success = await ib_client.requestAccountUpdates()
    if account_updates_success:
        logger.info("Requested account updates successfully")
    else:
        logger.error("Failed to request account updates")
    
    """Run the MCP server for testing"""
    account_summary = await get_account_summary()
    logger.info(f"Account Summary: {account_summary}")

    stock_positions = await get_stock_positions()
    logger.info(f"Stock Positions: {stock_positions}")

    option_positions = await get_option_positions()
    logger.info(f"Option Positions: {option_positions}")

    position_summary = await get_position_summary()
    logger.info(f"Position Summary: {position_summary}")

    daily_kline_aapl_30 = await get_daily_kline("AAPL", days=30)
    logger.info(f"AAPL Daily Kline (30 days): {daily_kline_aapl_30}")

    weekly_kline_msft_12 = await get_weekly_kline("MSFT", weeks=12)
    logger.info(f"MSFT Weekly Kline (12 weeks): {weekly_kline_msft_12}")

    monthly_kline_goog_6 = await get_monthly_kline("GOOG", months=6)
    logger.info(f"GOOG Monthly Kline (6 months): {monthly_kline_goog_6}")

    trading_days = get_trading_calendar("2023-01-01", "2023-12-31")
    logger.info(f"Trading Calendar 2023: {trading_days}")

    nvda_info = await get_company_info("NVDA")
    logger.info(f"NVDA Company Info: {nvda_info}")

    amazon_overview_financial = await get_financial_summary("AMZN")
    logger.info(f"AMZN Financial Summary: {amazon_overview_financial}")

    meta_analyst_reports = await get_analyst_reports("META")
    logger.info(f"META Analyst Reports: {meta_analyst_reports}")

if __name__ == "__main__":
    logger.info("Starting IBTraderMCP server...")
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=4211,
        path="/ibkr",
        log_level="debug",
    )
    # asyncio.run(test_server())
