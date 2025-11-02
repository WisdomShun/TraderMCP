"""
Real-time quote tools
"""
from typing import List, Optional, Dict
from ib_insync import Ticker
from src.ib_client import get_ib_client
from src.logger import logger
from src.models import BidAskSpread

ib_client = get_ib_client()


async def get_last_price(
    symbol: str,
    exchange: str = "SMART",
    session: str = "ALL"
) -> Optional[Ticker]:
    """
    获取标的最新价格（返回 ib_insync Ticker 对象）
    
    支持盘中、盘前、盘后和夜盘价格
    
    Args:
        symbol: 股票代码
        exchange: 交易所（默认SMART自动路由）
        session: 交易时段 (Regular/PreMarket/AfterHours/All)
                注意：IB默认返回所有时段的最新价格
        
    Returns:
        Ticker 对象，包含以下属性：
        - contract: 合约信息
        - time: 时间戳
        - bid, ask, last: 买价、卖价、最新价
        - bidSize, askSize, lastSize: 买量、卖量、成交量
        - volume: 总成交量
        - close: 上一交易日收盘价
        - high, low: 最高价、最低价
    """
    try:
        logger.info(f"Fetching last price for {symbol}...")
        
        contract = ib_client.create_stock_contract(symbol, exchange=exchange)
        ticker = await ib_client.get_ticker(contract, snapshot=True)
        
        if not ticker:
            logger.error(f"Failed to get ticker for {symbol}")
            return None
        
        logger.info(f"Retrieved ticker for {symbol}: last={ticker.last}")
        return ticker
        
    except Exception as e:
        logger.error(f"Error getting last price: {e}")
        return None


async def get_multiple_prices(symbols: List[str]) -> Dict[str, Optional[Ticker]]:
    """
    批量获取多个标的的最新价格（返回 Ticker 对象字典）
    
    Args:
        symbols: 股票代码列表
        
    Returns:
        字典，键为symbol，值为Ticker对象
    """
    try:
        logger.info(f"Fetching prices for {len(symbols)} symbols...")
        
        result = {}
        for symbol in symbols:
            ticker = await get_last_price(symbol)
            result[symbol] = ticker
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting multiple prices: {e}")
        return {}


async def get_bid_ask_spread(symbol: str) -> Optional[BidAskSpread]:
    """
    获取买卖价差信息（返回 Pydantic Model）
    
    Args:
        symbol: 股票代码
        
    Returns:
        BidAskSpread 对象
    """
    try:
        ticker = await get_last_price(symbol)
        
        if not ticker:
            return None
        
        bid = ticker.bid
        ask = ticker.ask
        
        if bid and ask and bid > 0 and ask > 0:
            spread = ask - bid
            spread_pct = (spread / bid) * 100
        else:
            spread = None
            spread_pct = None
        
        return BidAskSpread(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread=spread,
            spread_pct=spread_pct,
            time=str(ticker.time) if ticker.time else None
        )
        
    except Exception as e:
        logger.error(f"Error getting bid-ask spread: {e}")
        return None
