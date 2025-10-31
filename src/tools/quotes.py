"""
Real-time quote tools
"""
from typing import Dict, Any, Optional
from src.ib_client import get_ib_client
from src.logger import logger

ib_client = get_ib_client()


async def get_last_price(
    symbol: str,
    exchange: str = "SMART",
    session: str = "ALL"
) -> Dict[str, Any]:
    """
    获取标的最新价格（快照查询）
    
    支持盘中、盘前、盘后和夜盘价格
    
    Args:
        symbol: 股票代码
        exchange: 交易所（默认SMART自动路由）
        session: 交易时段 (Regular/PreMarket/AfterHours/All)
                注意：IB默认返回所有时段的最新价格
        
    Returns:
        价格信息字典，包含：
        - symbol: 股票代码
        - last: 最新成交价
        - bid: 买一价
        - ask: 卖一价
        - close: 上一交易日收盘价
        - volume: 成交量
        - time: 价格时间戳
    """
    try:
        logger.info(f"Fetching last price for {symbol}...")
        
        contract = ib_client.create_stock_contract(symbol, exchange=exchange)
        price_data = await ib_client.get_market_price(contract)
        
        if not price_data:
            logger.error(f"Failed to get price for {symbol}")
            return {
                'error': 'Failed to fetch price',
                'symbol': symbol
            }
        
        logger.info(f"Retrieved price for {symbol}: {price_data.get('last', 'N/A')}")
        return price_data
        
    except Exception as e:
        logger.error(f"Error getting last price: {e}")
        return {
            'error': str(e),
            'symbol': symbol
        }


async def get_multiple_prices(symbols: list[str]) -> Dict[str, Dict[str, Any]]:
    """
    批量获取多个标的的最新价格
    
    Args:
        symbols: 股票代码列表
        
    Returns:
        字典，键为symbol，值为价格信息
    """
    try:
        logger.info(f"Fetching prices for {len(symbols)} symbols...")
        
        result = {}
        for symbol in symbols:
            price_data = await get_last_price(symbol)
            result[symbol] = price_data
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting multiple prices: {e}")
        return {'error': str(e)}


async def get_bid_ask_spread(symbol: str) -> Dict[str, Any]:
    """
    获取买卖价差信息
    
    Args:
        symbol: 股票代码
        
    Returns:
        买卖价差信息
    """
    try:
        price_data = await get_last_price(symbol)
        
        if 'error' in price_data:
            return price_data
        
        bid = price_data.get('bid')
        ask = price_data.get('ask')
        
        if bid and ask and bid > 0 and ask > 0:
            spread = ask - bid
            spread_pct = (spread / bid) * 100
        else:
            spread = None
            spread_pct = None
        
        return {
            'symbol': symbol,
            'bid': bid,
            'ask': ask,
            'spread': spread,
            'spread_pct': spread_pct,
            'time': price_data.get('time')
        }
        
    except Exception as e:
        logger.error(f"Error getting bid-ask spread: {e}")
        return {'error': str(e), 'symbol': symbol}
